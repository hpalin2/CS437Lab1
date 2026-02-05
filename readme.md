# PiCar IoT Lab - Software Development

This repository contains the software components for the IoT Lab 1 PiCar project.

**Your Hardware Configuration:**
- Raspberry Pi 5 (16 GB RAM)
- PiCar-X Car Chassis Kit
- Raspberry Pi Camera Module
- 64 GB microSD card

**Note**: This lab documentation primarily references PiCar-4WD, but you're using PiCar-X. The core concepts are the same, but library installation and some API calls may differ. See compatibility notes below.

## Quick Start

### On Your PC (Development)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test the setup:**
   ```bash
   python test_locomotion.py
   ```
   This will run in mock mode, simulating hardware calls.

3. **Develop your code:**
   - Use `hardware_mock.py` to get hardware interfaces
   - Your code will automatically work on both PC (mocks) and Pi (real hardware)

### On Raspberry Pi (Deployment)

1. **Install PiCar library:**
   
   **For PiCar-X (Your Hardware):**
   ```bash
   # PiCar-X uses different library - follow SunFounder instructions
   # Installation guide: https://docs.sunfounder.com/projects/picar-x/
   # You may need to use vilib for object detection instead of TensorFlow Lite
   ```
   
   **For PiCar-4WD (Reference):**
   ```bash
   cd picar-4wd
   sudo python3 setup.py install
   ```
   The setup script will install dependencies (gpiozero, smbus2, websockets) and configure I2C/SPI interfaces.
   
   **Note**: `setup.py` is **only for Raspberry Pi** - it configures GPIO, I2C, and SPI interfaces that don't exist on Windows. You don't need it on your laptop because `hardware_mock.py` provides the same interface without hardware.
   
   **PiCar-X Specific Notes**:
   - Ultrasonic sensor may be fixed (not on servo) - you may need to mount it on camera pan servo
   - Consider using `vilib` instead of TensorFlow Lite for object detection (easier on PiCar-X)
   - API may differ slightly - check PiCar-X documentation

2. **Pull your code:**
   ```bash
   git pull origin main
   ```

3. **Run tests (CAREFUL - CAR WILL MOVE!):**
   ```bash
   python3 test_locomotion.py
   ```

## Project Status & Progress

### ✅ Completed Setup
- ✅ Hardware mock system for PC development
- ✅ Test scripts for locomotion and sensors
- ✅ picar-4wd repository cloned (for reference - you're using PiCar-X)
- ✅ **PiCar-X installed and API compatibility verified**
- ✅ Hardware abstraction layer (works with both PiCar-4WD and PiCar-X APIs)
- ✅ Obstacle avoidance starter code (`obstacle_avoidance.py`)

### ⚠️ Hardware-Specific Notes
- **Raspberry Pi 5**: More powerful than Pi 4 - should handle object detection better
- **PiCar-X**: Different library than PiCar-4WD - need to install PiCar-X specific library on Pi
- **Camera**: Standard Raspberry Pi Camera Module - compatible with both Pi 4 and Pi 5

### ✅ Part 1, Step 4 - Obstacle Avoidance: COMPLETE
**Status**: ✅ Implemented and tested

**Requirements** (from `project.md`):
- ✅ Use ultrasonic sensor to detect obstacles within threshold distance (e.g., 20cm)
- ✅ When obstacle detected: stop, back up, choose random direction, turn, continue
- ✅ Roomba-like behavior

**What's done**:
- ✅ Basic obstacle avoidance code structure created
- ✅ Tested on laptop with mocks
- ✅ Ready for deployment to Pi

### ✅ Part 2, Step 6 - Advanced Mapping: COMPLETE & CORRECTED
**Status**: ✅ Implemented, tested, and corrected based on feedback

**Requirements** (from `project.md`):
- ✅ Create 100x100 numpy array (1cm per cell) representing environment
- ✅ Scan surroundings with servo-mounted ultrasonic sensor
- ✅ Convert polar coordinates (angle, distance) to Cartesian (x, y)
- ✅ **3-state occupancy grid**: unknown=-1, free=0, occupied=1
- ✅ **Proper free space marking** along rays from car to obstacles
- ✅ **Gated obstacle marking** (only marks real obstacles within threshold)
- ✅ Optional interpolation between scan points
- ✅ Track car position (localization support)

**What's done**:
- ✅ `advanced_mapping.py` created with full implementation
- ✅ **Fixed**: 3-state occupancy (unknown/free/occupied)
- ✅ **Fixed**: Free space properly marked along rays
- ✅ **Fixed**: Invalid readings skipped (no fake obstacles)
- ✅ **Fixed**: Angle convention clarified and consistent
- ✅ **Fixed**: Localization separates rotation and translation
- ✅ Coordinate transformation (polar to Cartesian)
- ✅ Map visualization (ASCII art with 3 states)
- ✅ Interpolation support
- ✅ Tested on laptop with mocks
- ✅ Ready for deployment to Pi

**Next actions**:
1. Test on Pi with real hardware
2. Integrate with A* routing (Step 8)
3. Add map visualization with OpenCV (optional enhancement)

### 📋 Upcoming Tasks

**Part 1 (After Step 4)**:
- Step 5: Set up obstacle course and test driving (needs Pi + real hardware)
- Create demo video and report

**Part 2 (Can develop on laptop NOW - no need to wait for Step 5)**:
- Step 6: Advanced mapping with numpy arrays ✅ **COMPLETE** - `advanced_mapping.py` created and tested
- Step 7: Object detection with MediaPipe ⏭️ **Next** - Can prepare code on laptop (needs Pi for camera testing)
- Step 8: A* routing algorithm ⏭️ **Next** - Can develop on laptop now
- Step 9: Full self-driving integration (needs Pi for final testing)

**Important**: You can develop Steps 6-8 on your laptop **right now** without completing Step 5. These are algorithm/logic tasks that work with mocks. Step 5 is just testing Part 1 on real hardware, which is separate from developing Part 2 algorithms.

## Project Structure

```
.
├── hardware_mock.py          # Hardware abstraction (mocks for PC, real on Pi)
├── test_locomotion.py         # Test script for locomotion and sensors
├── obstacle_avoidance.py     # Part 1, Step 4 - Roomba behavior (✅ created)
├── advanced_mapping.py       # Part 2, Step 6 - Advanced mapping (✅ created)
├── requirements.txt           # Python dependencies
├── picar-4wd/                # Cloned picar-4wd library (reference)
├── picar-x/                  # Installed PiCar-X library (your hardware)
│   ├── picarx/               # Main library code
│   └── example/              # Example scripts
├── advanced_mapping.py        # Part 2, Step 6 (✅ created)
├── object_detection.py        # Part 2, Step 7 (⏭️ to create)
├── astar_routing.py          # Part 2, Step 8 (⏭️ to create)
└── full_self_driving.py      # Part 2, Step 9 (⏭️ to create)
```

## PiCar Library Information

### ⚠️ Hardware Compatibility Note

**You're using PiCar-X, not PiCar-4WD!**

The repository at **https://github.com/sunfounder/picar-4wd** is for PiCar-4WD. For **PiCar-X**, you need different installation:

- **PiCar-X Documentation**: https://docs.sunfounder.com/projects/picar-x/
- **PiCar-X Installation**: Follow SunFounder's PiCar-X specific instructions
- **Object Detection**: Consider using `vilib` instead of TensorFlow Lite (easier on PiCar-X)
- **Ultrasonic Sensor**: On PiCar-X, the ultrasonic may be fixed. You may need to mount it on the camera pan servo for scanning.

**✅ Your `hardware_mock.py` has been updated** - it now supports both PiCar-X and PiCar-4WD! The hardware abstraction layer automatically detects which library is installed and provides a unified interface.

**See `API_COMPATIBILITY.md`** for detailed comparison of PiCar-X vs PiCar-4WD APIs.

### PiCar-4WD Reference (For Understanding)
The repository at **https://github.com/sunfounder/picar-4wd** is the official version for PiCar-4WD (reference only).

**Key Components**:
- `servo.py` - Servo control for ultrasonic sensor rotation
- `ultrasonic.py` - Distance sensing
- `motor.py` - Motor control
- Example scripts: `keyboard_control.py`, `obstacle_avoidance.py`

### API Structure

The picar-4wd API uses:
- **Functions**: `forward(power)`, `backward(power)`, `turn_left(power)`, `turn_right(power)`, `stop()`
- **Objects**: `servo` (Servo instance), `us` (Ultrasonic instance)

**Usage Example:**
```python
import picar_4wd as fc

fc.forward(50)              # Move forward at 50% power
fc.servo.set_angle(90)      # Set servo to 90 degrees
distance = fc.us.get_distance()  # Get distance reading
fc.stop()                   # Stop all motors
```

Your `hardware_mock.py` matches this API, so code works on both PC (mocks) and Pi (real hardware).

## Development Workflow

1. **Develop on PC** using mocks
2. **Test logic** without hardware
3. **Commit and push** to git
4. **Pull on Raspberry Pi** and test with real hardware

### What You Can Develop on Laptop vs Pi

**✅ Can Develop on Laptop (Algorithm/Logic) - No Pi Needed**:
- Step 4: Obstacle avoidance logic ✅
- Step 6: Advanced mapping algorithm (numpy arrays) ✅ **Start now!**
- Step 7: Object detection code structure (prepare OpenCV/TensorFlow pipeline) ✅ **Start now!**
- Step 8: A* routing algorithm ✅ **Start now!**
- All Python logic and algorithms

**⚠️ Needs Pi (Hardware-Specific)**:
- Step 5: Actual driving test (needs real car) - **Optional before Part 2**
- Step 7: Object detection testing (needs camera)
- Step 9: Final integration testing

**Key Point**: You don't need to complete Step 5 before starting Part 2 development. Steps 6-8 are independent algorithms you can develop on your laptop using mocks. Step 5 is just testing Part 1 on real hardware.

## Quick Commands

```bash
# Test obstacle avoidance on laptop
python obstacle_avoidance.py

# Test basic locomotion
python test_locomotion.py

# When ready, commit and push
git add .
git commit -m "Update: [describe changes]"
git push
```

## Key Features

- ✅ Automatic hardware detection (PC vs Pi)
- ✅ Mock hardware for PC development
- ✅ Compatible with picar-4wd API
- ✅ Test scripts for locomotion, sensors, and obstacle avoidance

## Tips for Success

1. **Start Simple**: Get basic obstacle avoidance working first
2. **Test on Laptop**: Use mocks to debug logic quickly
3. **Iterate**: Refine parameters (thresholds, timing) based on testing
4. **Read Examples**: Check `picar-4wd/examples/` for reference
5. **Document**: Keep notes on what works/doesn't work

## Hardware Configuration

**Your Setup**: Raspberry Pi 5 + PiCar-X (see **`HARDWARE_NOTES.md`** for details)
- Important differences from PiCar-4WD documentation
- PiCar-X specific installation instructions
- Compatibility notes and troubleshooting

## System Architecture

For a detailed explanation of how the project works, see **`SYSTEM_ARCHITECTURE.md`**:
- **Input Sensors**: Ultrasonic, Camera, Speed sensors, Servo
- **Data Processing**: How sensor data flows through the system
- **Algorithms**: What algorithms are used and where (reactive control, mapping, object detection, A* pathfinding)
- **System Integration**: How all components work together

## Notes

- The `hardware_mock.py` module automatically detects your platform
- On PC: All hardware calls are simulated (printed to console)
- On Pi: Real hardware is used via picar-4wd library
- This allows you to develop and test logic on PC before deploying to Pi
- **You don't need `picar-4wd/setup.py` on your laptop** - it's only for Raspberry Pi (configures GPIO/I2C/SPI)
- **You can develop Part 2 (Steps 6-8) on laptop without completing Step 5** - they're independent algorithm tasks

---

**Last Updated**: Development setup complete. Ready to refine Step 4 obstacle avoidance.
