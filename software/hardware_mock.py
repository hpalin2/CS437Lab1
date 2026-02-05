"""
Hardware mock module for PC development.
This allows you to develop and test code on your PC without Raspberry Pi hardware.
On the Raspberry Pi, this will be replaced by the actual picar library (PiCar-X or PiCar-4WD).

This module provides a compatible interface that works with both:
- PiCar-4WD: Module-level API (fc.forward(), fc.turn_left(), etc.)
- PiCar-X: Instance-based API (px.forward(), px.set_dir_servo_angle(), etc.)

Your code will work on both PC (with mocks) and Raspberry Pi (with real hardware).
"""

import time
import sys
import random

class MockForward:
    """Mock forward control for testing on PC - matches picar-4wd forward API"""
    def __init__(self):
        self.power = 0
        self.is_moving = False
    
    def forward(self, power=50):
        """Mock forward movement - matches picar-4wd API"""
        self.power = power
        self.is_moving = True
        print(f"[MOCK] Moving forward at power: {power}%")
        time.sleep(0.1)
    
    def backward(self, power=50):
        """Mock backward movement"""
        self.power = -power
        self.is_moving = True
        print(f"[MOCK] Moving backward at power: {power}%")
        time.sleep(0.1)
    
    def stop(self):
        """Mock stop"""
        self.power = 0
        self.is_moving = False
        print("[MOCK] Stopped")
        time.sleep(0.1)
    
    def turn_left(self, power=50):
        """Mock left turn"""
        print(f"[MOCK] Turning left at power: {power}%")
        time.sleep(0.1)
    
    def turn_right(self, power=50):
        """Mock right turn"""
        print(f"[MOCK] Turning right at power: {power}%")
        time.sleep(0.1)

class MockServo:
    """Mock servo control for testing on PC - matches picar-4wd servo API"""
    def __init__(self):
        self.angle = 0
    
    def set_angle(self, angle):
        """Mock servo angle setting - matches picar-4wd API"""
        self.angle = angle
        print(f"[MOCK] Servo angle set to: {angle} degrees")
        time.sleep(0.05)
    
    def get_angle(self):
        """Get current servo angle"""
        return self.angle

class MockUltrasonic:
    """Mock ultrasonic sensor for testing on PC - matches picar-4wd ultrasonic API"""
    def __init__(self):
        self.distance = 100  # Default mock distance in cm
        self.base_distance = 50  # Base distance for simulation
    
    def get_distance(self):
        """Mock distance reading - matches picar-4wd API (uses get_distance(), not read())"""
        # Simulate realistic sensor readings with some noise
        noise = random.randint(-3, 3)
        distance = max(5, self.base_distance + noise)
        print(f"[MOCK] Ultrasonic reading: {distance} cm")
        return distance
    
    def read(self):
        """Alias for get_distance() for compatibility"""
        return self.get_distance()
    
    def set_base_distance(self, distance):
        """Set base distance for simulation (useful for testing different scenarios)"""
        self.base_distance = distance

def is_raspberry_pi():
    """Check if running on Raspberry Pi"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo:
                return True
    except:
        pass
    
    # Also check for common Pi indicators
    try:
        import RPi.GPIO as GPIO
        return True
    except:
        pass
    
    return False

def get_hardware():
    """
    Returns appropriate hardware interface based on platform.
    On PC: returns mock objects
    On Pi: tries PiCar-X first, then PiCar-4WD, then mocks
    
    Usage:
        hw = get_hardware()
        hw['forward'](50)              # Works on both PC and Pi
        hw['turn_left'](30)            # Works on both (maps to steering on PiCar-X)
        hw['servo'].set_angle(90)      # Works on both
        distance = hw['ultrasonic'].read()  # Works on both
    """
    if is_raspberry_pi():
        # Try PiCar-X first (your hardware)
        try:
            from picarx import Picarx
            px = Picarx()
            
            # Create wrapper functions for PiCar-X
            # PiCar-X uses steering servo for turning, not direct turn functions
            def turn_left_wrapper(power):
                px.set_dir_servo_angle(-30)  # Turn steering left
                px.forward(power)
            
            def turn_right_wrapper(power):
                px.set_dir_servo_angle(30)   # Turn steering right
                px.forward(power)
            
            # Create servo wrapper for camera pan (used for scanning)
            class PiCarXServoWrapper:
                def __init__(self, picarx_instance):
                    self.px = picarx_instance
                    self.angle = 0
                
                def set_angle(self, angle):
                    self.angle = angle
                    # Use camera pan servo for scanning (like ultrasonic servo in PiCar-4WD)
                    self.px.set_cam_pan_angle(angle)
                
                def get_angle(self):
                    return self.angle
            
            # Create ultrasonic wrapper
            class PiCarXUltrasonicWrapper:
                def __init__(self, picarx_instance):
                    self.px = picarx_instance
                
                def read(self):
                    return self.px.ultrasonic.read()
                
                def get_distance(self):
                    return self.px.ultrasonic.read()
            
            return {
                'px': px,  # The actual PiCar-X instance
                'forward': lambda p: px.forward(p),
                'backward': lambda p: px.backward(p),
                'turn_left': turn_left_wrapper,
                'turn_right': turn_right_wrapper,
                'stop': lambda: px.stop(),
                'servo': PiCarXServoWrapper(px),  # Wrapper for camera pan servo
                'ultrasonic': PiCarXUltrasonicWrapper(px),  # Wrapper for ultrasonic
                'is_mock': False,
                'hardware_type': 'picar-x'
            }
        except ImportError:
            # Try PiCar-4WD as fallback
            try:
                import picar_4wd as fc
                
                return {
                    'fc': fc,  # The actual picar_4wd module
                    'forward': lambda p: fc.forward(p),
                    'backward': lambda p: fc.backward(p),
                    'turn_left': lambda p: fc.turn_left(p),
                    'turn_right': lambda p: fc.turn_right(p),
                    'stop': lambda: fc.stop(),
                    'servo': fc.servo,  # Servo object from picar_4wd
                    'ultrasonic': fc.us,  # Ultrasonic object from picar_4wd
                    'is_mock': False,
                    'hardware_type': 'picar-4wd'
                }
            except ImportError as e:
                print(f"Warning: Running on Pi but neither picar-x nor picar-4wd found: {e}")
                print("Using mocks instead. Install picar-x or picar-4wd on Pi for real hardware.")
                return get_mock_hardware()
        except Exception as e:
            print(f"Warning: Error importing picar library: {e}")
            print("Using mocks instead.")
            return get_mock_hardware()
    else:
        return get_mock_hardware()

def get_mock_hardware():
    """Returns mock hardware for PC development"""
    mock_forward = MockForward()
    mock_servo = MockServo()
    mock_ultrasonic = MockUltrasonic()
    
    return {
        'px': None,  # Not available in mock mode
        'fc': None,  # Not available in mock mode
        'forward': lambda p: mock_forward.forward(p),
        'backward': lambda p: mock_forward.backward(p),
        'turn_left': lambda p: mock_forward.turn_left(p),
        'turn_right': lambda p: mock_forward.turn_right(p),
        'stop': lambda: mock_forward.stop(),
        'servo': mock_servo,
        'ultrasonic': mock_ultrasonic,
        'is_mock': True,
        'hardware_type': 'mock'
    }

# Convenience function to get hardware in a way that matches common picar-4wd usage
def get_picar_components():
    """
    Alternative interface that returns components in a way that matches
    common picar-4wd example code patterns.
    
    Usage (matches common picar examples):
        fc, servo, us = get_picar_components()
        fc.forward(50)
        servo.set_angle(90)
        distance = us.read()
    """
    hw = get_hardware()
    return hw['forward'], hw['servo'], hw['ultrasonic']
