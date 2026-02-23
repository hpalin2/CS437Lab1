"""
Part 2, Step 2.3: Self-Driving Navigation (Routing)

Implements A* pathfinding on the 2D occupancy grid produced by
advanced_mapping.py (Step 2.1).

Requirements (from project.md):
- Use A* (or derivation) to find shortest path from start to goal
- Treat the 100x100 numpy map as a graph (nodes = cells, edges = 4 directions)
- Add obstacle clearance so the car does not clip corners
- Periodically rescan and recompute the path while navigating

Key design choices:
- Heuristic: Euclidean distance (admissible, consistent)
- 4-connected grid (up / down / left / right)
- Obstacle inflation (configurable clearance radius)
- Path returned as list of (x, y) waypoints
"""

import heapq
import math
import numpy as np
import time
from advanced_mapping import (
    AdvancedMapper, OCCUPIED, FREE, UNKNOWN,
    MAP_SIZE, MAP_CENTER,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CLEARANCE_RADIUS = 3       # cells around each obstacle that are also blocked
RESCAN_EVERY_N_STEPS = 5   # rescan environment every N steps along the path
MOVE_STEP_CM = 10          # distance per step when following path (cm)
                           # With CELL_SIZE_CM=2, each grid cell = 2cm; 10cm ≈ 5 cells
TURN_SPEED = 30            # motor power for turning (%)
FORWARD_SPEED = 25         # motor power for forward steps (%)
STEP_DURATION = 0.4        # seconds to drive per step
TURN_DURATION = 0.4        # seconds per 90-degree turn

# Continuous sonar guard (navigation.py-style) — checked every ~50 ms while driving
SONAR_POLL_INTERVAL = 0.05  # seconds between reads during a drive step
SONAR_STOP_CM = 12          # stop immediately if anything closer than this
SONAR_MIN_VALID_CM = 5      # ignore readings ≤5 cm (chassis / mount)
# Reactive dodge on bump (mirrors navigation.py)
DODGE_BACKUP_SPEED = 30
DODGE_BACKUP_TIME  = 0.5    # seconds to reverse
DODGE_TURN_SPEED   = 30
DODGE_TURN_TIME    = 0.5    # seconds to turn (alternates left / right)


# ---------------------------------------------------------------------------
# Obstacle inflation
# ---------------------------------------------------------------------------
def inflate_obstacles(occupancy_map, radius=CLEARANCE_RADIUS):
    """
    Inflate (dilate) obstacles on the occupancy map so the A* planner
    keeps the car a safe distance from walls/obstacles.

    Args:
        occupancy_map: 2D numpy array (-1=unknown, 0=free, 1=occupied)
        radius: Number of cells to inflate around each obstacle

    Returns:
        inflated: Copy of the map with inflated obstacles (values same as input)
    """
    inflated = occupancy_map.copy()
    rows, cols = occupancy_map.shape

    # Find all obstacle cells
    obstacle_ys, obstacle_xs = np.where(occupancy_map == OCCUPIED)

    for oy, ox in zip(obstacle_ys, obstacle_xs):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                ny, nx = oy + dy, ox + dx
                if 0 <= ny < rows and 0 <= nx < cols:
                    # Euclidean check for circular inflation
                    if math.sqrt(dy * dy + dx * dx) <= radius:
                        if inflated[ny, nx] != OCCUPIED:
                            inflated[ny, nx] = OCCUPIED

    return inflated


# ---------------------------------------------------------------------------
# A* pathfinding
# ---------------------------------------------------------------------------
def heuristic(a, b):
    """Euclidean distance heuristic (admissible & consistent on a grid)."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def astar(occupancy_map, start, goal, allow_unknown=False):
    """
    A* search on a 2D occupancy grid.

    Args:
        occupancy_map: 2D numpy array (-1=unknown, 0=free, 1=occupied)
        start: (x, y) start position
        goal:  (x, y) goal position
        allow_unknown: If True, treat UNKNOWN cells as passable (risky but
                       useful when most of the map is unexplored).

    Returns:
        path: List of (x, y) from start to goal inclusive, or [] if no path.
    """
    rows, cols = occupancy_map.shape

    def passable(x, y):
        if not (0 <= x < cols and 0 <= y < rows):
            return False
        cell = occupancy_map[y, x]
        if cell == OCCUPIED:
            return False
        if cell == UNKNOWN and not allow_unknown:
            return False
        return True

    if not passable(*start):
        # If start is blocked (e.g. due to inflation), try to find nearest free
        start = _find_nearest_free(occupancy_map, start, allow_unknown)
        if start is None:
            return []

    if not passable(*goal):
        goal = _find_nearest_free(occupancy_map, goal, allow_unknown)
        if goal is None:
            return []

    # 4-connected neighbours (up, down, left, right)
    neighbours = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    open_set = []  # min-heap of (f_score, counter, (x, y))
    counter = 0    # tie-breaker so heapq never compares tuples
    heapq.heappush(open_set, (heuristic(start, goal), counter, start))

    came_from = {}
    g_score = {start: 0.0}
    closed = set()

    while open_set:
        _, _, current = heapq.heappop(open_set)

        if current == goal:
            return _reconstruct(came_from, current)

        if current in closed:
            continue
        closed.add(current)

        cx, cy = current
        for dx, dy in neighbours:
            nx, ny = cx + dx, cy + dy
            if not passable(nx, ny):
                continue
            neighbour = (nx, ny)
            if neighbour in closed:
                continue

            tentative_g = g_score[current] + 1.0  # uniform cost on grid

            if tentative_g < g_score.get(neighbour, float('inf')):
                g_score[neighbour] = tentative_g
                f = tentative_g + heuristic(neighbour, goal)
                came_from[neighbour] = current
                counter += 1
                heapq.heappush(open_set, (f, counter, neighbour))

    return []  # no path found


def _reconstruct(came_from, current):
    """Walk came_from back to start and return the full path."""
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def _find_nearest_free(occupancy_map, pos, allow_unknown=False):
    """
    BFS outward from *pos* to find the nearest passable cell.

    Returns:
        (x, y) of nearest free cell, or None.
    """
    rows, cols = occupancy_map.shape
    visited = set()
    queue = [pos]
    visited.add(pos)

    while queue:
        next_queue = []
        for (x, y) in queue:
            cell = occupancy_map[y, x] if (0 <= x < cols and 0 <= y < rows) else None
            if cell is not None and cell != OCCUPIED:
                if cell == FREE or (allow_unknown and cell == UNKNOWN):
                    return (x, y)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < cols and 0 <= ny < rows and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    next_queue.append((nx, ny))
        queue = next_queue

    return None


# ---------------------------------------------------------------------------
# Direction helpers
# ---------------------------------------------------------------------------
def direction_between(current, next_pos):
    """
    Return the heading angle (degrees) from *current* to *next_pos*.

    Convention (matches advanced_mapping.py):
        0°   = +x  (right on the grid)
        90°  = +y  (down on the grid — but we usually treat it as forward)
        etc.

    Returns:
        Angle in degrees [0, 360).
    """
    dx = next_pos[0] - current[0]
    dy = next_pos[1] - current[1]
    angle = math.degrees(math.atan2(dy, dx)) % 360
    return angle


def angle_difference(target, current):
    """
    Signed difference target - current, wrapped to [-180, 180].
    Positive → turn right, negative → turn left.
    """
    diff = (target - current + 180) % 360 - 180
    return diff


# ---------------------------------------------------------------------------
# Path simplification
# ---------------------------------------------------------------------------
def simplify_path(path):
    """
    Remove colinear intermediate waypoints so the car only needs to turn
    when the direction actually changes.

    Returns:
        Simplified list of (x, y) waypoints (always includes start & goal).
    """
    if len(path) <= 2:
        return list(path)

    simplified = [path[0]]
    for i in range(1, len(path) - 1):
        prev = path[i - 1]
        curr = path[i]
        nxt = path[i + 1]
        # Keep the point if the direction changes
        dx1, dy1 = curr[0] - prev[0], curr[1] - prev[1]
        dx2, dy2 = nxt[0] - curr[0], nxt[1] - curr[1]
        if (dx1, dy1) != (dx2, dy2):
            simplified.append(curr)
    simplified.append(path[-1])
    return simplified


# ---------------------------------------------------------------------------
# Path follower (integrates with hardware)
# ---------------------------------------------------------------------------
class PathFollower:
    """
    Follows a list of (x, y) waypoints using the car's motors.

    Integrates with:
    - AdvancedMapper  (Step 2.1) for rescanning
    - ObjectDetector  (Step 2.2) for vision overrides
    """

    def __init__(self, mapper, hw, detector=None, override=None):
        """
        Args:
            mapper:   AdvancedMapper instance
            hw:       Hardware dict from get_hardware()
            detector: ObjectDetector instance (optional, for vision)
            override: VisionOverride instance (optional)
        """
        self.mapper = mapper
        self.hw = hw
        self.detector = detector
        self.override = override
        self.current_heading = 0.0  # degrees, 0 = +x direction

    # ----- high-level navigate -------------------------------------------
    def navigate_to(self, goal, allow_unknown=True,
                    rescan_interval=RESCAN_EVERY_N_STEPS):
        """
        Plan a path to *goal* and drive there, rescanning periodically.

        Args:
            goal: (x, y) in map coordinates
            allow_unknown: Treat unknown cells as passable?
            rescan_interval: Rescan & replan every N steps

        Returns:
            True if goal reached, False otherwise.
        """
        print(f"\n{'='*60}")
        print(f"NAVIGATING to goal {goal}")
        print(f"  Car position : ({self.mapper.car_x}, {self.mapper.car_y})")
        print(f"  Car heading  : {self.current_heading:.0f}°")
        print(f"  Rescan every : {rescan_interval} steps")
        print(f"{'='*60}\n")

        steps_since_scan = rescan_interval  # force initial scan

        while True:
            start = (self.mapper.car_x, self.mapper.car_y)

            # Check if close enough to goal
            dist_to_goal = heuristic(start, goal)
            if dist_to_goal < 2.0:
                print(f"[NAV] Reached goal {goal}!")
                self.hw['stop']()
                return True

            # ---- periodic rescan + replan --------------------------------
            if steps_since_scan >= rescan_interval:
                print("[NAV] Scanning environment...")
                scan_data = self.mapper.scan_environment(self.hw, interpolate=True)
                self.mapper.update_map_from_scan(scan_data)
                steps_since_scan = 0

            # Inflate obstacles
            inflated = inflate_obstacles(self.mapper.get_map(),
                                         radius=CLEARANCE_RADIUS)

            # Plan path
            path = astar(inflated, start, goal,
                         allow_unknown=allow_unknown)

            if not path:
                print("[NAV] No path found! Trying with unknown cells passable...")
                path = astar(inflated, start, goal, allow_unknown=True)
                if not path:
                    print("[NAV] Still no path. Giving up.")
                    self.hw['stop']()
                    return False

            path = simplify_path(path)
            print(f"[NAV] Path has {len(path)} waypoints "
                  f"(distance ~{dist_to_goal:.0f} cells)")

            # ---- follow a chunk of the path ------------------------------
            steps_taken = 0
            for i in range(1, len(path)):
                # Vision override check
                if self._check_vision_override():
                    print("[NAV] Vision override active, waiting...")
                    self.hw['stop']()
                    while self._check_vision_override():
                        time.sleep(0.3)
                    print("[NAV] Vision override cleared, resuming")

                wp = path[i]
                self._move_to_waypoint(wp)
                steps_taken += 1
                steps_since_scan += 1

                # Time to rescan?
                if steps_since_scan >= rescan_interval:
                    break  # exit inner loop to rescan + replan

            # If we exited inner loop naturally, all waypoints done — check
            # goal again at top of while.

    # ----- private helpers -----------------------------------------------
    def _move_to_waypoint(self, waypoint):
        """
        Turn to face *waypoint* then drive one step forward.
        Returns True if a sonar bump occurred (caller should break + replan).
        """
        cx, cy = self.mapper.car_x, self.mapper.car_y
        desired_heading = direction_between((cx, cy), waypoint)
        delta = angle_difference(desired_heading, self.current_heading)

        # Turn if needed
        if abs(delta) > 10:
            self._turn(delta)

        # Drive forward — polls sonar continuously
        bumped = self._drive_forward_one_cell()

        if bumped:
            # Reactive dodge (backup + turn) before handing control back to A*
            self._reactive_dodge()
            return True  # signal to caller: break inner loop → replan

        # Update mapper's position
        self.mapper.car_x, self.mapper.car_y = waypoint
        self.current_heading = desired_heading
        return False

    def _turn(self, delta_deg):
        """
        Turn the car by *delta_deg* degrees.
        Positive = right, negative = left.
        """
        # Duration proportional to angle magnitude
        duration = TURN_DURATION * (abs(delta_deg) / 90.0)
        duration = max(0.1, min(duration, 1.5))

        if delta_deg > 0:
            self.hw['turn_right'](TURN_SPEED)
        else:
            self.hw['turn_left'](TURN_SPEED)
        time.sleep(duration)
        self.hw['stop']()
        time.sleep(0.1)

        self.current_heading = (self.current_heading + delta_deg) % 360

    def _read_sonar(self):
        """Single sonar read with validity filtering. Returns cm or None."""
        if self.hw.get('is_mock'):
            return None
        us = self.hw.get('ultrasonic')
        if us is None:
            return None
        try:
            d = us.get_distance() if hasattr(us, 'get_distance') else us.read()
            if d is not None and SONAR_MIN_VALID_CM < d < 400:
                return d
        except Exception:
            pass
        return None

    def _drive_forward_one_cell(self):
        """
        Drive forward one step, polling the sonar every 50 ms (navigation.py style).
        Returns True if an obstacle was hit mid-step (caller should dodge + replan).
        """
        self.hw['forward'](FORWARD_SPEED)
        deadline = time.time() + STEP_DURATION
        bumped = False
        while time.time() < deadline:
            d = self._read_sonar()
            if d is not None and d < SONAR_STOP_CM:
                self.hw['stop']()
                bumped = True
                break
            time.sleep(SONAR_POLL_INTERVAL)
        self.hw['stop']()
        time.sleep(0.05)
        return bumped

    def _reactive_dodge(self):
        """
        Roomba-style dodge when sonar detects a close obstacle mid-drive:
        reverse briefly, turn away (alternating L/R), then let the caller
        trigger a rescan + A* replan.
        """
        direction = 'left' if getattr(self, '_last_dodge_dir', 'right') == 'right' else 'right'
        self._last_dodge_dir = direction

        self.hw['backward'](DODGE_BACKUP_SPEED)
        time.sleep(DODGE_BACKUP_TIME)
        self.hw['stop']()
        time.sleep(0.1)

        if direction == 'left':
            self.hw['turn_left'](DODGE_TURN_SPEED)
        else:
            self.hw['turn_right'](DODGE_TURN_SPEED)
        time.sleep(DODGE_TURN_TIME)
        self.hw['stop']()
        time.sleep(0.1)

    def _check_vision_override(self):
        """Return True if vision says we must stop."""
        if self.detector is None or self.override is None:
            return False

        detections = self.detector.detect_objects()
        person = any(d['class'] == 'person' for d in detections)
        stop_sign = any('stop sign' in d['class'] for d in detections)
        self.override.update(person, stop_sign, time.time())
        return self.override.should_stop()


# ---------------------------------------------------------------------------
# Visualisation helpers (ASCII + optional OpenCV)
# ---------------------------------------------------------------------------
def visualize_path_ascii(occupancy_map, path, start, goal,
                         car_pos=None, map_size=MAP_SIZE):
    """
    Print a compact ASCII view of the map with the planned path overlaid.
    Only shows the region that contains the path (±5 cell margin).
    """
    if not path:
        print("[VIS] No path to display.")
        return

    # Determine bounding box of interesting region
    all_pts = list(path) + [start, goal]
    if car_pos:
        all_pts.append(car_pos)
    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    margin = 5
    x_min = max(0, min(xs) - margin)
    x_max = min(map_size - 1, max(xs) + margin)
    y_min = max(0, min(ys) - margin)
    y_max = min(map_size - 1, max(ys) + margin)

    path_set = set(path)
    print(f"\nMap region [{x_min}:{x_max}, {y_min}:{y_max}]  "
          f"S=start  G=goal  *=path  #=obstacle  .=free  ?=unknown")
    print("+" + "-" * (x_max - x_min + 1) + "+")

    for y in range(y_min, y_max + 1):
        row = "|"
        for x in range(x_min, x_max + 1):
            if car_pos and (x, y) == car_pos:
                row += "C"
            elif (x, y) == start:
                row += "S"
            elif (x, y) == goal:
                row += "G"
            elif (x, y) in path_set:
                row += "*"
            elif occupancy_map[y, x] == OCCUPIED:
                row += "#"
            elif occupancy_map[y, x] == FREE:
                row += "."
            else:
                row += "?"
            
        row += "|"
        print(row)

    print("+" + "-" * (x_max - x_min + 1) + "+")
    print(f"Path length: {len(path)} cells\n")


# ---------------------------------------------------------------------------
# Standalone test / demo
# ---------------------------------------------------------------------------
def test_astar():
    """
    Run A* on a synthetic map and print the result.
    Can run on PC (no hardware needed).
    """
    print("=" * 60)
    print("A* Pathfinding Test")
    print("=" * 60)

    # --- build a small test map with known obstacles -----------------------
    size = 30
    test_map = np.full((size, size), FREE, dtype=np.int8)

    # Horizontal wall with a gap
    for x in range(5, 25):
        if x != 15:  # leave a gap at x=15
            test_map[15, x] = OCCUPIED

    # Vertical wall
    for y in range(5, 15):
        test_map[y, 20] = OCCUPIED

    # Small block
    for y in range(8, 12):
        for x in range(8, 12):
            test_map[y, x] = OCCUPIED

    start = (3, 3)
    goal = (27, 27)

    print(f"\nMap size    : {size}x{size}")
    print(f"Start       : {start}")
    print(f"Goal        : {goal}")
    print(f"Clearance   : {CLEARANCE_RADIUS} cells")

    # --- inflate obstacles -------------------------------------------------
    inflated = inflate_obstacles(test_map, radius=CLEARANCE_RADIUS)
    print(f"Obstacles (raw)     : {int(np.sum(test_map == OCCUPIED))}")
    print(f"Obstacles (inflated): {int(np.sum(inflated == OCCUPIED))}")

    # --- run A* ------------------------------------------------------------
    t0 = time.time()
    path = astar(inflated, start, goal, allow_unknown=False)
    dt = time.time() - t0

    if path:
        simplified = simplify_path(path)
        print(f"\nPath found!  {len(path)} cells  "
              f"({len(simplified)} waypoints after simplification)")
        print(f"Computation time: {dt*1000:.1f} ms")
        visualize_path_ascii(inflated, path, start, goal, map_size=size)
    else:
        print("\nNo path found!")

    # --- test with no path -------------------------------------------------
    print("\n--- Test: blocked goal ---")
    blocked_map = np.full((10, 10), FREE, dtype=np.int8)
    # Wall around goal
    for x in range(6, 10):
        blocked_map[6, x] = OCCUPIED
    for y in range(6, 10):
        blocked_map[y, 6] = OCCUPIED

    path2 = astar(blocked_map, (0, 0), (8, 8), allow_unknown=False)
    print(f"Path to walled-off goal: {'Found' if path2 else 'Not found (correct)'}")

    # --- test with unknown cells -------------------------------------------
    print("\n--- Test: unknown cells ---")
    unk_map = np.full((10, 10), UNKNOWN, dtype=np.int8)
    unk_map[0, 0] = FREE
    unk_map[9, 9] = FREE

    path3 = astar(unk_map, (0, 0), (9, 9), allow_unknown=False)
    print(f"Path through unknowns (disallowed): {'Found' if path3 else 'Not found (correct)'}")

    path4 = astar(unk_map, (0, 0), (9, 9), allow_unknown=True)
    print(f"Path through unknowns (allowed)   : {'Found' if path4 else 'Not found'}")

    print("\n" + "=" * 60)
    print("A* pathfinding test complete!")
    print("=" * 60)


def test_with_mapper():
    """
    Integration test: use AdvancedMapper to scan (mock), then plan a path.
    """
    from hardware_mock import get_hardware

    print("\n" + "=" * 60)
    print("A* + Mapping Integration Test")
    print("=" * 60)

    hw = get_hardware()
    mapper = AdvancedMapper(map_size=MAP_SIZE)

    print(f"\nHardware: {'mock' if hw['is_mock'] else 'real'}")
    print(f"Map size: {MAP_SIZE}x{MAP_SIZE}")
    print(f"Car at  : ({mapper.car_x}, {mapper.car_y})")

    # Scan environment
    print("\n--- Scanning environment ---")
    scan_data = mapper.scan_environment(hw, interpolate=True)
    mapper.update_map_from_scan(scan_data)

    # Pick a goal
    goal = (mapper.car_x + 20, mapper.car_y + 15)
    goal = (min(goal[0], MAP_SIZE - 1), min(goal[1], MAP_SIZE - 1))
    start = (mapper.car_x, mapper.car_y)

    print(f"\nPlanning path: {start} -> {goal}")

    # Inflate + plan
    inflated = inflate_obstacles(mapper.get_map(), radius=CLEARANCE_RADIUS)
    path = astar(inflated, start, goal, allow_unknown=True)

    if path:
        simplified = simplify_path(path)
        print(f"Path found: {len(path)} cells ({len(simplified)} waypoints)")
        visualize_path_ascii(inflated, path, start, goal,
                             car_pos=start, map_size=MAP_SIZE)
    else:
        print("No path found (mock sensors may not produce obstacles)")

    # Quick PathFollower demo (won't actually drive in mock mode)
    print("\n--- PathFollower demo (mock, 3 steps max) ---")
    follower = PathFollower(mapper, hw)
    if path and len(path) > 1:
        demo_path = simplify_path(path)
        for i, wp in enumerate(demo_path[1:4]):  # first 3 waypoints only
            print(f"  Step {i+1}: moving to {wp}")
            follower._move_to_waypoint(wp)
        print("  (stopped after 3 demo steps)")
    else:
        print("  (no path to follow)")

    hw['stop']()
    print("\n" + "=" * 60)
    print("Integration test complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_astar()
    test_with_mapper()
