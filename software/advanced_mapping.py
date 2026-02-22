"""
Part 2, Step 2.1: Advanced Mapping
Implements non-probabilistic mapping using ultrasonic sensor scanning.

Requirements:
- Create 100x100 numpy array (1cm per cell) representing environment
- Scan surroundings with servo-mounted ultrasonic sensor
- Convert polar coordinates (angle, distance) to Cartesian (x, y)
- Store obstacles as 1's, free space as 0's
- Optional interpolation between scan points
- Track car position (localization)
"""

import numpy as np
import math
import time
from hardware_mock import get_hardware

# Configuration
MAP_SIZE = 100        # 100x100 grid (lab requirement: keep at 100)
CELL_SIZE_CM = 2      # Each cell = 2cm → grid covers 200cm x 200cm (2m x 2m)
MAP_CENTER = MAP_SIZE // 2  # Car starts at center (50, 50)
SCAN_ANGLE_MIN = -90  # Minimum scan angle (degrees)
SCAN_ANGLE_MAX = 90   # Maximum scan angle (degrees)
SCAN_STEP = 5         # Degrees between scan points (5° = 37 points per scan)
SERVO_STEP_DELAY = 0.02   # Seconds per 1° step during sweep (~20°/s — smooth but not sluggish)
SERVO_SETTLE_TIME = 0.15  # Extra settle pause after arriving at each scan angle (seconds)
MAX_DISTANCE = 200    # Maximum distance to consider (cm) - covers full 2m grid
OBSTACLE_THRESHOLD = 180 # Distance threshold for marking obstacles (cm)
SCAN_TILT_ANGLE = -2      # Tilt sensor slightly downward during scan (degrees, negative = down)
                          # Compensates for upward servo tilt; tune via calibrate_servo.py

# Occupancy states
UNKNOWN = -1  # Not yet observed
FREE = 0      # Observed and free
OCCUPIED = 1  # Observed and occupied (obstacle)

class AdvancedMapper:
    """
    Advanced mapping system that builds a 2D occupancy grid from ultrasonic scans.
    """
    
    def __init__(self, map_size=MAP_SIZE):
        """
        Initialize the mapper.
        
        Args:
            map_size: Size of the square map (map_size x map_size)
        """
        self.map_size = map_size
        self.map_center = map_size // 2
        # Use 3-state occupancy: unknown=-1, free=0, occupied=1
        self.occupancy_map = np.full((map_size, map_size), UNKNOWN, dtype=np.int8)
        
        # Car position (in map coordinates, starts at center)
        self.car_x = self.map_center
        self.car_y = self.map_center
        self.car_angle = 0  # Car's heading angle (0 = facing +x direction)
        
        # Scan history for interpolation
        self.scan_history = []
    
    def polar_to_cartesian(self, angle_deg, distance_cm, car_x=None, car_y=None, car_angle=None):
        """
        Convert polar coordinates (angle, distance) to Cartesian (x, y).
        
        Angle convention: 
        - 0° = forward (car's heading direction)
        - Positive angle = right (clockwise from forward)
        - Negative angle = left (counterclockwise from forward)
        
        This uses standard math convention where positive angle is counterclockwise,
        so we negate the angle to match the stated convention (right = positive).
        
        Args:
            angle_deg: Angle in degrees (0 = forward, positive = right, negative = left)
            distance_cm: Distance in centimeters
            car_x: Car's x position in map (default: current position)
            car_y: Car's y position in map (default: current position)
            car_angle: Car's heading angle in degrees (0 = +x direction)
        
        Returns:
            (x, y) tuple in map coordinates, or None if out of bounds
        """
        if car_x is None:
            car_x = self.car_x
        if car_y is None:
            car_y = self.car_y
        if car_angle is None:
            car_angle = self.car_angle
        
        # Convert angle to radians
        # Angle convention: positive = right, so we negate to match math convention
        # Math convention: positive = counterclockwise (left), so negate for right-positive
        total_angle_rad = math.radians(car_angle - angle_deg)
        
        # Convert polar to Cartesian (divide by CELL_SIZE_CM to convert cm → grid cells)
        x = car_x + (distance_cm / CELL_SIZE_CM) * math.cos(total_angle_rad)
        y = car_y + (distance_cm / CELL_SIZE_CM) * math.sin(total_angle_rad)
        
        # Check bounds (map_size is exclusive, so valid range is [0, map_size))
        x_int = int(round(x))
        y_int = int(round(y))
        if 0 <= x_int < self.map_size and 0 <= y_int < self.map_size:
            return (x_int, y_int)
        return None
    
    def _sweep_servo(self, servo, from_angle, to_angle):
        """
        Smoothly sweep servo from from_angle to to_angle one degree at a time.
        Always reads the servo's last-known position so there is no snapping.
        """
        if from_angle == to_angle:
            return
        direction = 1 if to_angle > from_angle else -1
        for a in range(from_angle + direction, to_angle + direction, direction):
            servo.set_angle(a)
            time.sleep(SERVO_STEP_DELAY)

    def scan_environment(self, hw, angle_min=SCAN_ANGLE_MIN, angle_max=SCAN_ANGLE_MAX, 
                        step=SCAN_STEP, interpolate=True):
        """
        Scan the environment using servo-mounted ultrasonic sensor.
        
        Args:
            hw: Hardware interface from get_hardware()
            angle_min: Minimum scan angle (degrees)
            angle_max: Maximum scan angle (degrees)
            step: Angle step between readings (degrees)
            interpolate: Whether to interpolate between scan points
        
        Returns:
            List of (angle, distance) tuples
        """
        servo = hw['servo']
        us = hw['ultrasonic']
        px = hw.get('px')  # PiCar-X instance for tilt control (None in mock mode)
        
        scan_data = []
        angles = list(range(angle_min, angle_max + 1, step))
        
        # Apply tilt correction if running on real hardware
        if px is not None:
            px.set_cam_tilt_angle(SCAN_TILT_ANGLE)
            time.sleep(0.2)
            print(f"Tilt set to {SCAN_TILT_ANGLE}° (downward compensation)")

        print(f"Scanning from {angle_min}° to {angle_max}° (step: {step}°)...")

        # Use the servo's last-known angle so we never snap to an assumed position.
        # servo.angle is set by every set_angle() call in both real and mock wrappers.
        current_angle = getattr(servo, 'angle', 0)

        # Smoothly move to start of scan range
        self._sweep_servo(servo, current_angle, angle_min)
        current_angle = angle_min
        time.sleep(SERVO_SETTLE_TIME)   # let vibration die before first reading
        
        for angle in angles:
            # Smoothly sweep to next measurement angle
            self._sweep_servo(servo, current_angle, angle)
            current_angle = angle
            time.sleep(SERVO_SETTLE_TIME)  # settle before reading

            # Take 3 readings and use median to reject outliers
            raw = []
            for _ in range(3):
                d = us.get_distance() if hasattr(us, 'get_distance') else us.read()
                if 0 < d < MAX_DISTANCE:
                    raw.append(d)
                time.sleep(0.05)
            
            if raw:
                distance = sorted(raw)[len(raw) // 2]  # median
                scan_data.append((angle, distance))
                print(f"  Angle {angle:3d}deg: {distance:5.1f} cm  (from {len(raw)} valid reads)")
            else:
                print(f"  Angle {angle:3d}deg:  no valid reading (skipping)")
        
        # Smoothly return servo to center and restore tilt
        self._sweep_servo(servo, current_angle, 0)
        time.sleep(SERVO_SETTLE_TIME)
        if px is not None:
            px.set_cam_tilt_angle(0)
        
        # Store scan history
        self.scan_history = scan_data
        
        # Interpolate if requested
        if interpolate:
            scan_data = self.interpolate_scan(scan_data, step)
        
        return scan_data
    
    def interpolate_scan(self, scan_data, step):
        """
        Interpolate between scan points to fill gaps.
        
        Args:
            scan_data: List of (angle, distance) tuples
            step: Original step size (for determining interpolation density)
        
        Returns:
            Interpolated list of (angle, distance) tuples
        """
        if len(scan_data) < 2:
            return scan_data
        
        interpolated = []
        
        for i in range(len(scan_data) - 1):
            angle1, dist1 = scan_data[i]
            angle2, dist2 = scan_data[i + 1]
            
            # Add original point
            interpolated.append((angle1, dist1))
            
            # Interpolate between points
            # Use smaller step for interpolation (e.g., every 5 degrees)
            interp_step = min(5, step // 2)
            num_points = abs(angle2 - angle1) // interp_step
            
            if num_points > 1:
                for j in range(1, num_points):
                    interp_angle = angle1 + j * interp_step * (1 if angle2 > angle1 else -1)
                    # Linear interpolation
                    t = j / num_points
                    interp_dist = dist1 + (dist2 - dist1) * t
                    interpolated.append((interp_angle, interp_dist))
        
        # Add last point
        if scan_data:
            interpolated.append(scan_data[-1])
        
        return interpolated
    
    def update_map_from_scan(self, scan_data, car_x=None, car_y=None, car_angle=None):
        """
        Update the occupancy map from scan data.
        
        Args:
            scan_data: List of (angle, distance) tuples
            car_x: Car's x position (default: current position)
            car_y: Car's y position (default: current position)
            car_angle: Car's heading angle (default: current angle)
        """
        if car_x is None:
            car_x = self.car_x
        if car_y is None:
            car_y = self.car_y
        if car_angle is None:
            car_angle = self.car_angle
        
        obstacles_found = 0
        
        for angle, distance in scan_data:
            # Gate obstacle marking: only mark if distance is within threshold
            if distance <= 0 or distance >= MAX_DISTANCE or distance > OBSTACLE_THRESHOLD:
                continue
            
            # Convert to Cartesian coordinates
            hit_pos = self.polar_to_cartesian(angle, distance, car_x, car_y, car_angle)
            
            if not hit_pos:
                continue
            
            x_hit, y_hit = hit_pos
            
            # Mark free space along the ray from car to (just before) hit
            # This marks all cells from car to obstacle as free
            self.mark_free_space(car_x, car_y, x_hit, y_hit)
            
            # Mark occupied at hit point
            if self.occupancy_map[y_hit, x_hit] != OCCUPIED:
                self.occupancy_map[y_hit, x_hit] = OCCUPIED
                obstacles_found += 1
        
        print(f"Map updated: {obstacles_found} new obstacles marked")
        return obstacles_found
    
    def mark_free_space(self, x1, y1, x2, y2):
        """
        Mark cells along the line from (x1, y1) to (x2, y2) as free space.
        Uses Bresenham's line algorithm.
        Marks all cells up to (but not including) the end point as free.
        
        Args:
            x1, y1: Start point (car position)
            x2, y2: End point (obstacle position - this cell is NOT marked as free)
        """
        # Bresenham's line algorithm
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        
        while not (x == x2 and y == y2):
            # Mark as free (but don't overwrite obstacles)
            if 0 <= x < self.map_size and 0 <= y < self.map_size:
                if self.occupancy_map[y, x] != OCCUPIED:
                    self.occupancy_map[y, x] = FREE
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
    
    def get_map(self):
        """
        Get the current occupancy map.
        
        Returns:
            2D numpy array (-1 = unknown, 0 = free, 1 = obstacle)
        """
        return self.occupancy_map.copy()
    
    def visualize_map(self, show_car=True):
        """
        Visualize the map as ASCII art.
        
        Args:
            show_car: Whether to show car position
        """
        print("\n" + "=" * (self.map_size + 2))
        print("Occupancy Map (-1=unknown, 0=free, 1=obstacle, C=car)")
        print("=" * (self.map_size + 2))
        
        obstacles = 0
        free_cells = 0
        unknown_cells = 0
        
        for y in range(self.map_size):
            line = "|"
            for x in range(self.map_size):
                if show_car and x == self.car_x and y == self.car_y:
                    line += "C"
                elif self.occupancy_map[y, x] == OCCUPIED:
                    line += "1"
                    obstacles += 1
                elif self.occupancy_map[y, x] == FREE:
                    line += "."
                    free_cells += 1
                else:  # UNKNOWN
                    line += "?"
                    unknown_cells += 1
            line += "|"
            print(line)
        
        print("=" * (self.map_size + 2))
        real_x = (self.car_x - self.map_center) * CELL_SIZE_CM
        real_y = (self.car_y - self.map_center) * CELL_SIZE_CM
        print(f"Car position: grid({self.car_x}, {self.car_y}) = real({real_x}cm, {real_y}cm), heading: {self.car_angle}deg")
        print(f"Grid: {self.map_size}x{self.map_size} cells @ {CELL_SIZE_CM}cm/cell = {self.map_size*CELL_SIZE_CM}cm x {self.map_size*CELL_SIZE_CM}cm coverage")
        print(f"Obstacles: {obstacles}, Free: {free_cells}, Unknown: {unknown_cells}")
        print()
    
    def update_car_position(self, distance_cm=0, delta_angle_deg=0):
        """
        Update car position based on movement (localization).
        
        This separates rotation and translation:
        1. First rotate by delta_angle_deg
        2. Then translate forward by distance_cm in the new heading
        
        Args:
            distance_cm: Distance to move forward in centimeters (after rotation)
            delta_angle_deg: Change in heading angle (positive = turn right, negative = turn left)
        """
        # Step 1: Update car angle (rotation)
        self.car_angle = (self.car_angle + delta_angle_deg) % 360
        
        # Step 2: Update car position (translation in new heading direction)
        # Divide by CELL_SIZE_CM to convert real-world cm → grid cells
        if distance_cm > 0:
            angle_rad = math.radians(self.car_angle)
            cells = distance_cm / CELL_SIZE_CM
            self.car_x += int(round(cells * math.cos(angle_rad)))
            self.car_y += int(round(cells * math.sin(angle_rad)))
            
            # Keep within bounds
            self.car_x = max(0, min(self.map_size - 1, self.car_x))
            self.car_y = max(0, min(self.map_size - 1, self.car_y))
    
    def clear_map(self):
        """Clear the occupancy map (reset to unknown)."""
        self.occupancy_map = np.full((self.map_size, self.map_size), UNKNOWN, dtype=np.int8)
        print("Map cleared (reset to unknown)")
    
    def save_map(self, filename="map.npy"):
        """Save map to file."""
        np.save(filename, self.occupancy_map)
        print(f"Map saved to {filename}")
    
    def load_map(self, filename="map.npy"):
        """Load map from file."""
        self.occupancy_map = np.load(filename)
        print(f"Map loaded from {filename}")


def init_hardware():
    """
    Initialize hardware ONCE per session.
    Call this at startup, then pass the returned hw dict to test_mapping().
    Avoids repeated Picarx() instantiation which triggers reset_mcu() and
    causes servos to snap to their MCU power-on default each time.
    """
    hw = get_hardware()
    if not hw['is_mock']:
        # reset_mcu() in Picarx.__init__ leaves servos in an unknown state.
        # Do a slow sweep back to center so recovery is smooth, not abrupt.
        px = hw['px']
        servo = hw['servo']
        print("[HW INIT] Slowly centering servos after MCU reset...")
        for angle in range(20, -1, -1):   # gentle approach from +20° → 0°
            px.set_cam_pan_angle(angle)
            time.sleep(0.03)
        servo.angle = 0
        px.set_cam_tilt_angle(0)
        time.sleep(0.3)
        print("[HW INIT] Servos centred.")
    return hw


def test_mapping(hw=None):
    """Test the mapping system."""
    print("=" * 60)
    print("Advanced Mapping Test")
    print("=" * 60)
    
    # Accept a pre-initialised hw dict so Picarx() isn't recreated each run
    if hw is None:
        hw = init_hardware()
    
    if hw['is_mock']:
        print("[INFO] Running in MOCK mode (PC development)")
        print("Map generation will be simulated.\n")
    else:
        print("[INFO] Running on Raspberry Pi with REAL hardware")
        print("Car will actually scan its environment!\n")
    
    # Create mapper
    mapper = AdvancedMapper()
    
    # Perform scan
    print("Performing environment scan...")
    scan_data = mapper.scan_environment(hw, interpolate=True)
    
    # Update map from scan
    print("\nUpdating map from scan data...")
    mapper.update_map_from_scan(scan_data)
    
    # Visualize map
    mapper.visualize_map(show_car=True)
    
    # Test coordinate conversion
    print("Testing coordinate conversion:")
    test_cases = [
        (0, 10),    # Forward 10cm
        (90, 20),   # Right 20cm
        (-90, 15),  # Left 15cm
        (45, 30),   # 45° right, 30cm
    ]
    
    for angle, dist in test_cases:
        pos = mapper.polar_to_cartesian(angle, dist)
        if pos:
            print(f"  Angle {angle:3d}deg, Distance {dist:3d}cm -> ({pos[0]}, {pos[1]})")
        else:
            print(f"  Angle {angle:3d}deg, Distance {dist:3d}cm -> Out of bounds")
    
    print("\n" + "=" * 60)
    print("Mapping test complete!")
    print("=" * 60)
    
    return mapper


if __name__ == "__main__":
    # Initialise hardware ONCE — avoids repeated MCU resets if you re-run
    # test_mapping() multiple times in the same session.
    hw = init_hardware()
    mapper = test_mapping(hw)
