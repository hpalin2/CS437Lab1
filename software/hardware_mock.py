"""
Hardware mock module for PC development.
This allows you to develop and test code on your PC without Raspberry Pi hardware.
On the Raspberry Pi, this uses the actual picarx library (PiCar-X).

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
        self._last_printed = None  # only print on significant angle changes
    
    def set_angle(self, angle):
        """Mock servo angle setting - silent during sweeps, prints at landmarks."""
        self.angle = angle
        # Only print when angle changes by ≥5° to avoid flooding output during sweeps
        if self._last_printed is None or abs(angle - self._last_printed) >= 5:
            print(f"[MOCK] Servo → {angle}°")
            self._last_printed = angle
        # No sleep — mock mode should run at full speed
    
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
    On PC: returns mock objects.
    On Pi: uses PiCar-X (picarx), falls back to mocks if unavailable.

    Usage:
        hw = get_hardware()
        hw['forward'](50)
        hw['turn_left'](30)
        hw['servo'].set_angle(90)
        distance = hw['ultrasonic'].read()
    """
    if is_raspberry_pi():
        # Try PiCar-X first (your hardware)
        # Check system Python paths for picarx (may be installed for Python 3.13)
        try:
            import sys
            import warnings
            # Suppress pyaudio warnings (not critical for basic functionality)
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=UserWarning)
                # Try to import picarx from venv first, then fall back to system paths
                try:
                    from picarx import Picarx
                except ImportError as e:
                    if 'pyaudio' in str(e).lower() or '_portaudio' in str(e).lower():
                        # pyaudio error in venv's picarx - set env flag and retry
                        import os
                        os.environ['PYAUDIO_IGNORE_ERRORS'] = '1'
                        from picarx import Picarx
                    else:
                        # picarx not in venv - try system package paths as fallback
                        system_paths = [
                            '/usr/local/lib/python3.13/dist-packages',
                            '/usr/local/lib/python3.12/dist-packages',
                            '/usr/local/lib/python3.11/dist-packages',
                            '/usr/lib/python3/dist-packages',
                        ]
                        for path in system_paths:
                            if path not in sys.path:
                                sys.path.append(path)  # append, not insert, to preserve venv priority
                        try:
                            from picarx import Picarx
                        except ImportError as e2:
                            if 'pyaudio' in str(e2).lower() or '_portaudio' in str(e2).lower():
                                import os
                                os.environ['PYAUDIO_IGNORE_ERRORS'] = '1'
                                from picarx import Picarx
                            else:
                                raise
                
                # Try to create Picarx instance (may fail due to GPIO permissions)
                try:
                    px = Picarx()
                except Exception as gpio_error:
                    # GPIO access error - this is OK, we can still use the module
                    # The hardware_mock will handle this gracefully
                    if 'gpio' in str(gpio_error).lower() or 'pin factory' in str(gpio_error).lower():
                        print(f"[INFO] picar-x found but GPIO access issue: {gpio_error}")
                        print("[INFO] This is normal - hardware access requires GPIO permissions")
                        print("[INFO] For now, continuing with mock hardware")
                        raise ImportError("GPIO access required for picar-x")  # Will fall through to mocks
                    else:
                        raise
            
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
            print("Warning: Running on Pi but picarx not found. Using mocks instead.")
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
