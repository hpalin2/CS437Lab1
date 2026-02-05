"""
Part 2, Step 6: Advanced Mapping
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
MAP_SIZE = 100  # 100x100 grid (1cm per cell = 100cm x 100cm)
MAP_CENTER = MAP_SIZE // 2  # Car starts at center (50, 50)
SCAN_ANGLE_MIN = -90  # Minimum scan angle (degrees)
SCAN_ANGLE_MAX = 90   # Maximum scan angle (degrees)
SCAN_STEP = 15        # Degrees between scan points (15° = 13 points per scan)
SERVO_DELAY = 0.1     # Time to wait for servo to move (seconds)
MAX_DISTANCE = 100    # Maximum distance to consider (cm) - beyond this, ignore
OBSTACLE_THRESHOLD = 80  # Distance threshold for marking obstacles (cm) - only mark if distance <= this

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
        
        # Convert polar to Cartesian
        x = car_x + distance_cm * math.cos(total_angle_rad)
        y = car_y + distance_cm * math.sin(total_angle_rad)
        
        # Check bounds (map_size is exclusive, so valid range is [0, map_size))
        x_int = int(round(x))
        y_int = int(round(y))
        if 0 <= x_int < self.map_size and 0 <= y_int < self.map_size:
            return (x_int, y_int)
        return None
    
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
        
        scan_data = []
        angles = range(angle_min, angle_max + 1, step)
        
        print(f"Scanning from {angle_min}° to {angle_max}° (step: {step}°)...")
        
        for angle in angles:
            # Set servo angle
            servo.set_angle(angle)
            time.sleep(SERVO_DELAY)  # Wait for servo to move
            
            # Read distance
            if hasattr(us, 'get_distance'):
                distance = us.get_distance()
            else:
                distance = us.read()
            
            # Only add valid readings (skip invalid/no-return readings)
            if 0 < distance < MAX_DISTANCE:
                scan_data.append((angle, distance))
                print(f"  Angle {angle:3d}deg: {distance:5.1f} cm")
            else:
                # Invalid reading - skip it (don't mark as obstacle)
                print(f"  Angle {angle:3d}deg: {distance:5.1f} cm (invalid, skipping)")
        
        # Return servo to center
        servo.set_angle(0)
        time.sleep(SERVO_DELAY)
        
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
        print(f"Car position: ({self.car_x}, {self.car_y}), heading: {self.car_angle}deg")
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
        if distance_cm > 0:
            angle_rad = math.radians(self.car_angle)
            self.car_x += int(round(distance_cm * math.cos(angle_rad)))
            self.car_y += int(round(distance_cm * math.sin(angle_rad)))
            
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


def test_mapping():
    """Test the mapping system."""
    print("=" * 60)
    print("Advanced Mapping Test")
    print("=" * 60)
    
    # Get hardware interface
    hw = get_hardware()
    
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
    mapper = test_mapping()
