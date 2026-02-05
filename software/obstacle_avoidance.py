"""
Part 1, Step 4: Environment Scanning (Mapping) - Obstacle Avoidance
Roomba-like behavior: detect obstacles, back up, turn, continue

This implements the requirements from project.md:
- Use ultrasonic sensor to detect obstacles within threshold distance
- When obstacle detected: stop, back up, choose random direction, turn, continue forward
"""

import time
import random
import sys
from collections import deque
from hardware_mock import get_hardware

# Configuration
OBSTACLE_THRESHOLD = 20  # cm - stop when object is this close
BACKUP_TIME = 1.0       # seconds to back up
TURN_TIME = 0.5         # seconds to turn
FORWARD_POWER = 30      # Power level for forward movement
TURN_POWER = 30         # Power level for turning
CHECK_INTERVAL = 0.1    # seconds between distance checks

# Sensor validation
MIN_VALID_DISTANCE = 2   
MAX_VALID_DISTANCE = 400  
DISTANCE_FILTER_SIZE = 3  

# Stuck detection
STUCK_TIMEOUT = 2.0      
STUCK_DISTANCE_THRESHOLD = 3  

def validate_distance(distance):
    """
    Validate ultrasonic sensor reading.
    
    Args:
        distance: Raw sensor reading
    
    Returns:
        Valid distance or None if invalid
    """
    if distance is None:
        return None
    
    # Check if distance is in valid range
    if distance < MIN_VALID_DISTANCE or distance > MAX_VALID_DISTANCE:
        return None
    
    return distance


def obstacle_avoidance_loop(hw, run_time=60):
    """
    Main obstacle avoidance loop - Roomba-like behavior
    
    Args:
        hw: Hardware interface from get_hardware()
        run_time: How long to run (seconds), None for infinite
    """
    print("=" * 50)
    print("Starting Obstacle Avoidance (Roomba Mode)")
    print("=" * 50)
    print(f"Obstacle threshold: {OBSTACLE_THRESHOLD} cm")
    print(f"Press Ctrl+C to stop\n")
    
    start_time = time.time()
    us = hw['ultrasonic']
    
    # State tracking to prevent race conditions
    current_state = 'stopped'  # 'stopped', 'forward', 'avoiding'
    
    # Distance filtering for noise reduction
    distance_buffer = deque(maxlen=DISTANCE_FILTER_SIZE)
    
    # Print throttling
    print_counter = 0
    last_printed_distance = None
    
    # Stuck detection - track if distance hasn't changed (car likely stuck)
    stuck_detection_distance = None
    stuck_detection_start_time = None
    
    try:
        while True:
            # Check if we should stop based on run_time
            if run_time and (time.time() - start_time) > run_time:
                print("\nRun time completed. Stopping...")
                break
            
            # Read distance with error handling
            try:
                if hasattr(us, 'get_distance'):
                    raw_distance = us.get_distance()
                else:
                    raw_distance = us.read()
            except Exception as e:
                print(f"\n[WARNING] Sensor read error: {e}")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Validate distance reading
            valid_distance = validate_distance(raw_distance)
            
            if valid_distance is None:
                # Invalid reading, skip this iteration
                if print_counter % 10 == 0:
                    print(f"[WARNING] Invalid sensor reading: {raw_distance}     ", end='\r')
                print_counter += 1
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Add to buffer for smoothing
            distance_buffer.append(valid_distance)
            
            # Calculate filtered distance (median or average)
            if len(distance_buffer) >= 2:
                # Use median to reduce noise spikes
                sorted_distances = sorted(distance_buffer)
                distance = sorted_distances[len(sorted_distances) // 2]
            else:
                distance = valid_distance
            
            # Print distance (throttled - only every 5 iterations or if changed significantly)
            print_counter += 1
            if print_counter % 5 == 0 or last_printed_distance is None or abs(distance - last_printed_distance) > 5:
                print(f"Distance: {distance:6.1f} cm | State: {current_state:10s}", end='\r')
                last_printed_distance = distance
            
            # Stuck detection - check if car is stuck (distance not changing while moving forward)
            stuck_detected = False
            if current_state == 'forward':
                # Initialize stuck detection if first time in forward state
                if stuck_detection_distance is None:
                    stuck_detection_distance = distance
                    stuck_detection_start_time = time.time()
                else:
                    # Check if distance has changed significantly
                    distance_change = abs(distance - stuck_detection_distance)
                    
                    if distance_change > STUCK_DISTANCE_THRESHOLD:
                        # Distance changed, reset stuck detection
                        stuck_detection_distance = distance
                        stuck_detection_start_time = time.time()
                    else:
                        # Distance hasn't changed, check timeout
                        stuck_duration = time.time() - stuck_detection_start_time
                        if stuck_duration > STUCK_TIMEOUT:
                            stuck_detected = True
                            print(f"\n[STUCK] Distance unchanged ({distance:.1f} cm) for {stuck_duration:.1f}s - likely stuck!")
            else:
                # Reset stuck detection when not moving forward
                stuck_detection_distance = None
                stuck_detection_start_time = None
            
            # Check if obstacle detected OR stuck detected
            if distance < OBSTACLE_THRESHOLD or stuck_detected:
                # Only trigger avoidance if not already avoiding
                if current_state != 'avoiding':
                    if stuck_detected:
                        print(f"\n[STUCK] Car appears stuck - executing recovery!")
                    else:
                        print(f"\n[OBSTACLE] Detected at {distance:.1f} cm!")
                    current_state = 'avoiding'
                    
                    # Stop immediately and wait for motors to stop
                    print("  → Stopping...")
                    hw['stop']()
                    time.sleep(0.3)  # Longer delay to ensure motors fully stop
                    
                    # Back up
                    print("  → Backing up...")
                    hw['backward'](FORWARD_POWER)
                    time.sleep(BACKUP_TIME)
                    hw['stop']()
                    time.sleep(0.3)  # Ensure stop before turning
                    
                    # Choose random direction
                    direction = random.choice(['left', 'right'])
                    print(f"  → Turning {direction}...")
                    
                    if direction == 'left':
                        hw['turn_left'](TURN_POWER)
                    else:
                        hw['turn_right'](TURN_POWER)
                    
                    time.sleep(TURN_TIME)
                    hw['stop']()
                    time.sleep(0.3)  # Ensure stop before continuing
                    
                    # Clear distance buffer and stuck detection after avoidance maneuver
                    distance_buffer.clear()
                    stuck_detection_distance = None
                    stuck_detection_start_time = None
                    
                    print("  → Ready to continue...\n")
                    current_state = 'stopped'  # Will transition to forward on next iteration
            
            # Move forward if no obstacle and not currently avoiding
            elif current_state != 'avoiding':
                # Only send forward command if not already moving forward
                if current_state != 'forward':
                    hw['forward'](FORWARD_POWER)
                    current_state = 'forward'
            
            # Small delay between checks
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    finally:
        # Always stop motors when exiting
        hw['stop']()
        print("\nMotors stopped. Safe to exit.")

def main():
    """Main function"""
    # Get hardware interface (auto-detects PC vs Pi)
    hw = get_hardware()
    
    if hw['is_mock']:
        print("[INFO] Running in MOCK mode (PC development)")
        print("Hardware calls will be simulated.\n")
        run_time = 10  # Shorter for testing
    else:
        print("[INFO] Running on Raspberry Pi with REAL hardware")
        print("WARNING: The car will actually move!\n")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
        run_time = None  # Run until interrupted
    
    # Run obstacle avoidance
    obstacle_avoidance_loop(hw, run_time=run_time)

if __name__ == "__main__":
    main()
