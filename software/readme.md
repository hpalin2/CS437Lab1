# PiCar IoT Lab - Software Development

This repository contains the software components for the IoT Lab 1 PiCar project.

**Your Hardware Configuration:**
- Raspberry Pi 5 (16 GB RAM)
- PiCar-X Car Chassis Kit
- Raspberry Pi Camera Module
- 64 GB microSD card

**Note**: This lab documentation primarily references PiCar-4WD, but you're using PiCar-X. The core concepts are the same, but library installation and some API calls may differ. See hardware configuration section below.

## Quick Start

### On Your PC (Development)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test the setup:**
   ```bash
   cd software
   python test_locomotion.py
   ```
   This will run in mock mode, simulating hardware calls.

3. **Develop your code:**
   - Use `software/hardware_mock.py` to get hardware interfaces
   - Your code will automatically work on both PC (mocks) and Pi (real hardware)

### On Raspberry Pi 5 (Deployment)

1. **Install PiCar-X Library:**
   ```bash
   # Follow PiCar-X specific instructions
   # Installation guide: https://docs.sunfounder.com/projects/picar-x/
   ```

2. **Install Camera Support:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-picamera2
   ```

3. **Pull your code:**
   ```bash
   git pull origin main
   ```

4. **Run tests (CAREFUL - CAR WILL MOVE!):**
   ```bash
   cd software
   python3 test_locomotion.py
   ```

## Hardware Configuration

### Raspberry Pi 5 vs Pi 4

**Advantages of Pi 5:**
- More powerful CPU - better for object detection
- More RAM (16 GB) - can handle larger models
- Should achieve better than 1 FPS for object detection
- Better overall performance

**Compatibility:**
- Most software works the same
- Camera interface is compatible
- GPIO pins are compatible
- May need updated drivers/libraries

### PiCar-X vs PiCar-4WD

**Key Differences:**

| Feature | PiCar-4WD | PiCar-X (Your Hardware) |
|---------|-----------|-------------------------|
| Library | `picar-4wd` | `picar-x` (different library) |
| Installation | `sudo python3 setup.py install` | Follow PiCar-X docs |
| Ultrasonic | Mounted on servo | May be fixed position |
| Object Detection | TensorFlow Lite | MediaPipe (recommended) |
| API | `picar_4wd` module | `picar_x` module (may differ) |

**PiCar-X Specific Setup:**

1. **Installation:**
   - Follow: https://docs.sunfounder.com/projects/picar-x/
   - Different installation process than PiCar-4WD
   - May use different package manager

2. **Ultrasonic Sensor:**
   - On PiCar-X, ultrasonic may be fixed (not on servo)
   - **Solution**: Mount ultrasonic on camera pan servo
   - Use toothpicks/rubber bands to attach
   - Add weight to bottom if needed for balance

3. **Turning:**
   - PiCar-X can turn in place
   - Use opposing wheel directions
   - May need different motor control than PiCar-4WD

**✅ Your `software/hardware_mock.py` has been updated** - it now supports both PiCar-X and PiCar-4WD! The hardware abstraction layer automatically detects which library is installed and provides a unified interface.

## Installation & Setup

### PC Development Setup

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test Locomotion Script:**
   ```bash
   cd software
   python test_locomotion.py
   ```
   This will run in mock mode on your PC, simulating hardware calls.

3. **Development Workflow:**
   - Develop on PC: Write and test your code using the mock hardware
   - Commit to Git: Push your changes to your repository
   - Deploy to Pi: Pull changes on Raspberry Pi and test with real hardware

### Raspberry Pi 5 Setup

1. **Install PiCar-X Library:**
   ```bash
   # Follow PiCar-X specific instructions
   # Check: https://docs.sunfounder.com/projects/picar-x/
   ```

2. **Install Camera Support:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-picamera2
   ```

3. **Test Camera:**
   ```bash
   libcamera-hello
   ```

4. **Verify Installation:**
   ```bash
   python3 -c "from picarx import Picarx; print('PiCar-X installed successfully')"
   ```

5. **Pull Your Code:**
   ```bash
   git pull origin main
   ```

6. **Run Tests (CAREFUL - CAR WILL MOVE!):**
   ```bash
   cd software
   python3 test_locomotion.py
   ```
   
   **WARNING**: On the Pi, this will actually move the car! Make sure:
   - The car is on a safe surface
   - There's enough space around it
   - You're ready to stop it if needed (Ctrl+C)

## Object Detection Setup (Step 7)

### Overview

This implementation uses **MediaPipe Tasks Object Detector** as the primary backend, which is the recommended 2026-safe approach. It works on both PC (development) and Raspberry Pi 5 (deployment).

### Key Features

- ✅ **MediaPipe Tasks Object Detector** (primary) - Full COCO object detection
- ✅ **vilib** (secondary) - Face detection only (PiCar-X convenience)
- ✅ **Mock** (development) - For PC development without camera
- ✅ **Label normalization** - Handles "stop sign" vs "stop_sign"
- ✅ **VisionOverride class** - Clean integration with mapping/routing
- ✅ **Automatic backend selection** - Works on PC and Pi automatically

### Installation

#### On PC (Development)

1. **Install dependencies:**
   ```bash
   pip install mediapipe opencv-python numpy
   ```

2. **Download model:**
   ```bash
   cd software
   python download_model.py
   ```
   Or manually download from:
   https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/python

3. **Test:**
   ```bash
   python object_detection.py --viewer
   ```

#### On Raspberry Pi 5

1. **Use virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   ```

2. **Install dependencies:**
   ```bash
   pip install mediapipe opencv-python numpy
   pip install picamera2  # For Pi camera
   ```

3. **Test camera:**
   ```bash
   libcamera-hello
   ```

4. **Download model:**
   ```bash
   cd software
   python3 download_model.py
   ```

5. **Test:**
   ```bash
   python3 object_detection.py --viewer
   ```

### Usage

#### Basic Usage

```python
from software.object_detection import ObjectDetector

# Auto-select best backend
detector = ObjectDetector()

# Detect objects
detections = detector.detect_objects()

# Check if should stop
should_stop, obj_class = detector.should_stop(detections)
if should_stop:
    print(f"Stop! Detected: {obj_class}")
```

#### Integration with Mapping/Routing

```python
from software.object_detection import ObjectDetector, VisionOverride
import time

detector = ObjectDetector()
override = VisionOverride()

while True:
    # Get detections
    detections = detector.detect_objects()
    
    # Check for critical objects
    person_present = any(d['class'] == 'person' for d in detections)
    stop_sign_present = any('stop sign' in d['class'] for d in detections)
    
    # Update override state
    override.update(person_present, stop_sign_present, time.time())
    
    # Check if should stop
    if override.should_stop():
        car.stop()
        continue
    
    # Continue with mapping/routing
    # ...
```

### Model Options

MediaPipe supports several EfficientDet-Lite models:

- **efficientdet_lite0.tflite** - Fastest, lower accuracy
- **efficientdet_lite1.tflite** - Balanced
- **efficientdet_lite2.tflite** - Slower, higher accuracy
- **efficientdet_lite3.tflite** - Slowest, highest accuracy

For Raspberry Pi 5, `efficientdet_lite0` or `lite1` are recommended for ~1 FPS target.

### Performance Tips

1. **Lower resolution**: Resize frames to 320x240 or 160x120 for faster processing
2. **Skip frames**: Process every 2nd or 3rd frame
3. **Use quantized models**: EfficientDet-Lite models are already quantized
4. **Avoid heavy visualization**: Disable display when measuring FPS

### Important Notes

#### vilib Limitations

- vilib's "human" detection is **face detection**, not full person detection
- Will miss people not facing the camera
- Does not detect stop signs or general objects
- Use MediaPipe for full object detection

#### MediaPipe Advantages

- ✅ Full COCO object detection (80+ classes)
- ✅ Detects person (full body, not just face)
- ✅ Detects stop signs
- ✅ Works on both PC and Pi
- ✅ Future-proof, actively maintained

## Project Status & Progress

### ✅ Completed Setup
- ✅ Hardware mock system for PC development
- ✅ Test scripts for locomotion and sensors
- ✅ picar-4wd repository cloned (for reference - you're using PiCar-X)
- ✅ **PiCar-X installed and API compatibility verified**
- ✅ Hardware abstraction layer (works with both PiCar-4WD and PiCar-X APIs)
- ✅ Obstacle avoidance starter code (`software/obstacle_avoidance.py`)

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
- ✅ `software/advanced_mapping.py` created with full implementation
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

### ✅ Part 2, Step 7 - Object Detection: COMPLETE
**Status**: ✅ Implemented with MediaPipe Tasks Object Detector

**What's done**:
- ✅ `software/object_detection.py` with MediaPipe backend
- ✅ Mock detector for PC development
- ✅ vilib support (face detection only)
- ✅ Label normalization
- ✅ VisionOverride class for integration
- ✅ Viewer window with bounding boxes
- ✅ Ready for deployment to Pi

### 📋 Upcoming Tasks

**Part 1 (After Step 4)**:
- Step 5: Set up obstacle course and test driving (needs Pi + real hardware)
- Create demo video and report

**Part 2 (Can develop on laptop NOW - no need to wait for Step 5)**:
- Step 6: Advanced mapping with numpy arrays ✅ **COMPLETE**
- Step 7: Object detection with MediaPipe ✅ **COMPLETE**
- Step 8: A* routing algorithm ⏭️ **Next** - Can develop on laptop now
- Step 9: Full self-driving integration (needs Pi for final testing)

**Important**: You can develop Steps 6-8 on your laptop **right now** without completing Step 5. These are algorithm/logic tasks that work with mocks. Step 5 is just testing Part 1 on real hardware, which is separate from developing Part 2 algorithms.

## Project Structure

```
.
├── software/                    # All code files
│   ├── advanced_mapping.py      # Part 2, Step 6 - Advanced mapping
│   ├── object_detection.py      # Part 2, Step 7 - Object detection
│   ├── hardware_mock.py          # Hardware abstraction layer
│   ├── obstacle_avoidance.py    # Part 1, Step 4 - Obstacle avoidance
│   ├── test_locomotion.py       # Locomotion testing
│   ├── download_model.py        # Model download script
│   └── download_model.sh        # Model download (bash)
├── readme.md                    # This file
├── requirements.txt             # Python dependencies
├── project.md                   # Project requirements
├── SYSTEM_ARCHITECTURE.md       # System architecture documentation
└── .gitignore                   # Git ignore rules
```

## Development Workflow

1. **Develop on PC** using mocks
2. **Test logic** without hardware
3. **Commit and push** to git
4. **Pull on Raspberry Pi** and test with real hardware

### What You Can Develop on Laptop vs Pi

**✅ Can Develop on Laptop (Algorithm/Logic) - No Pi Needed**:
- Step 4: Obstacle avoidance logic ✅
- Step 6: Advanced mapping algorithm (numpy arrays) ✅
- Step 7: Object detection code structure ✅
- Step 8: A* routing algorithm ⏭️
- All Python logic and algorithms

**⚠️ Needs Pi (Hardware-Specific)**:
- Step 5: Actual driving test (needs real car) - **Optional before Part 2**
- Step 7: Object detection testing (needs camera)
- Step 9: Final integration testing

**Key Point**: You don't need to complete Step 5 before starting Part 2 development. Steps 6-8 are independent algorithms you can develop on your laptop using mocks. Step 5 is just testing Part 1 on real hardware.

## Quick Commands

```bash
# Test obstacle avoidance on laptop
cd software
python obstacle_avoidance.py

# Test basic locomotion
python test_locomotion.py

# Test object detection with viewer
python object_detection.py --viewer

# Test advanced mapping
python advanced_mapping.py

# When ready, commit and push
git add .
git commit -m "Update: [describe changes]"
git push
```

## Troubleshooting

### On PC:
- If you get import errors, make sure you're using the mock hardware
- The script should automatically detect you're on PC and use mocks
- Install dependencies: `pip install -r requirements.txt`

### On Raspberry Pi 5:
- **Camera not working**: Ensure you're using `libcamera` commands, not old `raspistill`
- **GPIO issues**: Pi 5 GPIO is compatible but may need updated libraries
- **Performance**: Pi 5 should perform better - if slower, check thermal throttling
- **Library not found**: Make sure you installed PiCar-X library, not PiCar-4WD
- **Ultrasonic can't scan**: Mount it on camera pan servo
- **Object detection fails**: Use MediaPipe (recommended) instead of TensorFlow Lite
- **Motors not working**: Check PiCar-X specific motor control API
- **Model not found**: Run `python3 download_model.py` in software folder
- **Low FPS**: Reduce frame resolution, skip frames, use smaller model

### Import errors:
- Make sure you're in the virtual environment (on Pi)
- Install missing packages: `pip install mediapipe opencv-python numpy`

## System Architecture

For a detailed explanation of how the project works, see **`SYSTEM_ARCHITECTURE.md`**:
- **Input Sensors**: Ultrasonic, Camera, Speed sensors, Servo
- **Data Processing**: How sensor data flows through the system
- **Algorithms**: What algorithms are used and where (reactive control, mapping, object detection, A* pathfinding)
- **System Integration**: How all components work together

## Resources

- **PiCar-X Documentation**: https://docs.sunfounder.com/projects/picar-x/
- **Raspberry Pi 5 Docs**: https://www.raspberrypi.com/documentation/
- **MediaPipe Object Detection**: https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/python
- **PiCar-4WD Reference**: https://github.com/sunfounder/picar-4wd (for understanding, not your hardware)

## Notes

- The `software/hardware_mock.py` module automatically detects your platform
- On PC: All hardware calls are simulated (printed to console)
- On Pi: Real hardware is used via picar-x library
- This allows you to develop and test logic on PC before deploying to Pi
- **You don't need `picar-4wd/setup.py` on your laptop** - it's only for Raspberry Pi (configures GPIO/I2C/SPI)
- **You can develop Part 2 (Steps 6-8) on laptop without completing Step 5** - they're independent algorithm tasks

---

**Last Updated**: All setup documentation consolidated. Ready for development and deployment.
