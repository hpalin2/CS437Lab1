#!/usr/bin/env python3
"""
Diagnostic script to identify why stop signs aren't being detected.
"""

import cv2
import numpy as np
import time
import os

# Try to import the project's object detector; if unavailable, degrade gracefully
try:
    from object_detection import ObjectDetector, normalize_label
except Exception:
    ObjectDetector = None
    def normalize_label(x):
        return x

# Try to import Picamera2; if libcamera isn't installed we'll fall back to OpenCV
PICAMERA2_AVAILABLE = False
try:
    from picamera2 import Picamera2
    from pixmap import PixelFormat
    PICAMERA2_AVAILABLE = True
except Exception:
    Picamera2 = None
    PixelFormat = None
    PICAMERA2_AVAILABLE = False

def test_camera():
    """Test if camera is working and returning valid frames."""
    print("=" * 60)
    print("CAMERA DIAGNOSTIC")
    print("=" * 60)
    
    # Prefer Picamera2 when available
    if PICAMERA2_AVAILABLE:
        try:
            picam2 = Picamera2()
            picam2.configure(picam2.create_video_configuration(main={"format": "RGB888", "size": (640, 480)}))
            picam2.start()

            frame = picam2.capture_array()
            picam2.stop()

            if frame is None:
                print("[ERROR] Picamera2 returned no frame")
                # fall through to OpenCV fallback
            else:
                print("[OK] Picamera2 frame captured")
                return True

        except Exception as e:
            print(f"[WARN] Picamera2 capture failed: {e}")

    # OpenCV / V4L2 fallback
    device = os.environ.get('CAMERA_DEVICE', '/dev/video0')
    print(f"[INFO] Trying OpenCV V4L2 device: {device}")
    try:
        # If device is a path, use it directly with cv2.CAP_V4L2; otherwise try int()
        try:
            cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        except Exception:
            cap = cv2.VideoCapture(int(device))

        if not cap.isOpened():
            print(f"[ERROR] Cannot open video device {device}")
            return False

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            print("[ERROR] OpenCV failed to grab frame")
            return False

        print("[OK] OpenCV frame captured")
        return True

    except Exception as e:
        print(f"[ERROR] OpenCV camera test failed: {e}")
        return False


def test_model_file():
    """Check if model file exists and is valid."""
    print("\n" + "=" * 60)
    print("MODEL FILE DIAGNOSTIC")
    print("=" * 60)
    
    import os
    
    possible_paths = [
        'models/efficientdet_lite0.tflite',
        'efficientdet_lite0.tflite',
        'models/efficientdet_lite1.tflite',
        'efficientdet_lite1.tflite',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"[OK] Found: {path} ({size} bytes)")
            return path
    
    print("[ERROR] No model file found!")
    print("  Searched paths:")
    for path in possible_paths:
        print(f"    - {path}")
    return None


def test_mediapipe_with_test_image():
    """Test MediaPipe with a real image file."""
    print("\n" + "=" * 60)
    print("MEDIAPIPE TEST IMAGE DIAGNOSTIC")
    print("=" * 60)
    
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        # Try to find model
        import os
        model_path = None
        for path in ['models/efficientdet_lite0.tflite', 'efficientdet_lite0.tflite']:
            if os.path.exists(path):
                model_path = path
                break
        
        if not model_path:
            print("[ERROR] Model file not found")
            return False
        
        print(f"[OK] Loading model: {model_path}")
        
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.ObjectDetectorOptions(
            base_options=base_options,
            score_threshold=0.3,  # Lower threshold for testing
            max_results=5,
            running_mode=vision.RunningMode.IMAGE,
        )
        detector = vision.ObjectDetector.create_from_options(options)
        
        print("[OK] MediaPipe detector created")
        
        # Create a test image with some content
        print("\nCreating test image...")
        test_image = np.ones((480, 640, 3), dtype=np.uint8) * 128  # Gray image
        
        # Add some shapes to make it more interesting
        cv2.rectangle(test_image, (100, 100), (300, 300), (0, 0, 255), -1)  # Blue rect
        cv2.circle(test_image, (450, 200), 50, (0, 255, 0), -1)  # Green circle
        
        # Run detection
        print("Running detection on test image...")
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=test_image)
        result = detector.detect(mp_image)
        
        print(f"[OK] Detection completed. Detections: {len(result.detections)}")
        for i, det in enumerate(result.detections):
            label = det.categories[0].category_name
            score = det.categories[0].score
            print(f"  {i+1}. {label}: {score:.2f}")
        
        return True
    
    except Exception as e:
        print(f"[ERROR] MediaPipe test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_live_detection_with_diagnostics():
    """Test live detection with detailed diagnostics."""
    print("\n" + "=" * 60)
    print("LIVE DETECTION DIAGNOSTIC")
    print("=" * 60)
    print("\nCapturing 10 frames and running detection...\n")
    
    try:
        detector = None
        if ObjectDetector is not None:
            try:
                detector = ObjectDetector(method='mediapipe')
            except Exception as e:
                print(f"[WARN] Could not initialize ObjectDetector: {e}")

        frame_count = 0
        detected_any = False

        if detector is not None:
            # Use detector's frame source
            for i in range(10):
                frame = detector.get_frame()
                if frame is None:
                    print(f"Frame {i+1}: FAILED to get frame")
                    continue

                height, width = frame.shape[:2]
                brightness = np.mean(frame)
                max_pixel = np.max(frame)

                print(f"Frame {i+1}:")
                print(f"  Size: {width}x{height}, Brightness: {brightness:.1f}, Max pixel: {max_pixel}")

                detections = detector.detect_objects(frame)
                if detections:
                    print(f"  >>> DETECTED {len(detections)} object(s):")
                    detected_any = True
                    for det in detections:
                        print(f"      - {det['class']}: {det['confidence']:.2f}")
                else:
                    print("  No detections")

                time.sleep(0.3)

            try:
                detector.cleanup()
            except Exception:
                pass

        else:
            # No ObjectDetector available — just capture frames with OpenCV and report diagnostics
            device = os.environ.get('CAMERA_DEVICE', '/dev/video0')
            print(f"[INFO] No ObjectDetector; sampling frames from {device} using OpenCV")
            cap = None
            try:
                cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
                if not cap.isOpened():
                    print(f"[ERROR] Cannot open video device {device}")
                    return False

                for i in range(10):
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        print(f"Frame {i+1}: FAILED to capture frame")
                        continue

                    height, width = frame.shape[:2]
                    brightness = np.mean(frame)
                    max_pixel = np.max(frame)
                    print(f"Frame {i+1}:")
                    print(f"  Size: {width}x{height}, Brightness: {brightness:.1f}, Max pixel: {max_pixel}")
                    print("  Skipping detection (ObjectDetector not available)")
                    time.sleep(0.3)

                return False

            except Exception as e:
                print(f"[ERROR] OpenCV live capture failed: {e}")
                return False
            finally:
                if cap is not None:
                    cap.release()

        if not detected_any:
            print("\n[WARNING] No objects detected in any frame!")
            print("Possible causes:")
            print("  1. Camera returns blank/dark frames")
            print("  2. Most objects have confidence < 0.5 (model threshold)")
            print("  3. Model not working properly")

        return detected_any

    except Exception as e:
        print(f"[ERROR] Live detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def suggest_fixes():
    """Suggest fixes based on diagnostics."""
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    print("""
If no objects are detected:

1. **Lower the confidence threshold:**
   Edit object_detection.py, line ~153:
   Change: score_threshold=0.5
   To:     score_threshold=0.3  (or even 0.25)

2. **Check camera exposure:**
   If frames are too dark:
   - Check lighting conditions
   - Try adjusting camera properties in MediaPipeDetector.__init__()

3. **Use test image with visual markers:**
   Print a colored object and point camera at it to verify detection works

4. **For stop signs specifically:**
   - Ensure EfficientDet-Lite model includes "stop sign" class
   - Download the correct COCO-trained model if needed
   - Visit: https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/python
""")


if __name__ == "__main__":
    print("OBJECT DETECTION DIAGNOSTIC SUITE")
    print("=" * 60)
    
    # Run diagnostics
    camera_ok = test_camera()
    model_path = test_model_file()
    mediapipe_ok = test_mediapipe_with_test_image()
    detected = test_live_detection_with_diagnostics()
    
    suggest_fixes()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Camera test:        {'PASS' if camera_ok else 'FAIL'}")
    print(f"Model file:         {'PASS' if model_path else 'FAIL'}")
    print(f"MediaPipe test:     {'PASS' if mediapipe_ok else 'FAIL'}")
    print(f"Live detection:     {'PASS' if detected else 'FAIL'}")
    print("=" * 60)
