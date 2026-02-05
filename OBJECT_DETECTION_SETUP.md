# Object Detection (Step 7) - Setup Guide

## Overview

This implementation uses **MediaPipe Tasks Object Detector** as the primary backend, which is the recommended 2026-safe approach. It works on both PC (development) and Raspberry Pi 5 (deployment).

## Key Features

- ✅ **MediaPipe Tasks Object Detector** (primary) - Full COCO object detection
- ✅ **vilib** (secondary) - Face detection only (PiCar-X convenience)
- ✅ **Mock** (development) - For PC development without camera
- ✅ **Label normalization** - Handles "stop sign" vs "stop_sign"
- ✅ **VisionOverride class** - Clean integration with mapping/routing
- ✅ **Automatic backend selection** - Works on PC and Pi automatically

## Installation

### On PC (Development)

1. **Install dependencies:**
   ```bash
   pip install mediapipe opencv-python numpy
   ```

2. **Download model:**
   ```bash
   python download_model.py
   ```
   Or manually download from:
   https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/python

3. **Test:**
   ```bash
   python object_detection.py
   ```

### On Raspberry Pi 5

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
   python3 download_model.py
   ```

5. **Test:**
   ```bash
   python3 object_detection.py
   ```

## Usage

### Basic Usage

```python
from object_detection import ObjectDetector

# Auto-select best backend
detector = ObjectDetector()

# Detect objects
detections = detector.detect_objects()

# Check if should stop
should_stop, obj_class = detector.should_stop(detections)
if should_stop:
    print(f"Stop! Detected: {obj_class}")
```

### Integration with Mapping/Routing

```python
from object_detection import ObjectDetector, VisionOverride
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

## Model Options

MediaPipe supports several EfficientDet-Lite models:

- **efficientdet_lite0.tflite** - Fastest, lower accuracy
- **efficientdet_lite1.tflite** - Balanced
- **efficientdet_lite2.tflite** - Slower, higher accuracy
- **efficientdet_lite3.tflite** - Slowest, highest accuracy

For Raspberry Pi 5, `efficientdet_lite0` or `lite1` are recommended for ~1 FPS target.

## Performance Tips

1. **Lower resolution**: Resize frames to 320x240 or 160x120 for faster processing
2. **Skip frames**: Process every 2nd or 3rd frame
3. **Use quantized models**: EfficientDet-Lite models are already quantized
4. **Avoid heavy visualization**: Disable display when measuring FPS

## Label Normalization

The code automatically normalizes labels:
- "stop sign" = "stop_sign" (handles both)
- Case insensitive
- Handles spaces/underscores

## Important Notes

### vilib Limitations

- vilib's "human" detection is **face detection**, not full person detection
- Will miss people not facing the camera
- Does not detect stop signs or general objects
- Use MediaPipe for full object detection

### MediaPipe Advantages

- ✅ Full COCO object detection (80+ classes)
- ✅ Detects person (full body, not just face)
- ✅ Detects stop signs
- ✅ Works on both PC and Pi
- ✅ Future-proof, actively maintained

## Troubleshooting

### Model not found
- Run `python download_model.py` to download the model
- Or manually download from MediaPipe documentation

### Camera not working on Pi
- Test with `libcamera-hello`
- Check camera ribbon cable connection
- Enable camera in `raspi-config`

### Low FPS
- Reduce frame resolution
- Skip frames (process every Nth frame)
- Use smaller model (lite0 instead of lite2)

### Import errors
- Make sure you're in the virtual environment
- Install missing packages: `pip install mediapipe opencv-python`

## Next Steps

1. Test on PC with webcam
2. Download model file
3. Integrate with `advanced_mapping.py`
4. Deploy to Pi and test with real camera
5. Integrate with A* routing (Step 8)
