#!/usr/bin/env python3
"""
Diagnostic script to identify why stop signs aren't being detected.
"""

import cv2
import numpy as np
import time
from object_detection import ObjectDetector, normalize_label

def test_camera():
    """Test if camera is working and returning valid frames."""
    print("=" * 60)
    print("CAMERA DIAGNOSTIC")
    print("=" * 60)
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Cannot open camera 0")
            return False
        
        print("[OK] Camera opened successfully")
        
        # Try to capture frames
        print("\nCapturing 5 frames...")
        for i in range(5):
            ret, frame = cap.read()
            if ret and frame is not None:
                height, width = frame.shape[:2]
                # Check if frame is mostly black/empty
                mean_brightness = np.mean(frame)
                print(f"  Frame {i+1}: {width}x{height}, brightness: {mean_brightness:.1f}")
                
                if mean_brightness < 10:
                    print(f"    [WARNING] Frame is very dark (brightness < 10)")
            else:
                print(f"  Frame {i+1}: FAILED to capture")
                cap.release()
                return False
            
            time.sleep(0.2)
        
        cap.release()
        return True
    
    except Exception as e:
        print(f"[ERROR] Camera test failed: {e}")
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
        detector = ObjectDetector(method='mediapipe')
        
        frame_count = 0
        detected_any = False
        
        for i in range(10):
            frame = detector.get_frame()
            if frame is None:
                print(f"Frame {i+1}: FAILED to get frame")
                continue
            
            # Check frame properties
            height, width = frame.shape[:2]
            brightness = np.mean(frame)
            max_pixel = np.max(frame)
            
            print(f"Frame {i+1}:")
            print(f"  Size: {width}x{height}, Brightness: {brightness:.1f}, Max pixel: {max_pixel}")
            
            # Run detection
            detections = detector.detect_objects(frame)
            
            if detections:
                print(f"  >>> DETECTED {len(detections)} object(s):")
                detected_any = True
                for det in detections:
                    print(f"      - {det['class']}: {det['confidence']:.2f}")
            else:
                print(f"  No detections")
            
            time.sleep(0.3)
        
        detector.cleanup()
        
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
