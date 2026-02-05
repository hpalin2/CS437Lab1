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
from hardware_mock import get_hardware

# Configuration
OBSTACLE_THRESHOLD = 20  # cm - stop when object is this close
BACKUP_TIME = 1.0       # seconds to back up
TURN_TIME = 0.5         # seconds to turn
FORWARD_POWER = 30      # Power level for forward movement
TURN_POWER = 30         # Power level for turning
CHECK_INTERVAL = 0.1    # seconds between distance checks

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
    
    try:
        while True:
            # Check if we should stop based on run_time
            if run_time and (time.time() - start_time) > run_time:
                print("\nRun time completed. Stopping...")
                break
            
            # Check distance ahead
            if hasattr(us, 'get_distance'):
                distance = us.get_distance()
            else:
                distance = us.read()
            
            print(f"Distance: {distance} cm", end='\r')
            
            # Check if obstacle detected
            if distance < OBSTACLE_THRESHOLD:
                print(f"\n[OBSTACLE] Detected at {distance} cm!")
                
                # Stop immediately
                print("  → Stopping...")
                hw['stop']()
                time.sleep(0.2)
                
                # Back up
                print("  → Backing up...")
                hw['backward'](FORWARD_POWER)
                time.sleep(BACKUP_TIME)
                hw['stop']()
                time.sleep(0.2)
                
                # Choose random direction
                direction = random.choice(['left', 'right'])
                print(f"  → Turning {direction}...")
                
                if direction == 'left':
                    hw['turn_left'](TURN_POWER)
                else:
                    hw['turn_right'](TURN_POWER)
                
                time.sleep(TURN_TIME)
                hw['stop']()
                time.sleep(0.2)
                
                print("  → Continuing forward...\n")
            
            # Move forward if no obstacle
            else:
                hw['forward'](FORWARD_POWER)
            
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
