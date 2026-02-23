# Quick Start: Object Detection with py311 Virtual Environment

## ✅ Setup Complete!

Your object detection environment is ready to use with the `py311` virtual environment.

## How to Run Object Detection

### Option 1: Using the convenience script (Recommended)

```bash
cd /home/hpalin/CS437Lab1/software
./run_object_detection.sh --viewer
```

Or without viewer (quick test):
```bash
./run_object_detection.sh --no-viewer
```

### Option 2: Manual activation

```bash
# Activate virtual environment
source /home/hpalin/py311/bin/activate

# Navigate to software directory
cd /home/hpalin/CS437Lab1/software

# Run object detection
python3 object_detection.py --viewer    # With camera viewer window
python3 object_detection.py --no-viewer # Without viewer (faster)
```

## What's Installed

- ✅ Python 3.11 virtual environment (`py311`)
- ✅ MediaPipe (object detection backend)
- ✅ OpenCV (camera and image processing)
- ✅ NumPy (numerical operations)
- ✅ Model file: `efficientdet_lite0.tflite` (4.6 MB)

## Usage Examples

### Basic Detection Test
```bash
source /home/hpalin/py311/bin/activate
cd /home/hpalin/CS437Lab1/software
python3 object_detection.py --no-viewer
```

### With Viewer Window (shows camera feed + detections)
```bash
source /home/hpalin/py311/bin/activate
cd /home/hpalin/CS437Lab1/software
python3 object_detection.py --viewer
```
Press 'q' to quit when viewer is open.

### Diagnostic Test
```bash
source /home/hpalin/py311/bin/activate
cd /home/hpalin/CS437Lab1/software
python3 diagnose_detection.py
```

## Integration with Your Code

You can use the object detector in your own scripts:

```python
from object_detection import ObjectDetector, VisionOverride
import time

# Initialize detector
detector = ObjectDetector(method='auto')  # Auto-selects MediaPipe
override = VisionOverride()

# Detect objects
detections = detector.detect_objects()
print(f"Detected {len(detections)} objects")

# Check for critical objects (person, stop sign)
should_stop, obj_class = detector.should_stop(detections)
if should_stop:
    print(f"STOP! Detected: {obj_class}")

# Cleanup when done
detector.cleanup()
```

## Troubleshooting

### Camera not found
- Check if camera is connected: `ls /dev/video*`
- Try different camera index: `python3 object_detection.py --viewer` (will try index 0 by default)

### Low FPS
- The model is optimized for Raspberry Pi 5
- On PC, you should get good performance
- If slow, try reducing frame resolution in `object_detection.py`

### Model not found
- Model file should be at: `software/efficientdet_lite0.tflite`
- If missing, run: `python3 download_model.py`

## Next Steps

1. **Test detection**: Run `python3 object_detection.py --viewer` to see live detections
2. **Integrate with navigation**: Use `VisionOverride` class in your navigation code
3. **Customize**: Adjust detection threshold in `object_detection.py` (line ~161)

## Files
- `object_detection.py` - Main detector implementation
- `diagnose_detection.py` - Diagnostic tools
- `download_model.py` - Model download script
- `run_object_detection.sh` - Convenience script

---

**Ready to go!** Your object detection system is set up and ready to use. 🚀
