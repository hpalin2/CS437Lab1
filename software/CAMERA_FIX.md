# Camera Access Fix for Raspberry Pi 5

## Problem
The camera can be opened but frames cannot be read. This is because Raspberry Pi 5 uses libcamera, and the Python bindings need to be installed.

## Solution

### Option 1: Install libcamera Python bindings (Recommended)

Run the fix script:
```bash
cd /home/hpalin/CS437Lab1/software
./fix_camera.sh
```

Or manually:
```bash
sudo apt-get update
sudo apt-get install -y python3-libcamera
```

After installation, Picamera2 should work properly.

### Option 2: Use Mock Detector (for testing without camera)

If you just want to test the code without a camera:
```bash
source /home/hpalin/py311/bin/activate
cd /home/hpalin/CS437Lab1/software
python3 -c "from object_detection import ObjectDetector; d = ObjectDetector(method='mock'); print('Mock detector works')"
```

### Option 3: Test camera with libcamera command-line tools

Verify camera works at system level:
```bash
libcamera-hello -t 2000  # Should show camera preview for 2 seconds
```

If this works, the camera hardware is fine - we just need Python bindings.

## After Fix

Once python3-libcamera is installed, the object detection should automatically use Picamera2 on Raspberry Pi:

```bash
source /home/hpalin/py311/bin/activate
cd /home/hpalin/CS437Lab1/software
python3 object_detection.py --viewer
```

You should see:
```
[INFO] Using Picamera2 for camera capture
```

Instead of:
```
[INFO] Using OpenCV for camera capture (index 0)
[WARNING] Could not get frame, retrying...
```

## Current Status

- ✅ Virtual environment (py311) created
- ✅ Dependencies installed (MediaPipe, OpenCV, NumPy)
- ✅ Picamera2 Python package installed
- ⚠️  libcamera Python bindings needed (system package)
- ✅ Model file exists

## Notes

- The libcamera Python bindings are a system package, not a pip package
- They should still be accessible from your virtual environment
- Picamera2 requires these bindings to work properly on Raspberry Pi 5
