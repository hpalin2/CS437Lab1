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
# COCO-class behaviour groups
# EfficientDet-Lite (all variants) is trained on COCO-80.
# We split those 80 labels into three groups:
#
#   STOP_WAIT   → person is present; wait for them to clear before moving
#   TRAFFIC     → traffic rule; mandatory pause then continue same path
#   OBSTACLES   → static physical object; quick scan + reroute around it
#
# Anything not in any group is silently ignored (food, animals, etc.)
# ---------------------------------------------------------------------------
STOP_WAIT_CLASSES = {'person'}
TRAFFIC_CLASSES   = {'stop sign', 'traffic light'}

# Objects that should be mapped as obstacles and routed around.
# NOTE: only triggered when confidence AND bbox area thresholds are met.
OBSTACLE_CLASSES = {
    # Furniture / large indoor objects
    'chair', 'couch', 'bed', 'dining table', 'toilet',
    # Vehicles (if indoors, treat as obstacle)
    'car', 'truck', 'bus', 'motorcycle', 'bicycle',
    # Bags / luggage (common lab-floor hazard)
    'backpack', 'handbag', 'suitcase',
    # Bottles / cups on the floor
    'bottle', 'cup', 'bowl',
    # Large electronics
    'tv', 'laptop',
    # Other large objects
    'potted plant', 'vase', 'clock',
}

# ---------------------------------------------------------------------------
# Vision filtering thresholds — prevent false-positive loops
# ---------------------------------------------------------------------------
# Minimum confidence to act on each category
PERSON_CONFIDENCE_MIN   = 0.45   # safety-critical, lower threshold acceptable
TRAFFIC_CONFIDENCE_MIN  = 0.45   # traffic rules
OBSTACLE_CONFIDENCE_MIN = 0.55   # static objects: require stronger evidence

# Bounding-box area (pixels²) below which an obstacle is "background" / too far
# ~50×50 px at typical 320×240 capture. Ignored for person/traffic (safety).
OBSTACLE_BBOX_MIN_AREA  = 2500

# Cooldown in seconds after handling a detection of a given class — prevents
# infinite rescan loops on permanently-visible background objects (e.g. a TV
# mounted on the wall that is always in frame).
PERSON_COOLDOWN_S   =  0.0   # no cooldown — always react to people
TRAFFIC_COOLDOWN_S  = 12.0   # don't re-stop at same sign for 12 s
OBSTACLE_COOLDOWN_S = 30.0   # object already mapped; ignore for 30 s


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

        # Per-class cooldown timestamps — maps class label → expiry time.
        # Prevents infinite loops when a static object (e.g. wall-mounted TV)
        # is permanently visible in the camera frame.
        self._vision_cooldown: dict = {}   # {class_str: expiry_timestamp}

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

        Returns (should_stop, detections, category) where category is one of:
          'person'    — wait for person to clear
          'traffic'   — traffic sign/light (mandatory pause)
          'obstacle'  — static object; map it and reroute
          None        — nothing actionable detected

        Three-layer filter prevents infinite loops:
          1. Confidence threshold  — different minima per category
          2. Bounding-box area     — ignore tiny/far-away obstacle detections
          3. Per-class cooldown    — after handling, silence that class for N s
        """
        try:
            all_detections = self.detector.detect_objects()
            now = time.time()

            persons   = []
            traffics  = []
            obstacles = []

            for d in all_detections:
                cls   = d['class'].lower()
                conf  = d.get('confidence', d.get('score', 0.0))
                bbox  = d.get('bbox', (0, 0, 0, 0))
                area  = bbox[2] * bbox[3]          # w × h
                on_cd = now < self._vision_cooldown.get(cls, 0)

                if cls in STOP_WAIT_CLASSES:
                    if conf >= PERSON_CONFIDENCE_MIN and not on_cd:
                        persons.append(d)

                elif cls in TRAFFIC_CLASSES:
                    if conf >= TRAFFIC_CONFIDENCE_MIN and not on_cd:
                        traffics.append(d)

                elif cls in OBSTACLE_CLASSES:
                    # Extra area filter: tiny bbox → background object, ignore
                    if (conf >= OBSTACLE_CONFIDENCE_MIN
                            and area >= OBSTACLE_BBOX_MIN_AREA
                            and not on_cd):
                        obstacles.append(d)

            self.override.update(bool(persons), bool(traffics), now)

            if persons:
                return True, persons, 'person'
            if traffics:
                return True, traffics, 'traffic'
            if obstacles:
                return True, obstacles, 'obstacle'
            return False, all_detections, None

        except Exception as e:
            self.log.debug(f"Vision check error: {e}")
            return False, [], None

    def _handle_vision_override(self, detections, category):
        """
        Smart response based on what was detected.

        category == 'person'   → wait up to 10 s, reverse if stuck, then replan
        category == 'traffic'  → mandatory 3 s pause, then continue same path
        category == 'obstacle' → quick scan now; A* will route around it
        """
        self.hw['stop']()
        self.total_vision_stops += 1

        labels = ', '.join(
            f"{d['class']} ({d.get('confidence', d.get('score', 0)):.0%})"
            for d in detections
        )
        self.log.warning(f"Vision override [{category}] — detected: [{labels}]")

        if category == 'traffic':
            self.log.info("TRAFFIC SIGN/LIGHT — pausing 3 s then continuing on same path")
            time.sleep(3.0)

        elif category == 'person':
            self.log.info("PERSON detected — waiting up to 10 s for them to clear…")
            deadline = time.time() + 10.0
            while time.time() < deadline:
                still_blocked, _, _ = self._vision_check()
                if not still_blocked:
                    break
                time.sleep(0.3)
            else:
                self.log.warning("Person still present — reversing 0.5 s to create space")
                self.hw['backward'](20)
                time.sleep(0.5)
                self.hw['stop']()

        elif category == 'obstacle':
            self.log.info(f"STATIC OBSTACLE detected — scanning to map it")
            # No waiting needed — the object is already there; scan will
            # add it to the occupancy grid and A* will route around it.

        # Quick forward-sector scan so A* has fresh obstacle data
        self.log.info("Quick forward scan after vision override…")
        self.mapper.quick_scan(self.hw, angle_min=-60, angle_max=60)

        # Set per-class cooldown so we don't loop on the same detection
        now = time.time()
        if category == 'obstacle':
            for d in detections:
                cls = d['class'].lower()
                self._vision_cooldown[cls] = now + OBSTACLE_COOLDOWN_S
                self.log.debug(f"  Cooldown set for '{cls}' for {OBSTACLE_COOLDOWN_S:.0f} s")
        elif category == 'traffic':
            for d in detections:
                cls = d['class'].lower()
                self._vision_cooldown[cls] = now + TRAFFIC_COOLDOWN_S

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
