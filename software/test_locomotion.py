"""
Test script for car locomotion.
This script tests basic movement capabilities and can run on both PC (with mocks) and Raspberry Pi (with real hardware).

Based on the lab requirements, this tests:
- Forward/backward movement
- Servo control (for ultrasonic sensor rotation)
- Ultrasonic distance sensing
- Basic obstacle avoidance logic
"""

import time
import sys
from hardware_mock import get_hardware, get_picar_components

def test_forward_movement(hw, duration=2):
    """Test forward movement"""
    print("\n=== Testing Forward Movement ===")
    print(f"Moving forward for {duration} seconds...")
    
    hw['forward'](50)  # 50% power - matches picar-4wd API
    time.sleep(duration)
    hw['stop']()
    
    print("Forward movement test complete!\n")

def test_servo_movement(hw):
    """Test servo rotation"""
    print("\n=== Testing Servo Movement ===")
    
    angles = [0, 45, 90, -45, -90, 0]
    for angle in angles:
        print(f"Setting servo to {angle} degrees")
        hw['servo'].set_angle(angle)
        time.sleep(0.5)
    
    print("Servo movement test complete!\n")

def test_ultrasonic_sensor(hw, num_readings=5):
    """Test ultrasonic sensor readings"""
    print("\n=== Testing Ultrasonic Sensor ===")
    
    distances = []
    us = hw['ultrasonic']
    for i in range(num_readings):
        # Use get_distance() which matches picar-4wd API
        if hasattr(us, 'get_distance'):
            distance = us.get_distance()
        else:
            distance = us.read()  # Fallback for mock compatibility
        distances.append(distance)
        time.sleep(0.2)
    
    avg_distance = sum(distances) / len(distances)
    print(f"Average distance: {avg_distance:.2f} cm")
    print("Ultrasonic sensor test complete!\n")
    return distances

def test_obstacle_avoidance(hw):
    """Test basic obstacle avoidance logic (as described in Step 4 of Part 1)"""
    print("\n=== Testing Obstacle Avoidance Logic ===")
    print("This simulates the Roomba-like behavior from the lab requirements.")
    
    obstacle_threshold = 20  # cm - stop when object is this close
    us = hw['ultrasonic']
    
    for i in range(5):
        # Use get_distance() which matches picar-4wd API
        if hasattr(us, 'get_distance'):
            distance = us.get_distance()
        else:
            distance = us.read()  # Fallback for mock compatibility
        
        if distance < obstacle_threshold:
            print(f"[WARNING] Obstacle detected at {distance} cm! Stopping...")
            hw['stop']()
            time.sleep(0.5)
            
            print("Backing up...")
            if 'backward' in hw:
                hw['backward'](30)
            else:
                print("[MOCK] Would back up here")
            time.sleep(0.5)
            hw['stop']()
            
            print("Choosing new direction and turning...")
            # Simulate choosing a random direction
            import random
            direction = random.choice(['left', 'right'])
            print(f"Turning {direction}...")
            if direction == 'left' and 'turn_left' in hw:
                hw['turn_left'](30)
            elif direction == 'right' and 'turn_right' in hw:
                hw['turn_right'](30)
            time.sleep(0.5)
            hw['stop']()
        else:
            print(f"[OK] Clear path ({distance} cm). Moving forward...")
            hw['forward'](30)
            time.sleep(0.3)
            hw['stop']()
        
        time.sleep(0.2)
    
    print("Obstacle avoidance test complete!\n")

def test_servo_scan(hw):
    """Test scanning environment with servo-mounted ultrasonic (for mapping)"""
    print("\n=== Testing Servo Scanning (for mapping) ===")
    print("This simulates the scanning behavior needed for Step 4 mapping.")
    
    # Scan from -90 to +90 degrees
    angles = range(-90, 91, 15)  # Every 15 degrees
    distances = []
    
    servo = hw['servo']
    us = hw['ultrasonic']
    
    for angle in angles:
        servo.set_angle(angle)
        time.sleep(0.1)  # Wait for servo to move
        # Use get_distance() which matches picar-4wd API
        if hasattr(us, 'get_distance'):
            distance = us.get_distance()
        else:
            distance = us.read()  # Fallback for mock compatibility
        distances.append((angle, distance))
        print(f"  Angle {angle}°: {distance} cm")
    
    # Return to center
    servo.set_angle(0)
    
    print(f"\nScan complete. Found {len([d for _, d in distances if d < 30])} obstacles within 30cm")
    print("Servo scanning test complete!\n")
    return distances

def main():
    """Main test function"""
    print("=" * 50)
    print("PiCar Locomotion Test Script")
    print("=" * 50)
    
    # Get hardware interface (auto-detects PC vs Pi)
    hw = get_hardware()
    
    if hw['is_mock']:
        print("\n[INFO] Running in MOCK mode (PC development)")
        print("Hardware calls will be simulated.\n")
    else:
        print("\n[INFO] Running on Raspberry Pi with real hardware")
        print("Be careful - the car will actually move!\n")
    
    # Wait a moment for user to read
    time.sleep(2)
    
    try:
        # Run basic component tests
        print("\nRunning basic component tests...")
        test_servo_movement(hw)
        test_ultrasonic_sensor(hw, num_readings=3)
        
        # Test servo scanning (important for mapping)
        test_servo_scan(hw)
        
        # Test obstacle avoidance logic
        test_obstacle_avoidance(hw)
        
        # Movement tests (only on real hardware with confirmation)
        if not hw['is_mock']:
            print("\n[WARNING] REAL HARDWARE DETECTED [WARNING]")
            response = input("Test actual forward movement? (y/n): ")
            if response.lower() == 'y':
                duration = input("Duration in seconds (default 2): ")
                try:
                    duration = float(duration) if duration else 2.0
                except:
                    duration = 2.0
                test_forward_movement(hw, duration=duration)
        else:
            print("\n[MOCK MODE] Skipping actual movement test")
            print("Movement would be tested on Raspberry Pi with real hardware")
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Review the test outputs above")
        print("2. Implement your mapping algorithm (Step 4)")
        print("3. Implement obstacle avoidance (Step 4)")
        print("4. Push to git and test on Raspberry Pi")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        hw['forward'].stop()
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError during testing: {e}")
        hw['forward'].stop()
        sys.exit(1)

if __name__ == "__main__":
    main()
