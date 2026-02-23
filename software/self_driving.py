#!/usr/bin/env python3
"""
Part 2, Step 2.4: Full Self-Driving Integration

Combines all subsystems into a single autonomous driving controller:
  - Advanced Mapping   (Step 2.1) — ultrasonic-based occupancy grid
  - Object Detection   (Step 2.2) — MediaPipe / mock camera detection
  - A* Routing         (Step 2.3) — pathfinding on the inflated map
  - Obstacle Avoidance (Part 1)   — reactive emergency stop

Flow
----
1. Scan surroundings  → build / update occupancy map
2. Detect objects     → stop for people / stop signs
3. Plan route (A*)    → shortest path from car to goal
4. Follow path        → drive step-by-step, rescan periodically
5. React to vision    → override routing if critical object detected
6. Repeat until goal reached

Usage:
    # Mock mode (PC):
    python self_driving.py

    # On Raspberry Pi (will actually drive!):
    python3 self_driving.py --goal 70,65

    # With custom parameters:
    python3 self_driving.py --goal 70,65 --rescan 3 --clearance 4
"""

import argparse
import logging
import time
import sys
import math

from hardware_mock import get_hardware
from advanced_mapping import AdvancedMapper, MAP_SIZE, OCCUPIED, FREE, UNKNOWN
from astar_routing import (
    astar, inflate_obstacles, simplify_path, PathFollower,
    visualize_path_ascii, heuristic,
    CLEARANCE_RADIUS, RESCAN_EVERY_N_STEPS,
)
from object_detection import ObjectDetector, VisionOverride

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_GOAL = (70, 65)        # default goal in map coordinates
ARRIVAL_THRESHOLD = 3.0        # cells — "close enough" to goal
MAX_REPLAN_FAILURES = 5        # give up after N consecutive no-path results
VISION_CHECK_INTERVAL = 0.5    # seconds between vision checks while driving
RESCAN_ON_BLOCKED = True       # force rescan when A* finds no path
LOG_LEVEL = logging.INFO

# ---------------------------------------------------------------------------
# Vision filtering for indoor floor driving
# ---------------------------------------------------------------------------
# We intentionally prioritize "close enough to matter" over class semantics.
# Actionable if object is both confident and physically large in frame.
VISION_MIN_CONFIDENCE = 0.55
VISION_MIN_BBOX_AREA = 1800         # px^2
VISION_MIN_BBOX_AREA_RATIO = 0.008  # bbox_area / (frame_area)
VISION_HARD_STOP_AREA_RATIO = 0.10  # very close object -> immediate stop + rescan
VISION_CENTER_X_TOL_RATIO = 0.42    # only react if object center is near heading direction
VISION_MIN_BBOX_BOTTOM_RATIO = 0.35 # ignore high-in-frame detections (likely far/background)
VISION_RETRIGGER_COOLDOWN_S = 2.0   # short cooldown to avoid stop-loop flicker
CAMERA_FRAME_W = 640
CAMERA_FRAME_H = 480

# Mapping robustness defaults
MAP_REBUILD_EACH_FULL_SCAN = True   # avoid stale accumulated obstacles across replans
NO_PATH_RELAX_CLEARANCE = True      # if blocked, retry once with slightly less inflation


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def setup_logging(level=LOG_LEVEL):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("self_driving")


# ---------------------------------------------------------------------------
# Main self-driving controller
# ---------------------------------------------------------------------------
class SelfDrivingCar:
    """
    Orchestrates mapping, detection, routing, and motor control
    into a complete self-driving loop.
    """

    def __init__(self, hw, goal=DEFAULT_GOAL,
                 clearance=CLEARANCE_RADIUS,
                 rescan_interval=RESCAN_EVERY_N_STEPS,
                 detector_method='auto'):
        """
        Args:
            hw:               Hardware dict from get_hardware()
            goal:             (x, y) destination in map coordinates
            clearance:        Obstacle inflation radius (cells)
            rescan_interval:  Rescan every N path steps
            detector_method:  'auto', 'mediapipe', 'vilib', or 'mock'
        """
        self.log = setup_logging()
        self.hw = hw
        self.goal = goal
        self.clearance = clearance
        self.rescan_interval = rescan_interval

        # Subsystems
        self.mapper = AdvancedMapper(map_size=MAP_SIZE)
        self.detector = ObjectDetector(method=detector_method)
        self.override = VisionOverride()
        self.follower = PathFollower(
            self.mapper, self.hw,
            detector=self.detector,
            override=self.override,
        )

        # State
        self.running = False
        self.reached_goal = False
        self.total_scans = 0
        self.total_replans = 0
        self.total_vision_stops = 0
        self.start_time = None

        # Small global cooldown to avoid repeated stop/replan on same close object.
        self._vision_cooldown_until = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, max_time=None):
        """
        Main entry point.  Drives the car to ``self.goal``.

        Args:
            max_time: Maximum seconds to run (None = unlimited)

        Returns:
            True if goal reached, False otherwise.
        """
        self.running = True
        self.start_time = time.time()

        self.log.info("=" * 60)
        self.log.info("SELF-DRIVING MODE ACTIVATED")
        self.log.info(f"  Hardware   : {self.hw.get('hardware_type', '?')}")
        self.log.info(f"  Map size   : {MAP_SIZE}x{MAP_SIZE}")
        self.log.info(f"  Car start  : ({self.mapper.car_x}, {self.mapper.car_y})")
        self.log.info(f"  Goal       : {self.goal}")
        self.log.info(f"  Clearance  : {self.clearance} cells")
        self.log.info(f"  Rescan     : every {self.rescan_interval} steps")
        self.log.info(f"  Vision     : {self.detector.detection_backend}")
        self.log.info("=" * 60)

        replan_failures = 0

        try:
            while self.running:
                # Time limit
                if max_time and (time.time() - self.start_time) > max_time:
                    self.log.info("Time limit reached.")
                    break

                # ---- 1. Check if we have arrived -------------------------
                car_pos = (self.mapper.car_x, self.mapper.car_y)
                dist = heuristic(car_pos, self.goal)
                if dist < ARRIVAL_THRESHOLD:
                    self.log.info(f"GOAL REACHED! Position {car_pos}, "
                                  f"distance {dist:.1f} cells")
                    self.reached_goal = True
                    break

                # ---- 2. Vision check (stop for people / signs / obstacles) --
                should_stop, detections, category = self._vision_check()
                if should_stop:
                    self._handle_vision_override(detections, category)

                # ---- 3. Scan environment ---------------------------------
                self.log.info("Scanning environment...")
                # Keep mapper orientation aligned with actual drive controller heading.
                self.mapper.car_angle = int(round(self.follower.current_heading)) % 360
                if MAP_REBUILD_EACH_FULL_SCAN:
                    # Rebuild local map from fresh scan each cycle to avoid stale
                    # obstacle accumulation that can falsely seal corridors.
                    self.mapper.occupancy_map.fill(UNKNOWN)
                    self.mapper.occupancy_map[self.mapper.car_y, self.mapper.car_x] = FREE
                scan_data = self.mapper.scan_environment(
                    self.hw, interpolate=True)
                self.mapper.update_map_from_scan(scan_data)
                self.total_scans += 1

                # ---- 4. Inflate obstacles --------------------------------
                inflated = inflate_obstacles(
                    self.mapper.get_map(), radius=self.clearance)

                # ---- 5. Plan path (A*) -----------------------------------
                start = (self.mapper.car_x, self.mapper.car_y)
                path = astar(inflated, start, self.goal,
                             allow_unknown=True)
                if (not path) and NO_PATH_RELAX_CLEARANCE and self.clearance > 0:
                    relaxed = max(0, self.clearance - 1)
                    self.log.warning(
                        f"No path with clearance={self.clearance}; retrying with {relaxed}")
                    inflated = inflate_obstacles(
                        self.mapper.get_map(), radius=relaxed)
                    path = astar(inflated, start, self.goal, allow_unknown=True)
                self.total_replans += 1

                if not path:
                    replan_failures += 1
                    self.log.warning(
                        f"No path found (attempt {replan_failures}/"
                        f"{MAX_REPLAN_FAILURES})")
                    if replan_failures >= MAX_REPLAN_FAILURES:
                        self.log.error("Too many replan failures — aborting.")
                        break
                    # Try rescanning with a wider view before giving up
                    if RESCAN_ON_BLOCKED:
                        self.log.info("Rescanning with wider angles...")
                        scan_data = self.mapper.scan_environment(
                            self.hw, angle_min=-90, angle_max=90,
                            step=10, interpolate=True)
                        self.mapper.update_map_from_scan(scan_data)
                    continue
                else:
                    replan_failures = 0

                simplified = simplify_path(path)
                self.log.info(
                    f"Path planned: {len(path)} cells, "
                    f"{len(simplified)} waypoints, "
                    f"~{dist:.0f} cells to goal")

                # ASCII visualization (compact)
                visualize_path_ascii(
                    inflated, path, start, self.goal,
                    car_pos=start, map_size=MAP_SIZE)

                # ---- 6. Follow path chunk --------------------------------
                steps_taken = 0
                for i in range(1, len(simplified)):
                    # Time limit check
                    if max_time and (time.time() - self.start_time) > max_time:
                        self.running = False
                        break

                    # Vision override mid-path
                    should_stop, detections, category = self._vision_check()
                    if should_stop:
                        self._handle_vision_override(detections, category)
                        break  # break inner loop → replan with fresh map

                    wp = simplified[i]
                    bumped = self.follower._move_to_waypoint(wp)
                    if bumped:
                        self.log.warning("Sonar bump — dodged obstacle, replanning")
                        break  # break inner loop → rescan + replan
                    steps_taken += 1

                    # Check arrival after each step
                    car_pos = (self.mapper.car_x, self.mapper.car_y)
                    if heuristic(car_pos, self.goal) < ARRIVAL_THRESHOLD:
                        self.reached_goal = True
                        break

                    # Rescan interval
                    if steps_taken >= self.rescan_interval:
                        self.log.info("Rescan interval reached, replanning...")
                        break  # break to outer loop for rescan

                if self.reached_goal:
                    break

        except KeyboardInterrupt:
            self.log.info("\nStopped by user (Ctrl+C)")
        finally:
            self.hw['stop']()
            self._print_summary()

        return self.reached_goal

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _vision_check(self):
        """
        Run one detection cycle.

        Returns (should_stop, detections, category) where category is:
          'proximity_hard'  — very large in-frame obstacle, immediate stop
          'proximity'       — likely-close obstacle, stop + quick rescan/replan
          None              — nothing actionable detected
        """
        try:
            all_detections = self.detector.detect_objects()
            now = time.time()
            if now < self._vision_cooldown_until:
                return False, all_detections, None

            frame_area = CAMERA_FRAME_W * CAMERA_FRAME_H
            actionable = []
            hard = []

            for d in all_detections:
                conf = d.get('confidence', d.get('score', 0.0))
                bbox = d.get('bbox', (0, 0, 0, 0))
                x = max(0, int(bbox[0]))
                y = max(0, int(bbox[1]))
                w = max(0, int(bbox[2]))
                h = max(0, int(bbox[3]))
                area = w * h
                if conf < VISION_MIN_CONFIDENCE:
                    continue
                if area < VISION_MIN_BBOX_AREA:
                    continue

                cx = x + (w / 2.0)
                bottom = y + h
                if abs(cx - (CAMERA_FRAME_W / 2.0)) > (CAMERA_FRAME_W * VISION_CENTER_X_TOL_RATIO):
                    continue
                if bottom < (CAMERA_FRAME_H * VISION_MIN_BBOX_BOTTOM_RATIO):
                    continue

                ratio = area / float(frame_area)
                if ratio >= VISION_MIN_BBOX_AREA_RATIO:
                    actionable.append(d)
                    if ratio >= VISION_HARD_STOP_AREA_RATIO:
                        hard.append(d)

            # Keep override API sane: any actionable proximity object triggers stop.
            self.override.update(bool(actionable), False, now)

            if hard:
                return True, hard, 'proximity_hard'
            if actionable:
                return True, actionable, 'proximity'
            return False, all_detections, None

        except Exception as e:
            self.log.debug(f"Vision check error: {e}")
            return False, [], None

    def _handle_vision_override(self, detections, category):
        """
        Smart response based on what was detected.

        category == 'proximity_hard' → immediate hard stop + short backoff
        category == 'proximity'      → stop + quick scan + replan
        """
        self.hw['stop']()
        self.total_vision_stops += 1

        labels = ', '.join(
            f"{d['class']} ({d.get('confidence', d.get('score', 0)):.0%})"
            for d in detections
        )
        self.log.warning(f"Vision override [{category}] — detected: [{labels}]")

        if category == 'proximity_hard':
            self.log.warning("Very close object in frame — hard stop + brief backoff")
            self.hw['backward'](18)
            time.sleep(0.35)
            self.hw['stop']()
        elif category == 'proximity':
            self.log.info("Close/large object in frame — stopping and rescanning")

        # Quick forward-sector scan so A* has fresh obstacle data
        self.log.info("Quick forward scan after vision override…")
        self.mapper.quick_scan(self.hw, angle_min=-60, angle_max=60)

        # Set short cooldown so persistent camera view doesn't trigger every cycle.
        self._vision_cooldown_until = time.time() + VISION_RETRIGGER_COOLDOWN_S

        self.log.info("Vision override handled — replanning")

    def _print_summary(self):
        elapsed = time.time() - self.start_time if self.start_time else 0
        car_pos = (self.mapper.car_x, self.mapper.car_y)
        dist = heuristic(car_pos, self.goal)

        self.log.info("")
        self.log.info("=" * 60)
        self.log.info("SELF-DRIVING SESSION SUMMARY")
        self.log.info(f"  Result        : {'GOAL REACHED' if self.reached_goal else 'DID NOT REACH GOAL'}")
        self.log.info(f"  Elapsed       : {elapsed:.1f} s")
        self.log.info(f"  Final position: {car_pos}")
        self.log.info(f"  Distance left : {dist:.1f} cells")
        self.log.info(f"  Total scans   : {self.total_scans}")
        self.log.info(f"  Total replans : {self.total_replans}")
        self.log.info(f"  Vision stops  : {self.total_vision_stops}")
        self.log.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="PiCar Full Self-Driving Controller (Step 2.4)")
    parser.add_argument(
        "--goal", type=str, default=None,
        help="Goal coordinates as x,y (e.g. '70,65'). "
             "Default: 20 cells ahead of start.")
    parser.add_argument(
        "--clearance", type=int, default=CLEARANCE_RADIUS,
        help=f"Obstacle inflation radius (default: {CLEARANCE_RADIUS})")
    parser.add_argument(
        "--rescan", type=int, default=RESCAN_EVERY_N_STEPS,
        help=f"Rescan every N steps (default: {RESCAN_EVERY_N_STEPS})")
    parser.add_argument(
        "--max-time", type=float, default=None,
        help="Maximum run time in seconds (default: unlimited)")
    parser.add_argument(
        "--detector", type=str, default='auto',
        choices=['auto', 'mediapipe', 'vilib', 'mock'],
        help="Object detection backend (default: auto)")
    parser.add_argument(
        "--yes", "-y", action='store_true',
        help="Skip the 'Ready to start?' confirmation prompt")
    args = parser.parse_args()

    # Get hardware
    hw = get_hardware()
    is_mock = hw['is_mock']

    if is_mock:
        print("[INFO] Running in MOCK mode (PC development)")
        print("[INFO] Hardware calls will be simulated.\n")
        max_time = args.max_time or 15  # limit mock runs
        detector_method = 'mock'
    else:
        print("[INFO] Running on Raspberry Pi — the car WILL move!")
        if not args.yes:
            confirm = input("Ready to start? (y/n): ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                return
        max_time = args.max_time
        detector_method = args.detector

    # Parse goal
    if args.goal:
        parts = args.goal.split(",")
        goal = (int(parts[0].strip()), int(parts[1].strip()))
    else:
        # Default: 20 cells forward (+x direction) from centre
        goal = (MAP_SIZE // 2 + 20, MAP_SIZE // 2 + 15)
        print(f"[INFO] No goal specified, using default: {goal}")

    # Create and run
    car = SelfDrivingCar(
        hw=hw,
        goal=goal,
        clearance=args.clearance,
        rescan_interval=args.rescan,
        detector_method=detector_method,
    )
    car.run(max_time=max_time)


if __name__ == "__main__":
    main()
