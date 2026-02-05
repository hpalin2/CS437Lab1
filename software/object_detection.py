"""
Part 2, Step 7: Object Detection
Detects objects using camera feed and reacts accordingly.

Primary backend: MediaPipe Tasks Object Detector (recommended for 2026)
- Works on both PC (webcam) and Raspberry Pi 5 (Picamera2)
- Supports COCO classes: person, stop sign, etc.
- Future-proof, actively maintained by Google

Secondary backend: vilib (PiCar-X convenience features only)
- Face detection (not full person detection)
- Color detection, QR codes
- Limited to PiCar-X ecosystem
"""

import time
import os
import sys
import numpy as np
from hardware_mock import is_raspberry_pi

# Try to import detection libraries
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

try:
    from vilib import Vilib
    VILIB_AVAILABLE = True
except ImportError:
    VILIB_AVAILABLE = False

# Try Picamera2 for Raspberry Pi
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False


def normalize_label(label):
    """
    Normalize object detection labels.
    Handles variations like "stop sign" vs "stop_sign", case differences, etc.
    
    Args:
        label: Raw label string
    
    Returns:
        Normalized lowercase label with spaces
    """
    if not label:
        return ""
    # Convert to lowercase, replace underscores with spaces, strip
    normalized = label.lower().replace("_", " ").strip()
    return normalized


class MockDetector:
    """Mock object detector for PC development"""
    
    def __init__(self):
        self.detection_count = 0
    
    def detect_objects(self, frame=None):
        """Mock detection - returns simulated detections"""
        self.detection_count += 1
        
        # Simulate occasional detections
        import random
        detections = []
        
        # 10% chance of detecting a person
        if random.random() < 0.1:
            detections.append({
                'class': 'person',
                'confidence': 0.85,
                'bbox': (100, 100, 200, 300)  # (x, y, width, height)
            })
        
        # 5% chance of detecting stop sign (use correct COCO label)
        if random.random() < 0.05:
            detections.append({
                'class': 'stop sign',  # COCO uses "stop sign" with space
                'confidence': 0.90,
                'bbox': (300, 150, 100, 100)
            })
        
        return detections
    
    def get_frame(self):
        """Get mock frame (numpy array)"""
        # Return a dummy image array
        return np.zeros((480, 640, 3), dtype=np.uint8)
    
    def cleanup(self):
        """Clean up resources"""
        pass


class MediaPipeDetector:
    """
    Object detector using MediaPipe Tasks Object Detector.
    Primary backend - works on both PC and Raspberry Pi 5.
    """
    
    def __init__(self, model_path=None, camera_index=0, use_picamera2=None):
        """
        Initialize MediaPipe detector.
        
        Args:
            model_path: Path to .tflite model file (e.g., efficientdet_lite0.tflite)
            camera_index: Camera index for OpenCV (PC) or None for auto-select
            use_picamera2: Force Picamera2 on Pi (None = auto-detect)
        """
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError("MediaPipe not available. Install: pip install mediapipe")
        
        if not OPENCV_AVAILABLE:
            raise ImportError("OpenCV not available. Install: pip install opencv-python")
        
        # Determine model path
        if model_path is None:
            # Try common locations
            possible_paths = [
                'models/efficientdet_lite0.tflite',
                'efficientdet_lite0.tflite',
                'models/efficientdet_lite1.tflite',
                'efficientdet_lite1.tflite',
            ]
            
            model_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    model_path = path
                    break
            
            if model_path is None:
                raise FileNotFoundError(
                    "Model file not found. Please download EfficientDet-Lite model.\n"
                    "See: https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/python"
                )
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Initialize MediaPipe object detector
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.ObjectDetectorOptions(
            base_options=base_options,
            score_threshold=0.5,
            max_results=5,
            running_mode=vision.RunningMode.IMAGE,
        )
        self.detector = vision.ObjectDetector.create_from_options(options)
        
        # Initialize camera
        self.camera = None
        self.camera_index = camera_index
        self.use_picamera2 = use_picamera2
        
        # Auto-detect camera backend
        if use_picamera2 is None:
            self.use_picamera2 = is_raspberry_pi() and PICAMERA2_AVAILABLE
        
        if self.use_picamera2:
            try:
                self.camera = Picamera2()
                # Configure for object detection (lower resolution for speed)
                config = self.camera.create_preview_configuration(
                    main={"size": (640, 480)}
                )
                self.camera.configure(config)
                self.camera.start()
                print("[INFO] Using Picamera2 for camera capture")
            except Exception as e:
                print(f"[WARNING] Picamera2 initialization failed: {e}")
                print("[INFO] Falling back to OpenCV")
                self.use_picamera2 = False
        
        if not self.use_picamera2:
            # Use OpenCV for camera capture
            self.camera = cv2.VideoCapture(camera_index)
            if not self.camera.isOpened():
                raise RuntimeError(f"Could not open camera {camera_index}")
            print(f"[INFO] Using OpenCV for camera capture (index {camera_index})")
        
        print(f"[INFO] MediaPipe detector initialized with model: {model_path}")
    
    def get_frame(self):
        """
        Get current camera frame.
        
        Returns:
            numpy array (BGR format) or None if capture fails
        """
        if self.use_picamera2:
            # Picamera2 capture
            try:
                frame = self.camera.capture_array()
                # Picamera2 returns RGB, convert to BGR for OpenCV compatibility
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                return frame_bgr
            except Exception as e:
                print(f"[ERROR] Picamera2 capture failed: {e}")
                return None
        else:
            # OpenCV capture
            ret, frame = self.camera.read()
            if ret:
                return frame
            return None
    
    def detect_objects(self, frame=None):
        """
        Detect objects in frame.
        
        Args:
            frame: numpy array image (BGR format). If None, captures from camera.
        
        Returns:
            List of detection dictionaries with normalized labels
        """
        # Get frame if not provided
        if frame is None:
            frame = self.get_frame()
            if frame is None:
                return []
        
        # Resize for speed (optional, but recommended for Pi)
        # Keep original size for better accuracy, or resize for speed
        # frame = cv2.resize(frame, (320, 240))  # Uncomment for faster processing
        
        # Convert BGR to RGB
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame_rgb = frame
        
        # Create MediaPipe image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        # Detect objects
        detection_result = self.detector.detect(mp_image)
        
        # Convert to our format with normalized labels
        detections = []
        for detection in detection_result.detections:
            bbox = detection.bounding_box
            category = detection.categories[0]
            
            # Normalize label (handles "stop sign" vs "stop_sign", etc.)
            label = normalize_label(category.category_name)
            
            detections.append({
                'class': label,
                'confidence': category.score,
                'bbox': (bbox.origin_x, bbox.origin_y, bbox.width, bbox.height)
            })
        
        return detections
    
    def cleanup(self):
        """Clean up resources"""
        if self.use_picamera2 and self.camera:
            try:
                self.camera.stop()
            except:
                pass
        elif self.camera:
            try:
                self.camera.release()
            except:
                pass


class VilibDetector:
    """
    Object detector using vilib (PiCar-X convenience features).
    
    NOTE: vilib's "human" detection is FACE detection, not full person detection.
    It will miss people not facing the camera. For general object detection
    (including stop signs), use MediaPipe instead.
    """
    
    def __init__(self):
        if not VILIB_AVAILABLE:
            raise ImportError("vilib not available. Install vilib for PiCar-X.")
        
        # Start camera
        Vilib.camera_start(vflip=False, hflip=False)
        Vilib.display(local=False, web=False)  # No display for headless
        
        # Enable face detection (NOT general object detection)
        # Note: vilib.object_detect_switch() may not provide general COCO classes
        Vilib.face_detect_switch(True)
        
        print("[INFO] vilib detector initialized (face detection only)")
        print("[WARNING] vilib 'human' detection is face detection, not full person detection")
    
    def detect_objects(self, frame=None):
        """
        Detect objects using vilib.
        
        NOTE: This only detects faces (not full person detection).
        For stop signs and general objects, use MediaPipe.
        
        Returns:
            List of detection dictionaries
        """
        detections = []
        
        # Check for face (vilib's "human" is actually face detection)
        if Vilib.detect_obj_parameter.get('human_n', 0) != 0:
            detections.append({
                'class': 'person',  # Map face to person for compatibility
                'confidence': 0.8,  # vilib doesn't provide confidence
                'bbox': (
                    Vilib.detect_obj_parameter.get('human_x', 0),
                    Vilib.detect_obj_parameter.get('human_y', 0),
                    Vilib.detect_obj_parameter.get('human_w', 0),
                    Vilib.detect_obj_parameter.get('human_h', 0)
                ),
                'note': 'face_detection'  # Indicate this is face, not full person
            })
        
        # vilib does not provide general object detection (stop signs, etc.)
        # Use MediaPipe for that
        
        return detections
    
    def get_frame(self):
        """Get current camera frame"""
        # vilib manages frames internally
        try:
            return Vilib.img if hasattr(Vilib, 'img') else None
        except:
            return None
    
    def cleanup(self):
        """Clean up resources"""
        Vilib.camera_close()


class ObjectDetector:
    """
    Unified object detector interface.
    Primary backend: MediaPipe (recommended for 2026)
    Secondary: vilib (face detection only, PiCar-X convenience)
    """
    
    def __init__(self, method='auto', model_path=None, camera_index=0):
        """
        Initialize detector.
        
        Args:
            method: 'auto', 'mediapipe', 'vilib', or 'mock'
            model_path: Path to .tflite model (for MediaPipe)
            camera_index: Camera index for OpenCV (PC)
        """
        self.method = method
        self.detector = None
        self.detection_backend = None
        
        if method == 'auto':
            # Auto-select: prefer MediaPipe (most capable)
            if MEDIAPIPE_AVAILABLE:
                method = 'mediapipe'
            elif is_raspberry_pi() and VILIB_AVAILABLE:
                method = 'vilib'
            else:
                method = 'mock'
        
        # Initialize appropriate detector
        if method == 'mediapipe':
            try:
                self.detector = MediaPipeDetector(model_path=model_path, camera_index=camera_index)
                self.detection_backend = 'mediapipe'
                print("[INFO] Using MediaPipe Tasks Object Detector (primary backend)")
            except Exception as e:
                print(f"[WARNING] MediaPipe initialization failed: {e}")
                print("[INFO] Falling back to mock detector")
                self.detector = MockDetector()
                self.detection_backend = 'mock'
        
        elif method == 'vilib':
            try:
                self.detector = VilibDetector()
                self.detection_backend = 'vilib'
                print("[INFO] Using vilib (face detection only, limited capabilities)")
            except Exception as e:
                print(f"[WARNING] vilib initialization failed: {e}")
                print("[INFO] Falling back to mock detector")
                self.detector = MockDetector()
                self.detection_backend = 'mock'
        
        else:  # mock
            self.detector = MockDetector()
            self.detection_backend = 'mock'
            print("[INFO] Using mock detector (PC development mode)")
    
    def detect_objects(self, frame=None):
        """
        Detect objects in frame.
        
        Args:
            frame: Optional image frame. If None, captures from camera.
        
        Returns:
            List of detection dictionaries with normalized labels
        """
        return self.detector.detect_objects(frame)
    
    def should_stop(self, detections=None, stop_classes=None):
        """
        Check if car should stop based on detections.
        
        Args:
            detections: List of detections (if None, will detect)
            stop_classes: List of class names that require stopping.
                         Default: ['person', 'stop sign']
        
        Returns:
            (should_stop: bool, detected_class: str or None)
        """
        if stop_classes is None:
            stop_classes = ['person', 'stop sign']
        
        if detections is None:
            detections = self.detect_objects()
        
        # Normalize stop classes for comparison
        stop_classes_normalized = [normalize_label(c) for c in stop_classes]
        
        for detection in detections:
            detected_class = normalize_label(detection['class'])
            if detected_class in stop_classes_normalized:
                return True, detected_class
        
        return False, None
    
    def get_frame(self):
        """Get current camera frame"""
        return self.detector.get_frame()
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self.detector, 'cleanup'):
            self.detector.cleanup()


class VisionOverride:
    """
    Vision override state for integration with mapping/routing.
    Provides a clean interface for Step 7 to override Step 6/8 navigation.
    """
    
    def __init__(self):
        self.person_present = False
        self.stop_sign_present = False
        self.stop_until_ts = 0.0  # Timestamp until which to stop
    
    def update(self, person_present, stop_sign_present, now=None):
        """
        Update vision override state.
        
        Args:
            person_present: Whether person is detected
            stop_sign_present: Whether stop sign is detected
            now: Current timestamp (default: time.time())
        """
        if now is None:
            now = time.time()
        
        self.person_present = person_present
        
        # If stop sign detected, stop for 2 seconds
        if stop_sign_present:
            self.stop_until_ts = max(self.stop_until_ts, now + 2.0)
    
    def should_stop(self, now=None):
        """
        Check if car should stop.
        
        Args:
            now: Current timestamp (default: time.time())
        
        Returns:
            True if car should stop
        """
        if now is None:
            now = time.time()
        
        # Stop if person present or within stop sign timeout
        return self.person_present or (now < self.stop_until_ts)
    
    def get_status(self):
        """Get current override status"""
        return {
            'person_present': self.person_present,
            'stop_sign_present': self.stop_sign_present,
            'stop_until_ts': self.stop_until_ts,
            'should_stop': self.should_stop()
        }


def visualize_detections(frame, detections, fps=0.0, override_status=None):
    """
    Draw detections on frame for visualization.
    
    Args:
        frame: Image frame (BGR format)
        detections: List of detection dictionaries
        fps: Current FPS
        override_status: VisionOverride status dict (optional)
    
    Returns:
        Annotated frame
    """
    if not OPENCV_AVAILABLE:
        return frame
    
    annotated = frame.copy()
    
    # Draw FPS
    cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Draw detections
    for det in detections:
        x, y, w, h = det['bbox']
        label = det['class']
        confidence = det['confidence']
        
        # Color based on class
        if 'person' in label:
            color = (0, 0, 255)  # Red for person
        elif 'stop sign' in label:
            color = (0, 165, 255)  # Orange for stop sign
        else:
            color = (0, 255, 0)  # Green for others
        
        # Draw bounding box
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        
        # Draw label and confidence
        label_text = f"{label} {confidence:.2f}"
        label_size, _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_y = max(y, label_size[1] + 10)
        
        # Background for text
        cv2.rectangle(annotated, (x, label_y - label_size[1] - 5),
                     (x + label_size[0], label_y + 5), color, -1)
        cv2.putText(annotated, label_text, (x, label_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Draw override status
    if override_status:
        y_offset = 50
        if override_status.get('person_present'):
            cv2.putText(annotated, "PERSON DETECTED - STOP!", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y_offset += 30
        if override_status.get('stop_sign_present'):
            cv2.putText(annotated, "STOP SIGN - STOP!", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            y_offset += 30
        if override_status.get('should_stop'):
            cv2.putText(annotated, ">>> STOPPING <<<", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)
    
    return annotated


def test_object_detection_with_viewer(show_viewer=True):
    """
    Test object detection system with optional viewer window.
    
    Args:
        show_viewer: If True, shows OpenCV window with detections
    """
    print("=" * 60)
    print("Object Detection Test")
    if show_viewer:
        print("(Viewer window will open - press 'q' to quit)")
    print("=" * 60)
    
    if show_viewer and not OPENCV_AVAILABLE:
        print("[WARNING] OpenCV not available, viewer disabled")
        show_viewer = False
    
    # Create detector (auto-selects best available)
    detector = ObjectDetector(method='auto')
    
    print(f"\nUsing backend: {detector.detection_backend}")
    print(f"Running on: {'Raspberry Pi' if is_raspberry_pi() else 'PC'}")
    print(f"Viewer: {'Enabled' if show_viewer else 'Disabled'}\n")
    
    # Create override for integration demo
    override = VisionOverride()
    
    # FPS tracking
    last_time = time.time()
    fps = 0.0
    frame_count = 0
    
    try:
        while True:
            frame_start = time.time()
            
            # Get frame
            frame = detector.get_frame()
            if frame is None:
                print("[WARNING] Could not get frame, skipping...")
                time.sleep(0.1)
                continue
            
            # Detect objects
            detections = detector.detect_objects(frame)
            
            # Check for critical objects
            person_present = any('person' in normalize_label(d['class']) for d in detections)
            stop_sign_present = any('stop sign' in normalize_label(d['class']) for d in detections)
            
            # Update override
            override.update(person_present, stop_sign_present, time.time())
            
            # Calculate FPS
            frame_time = time.time() - frame_start
            if frame_time > 0:
                current_fps = 1.0 / frame_time
                fps = 0.9 * fps + 0.1 * current_fps  # Exponential moving average
            
            frame_count += 1
            
            # Print status every 10 frames
            if frame_count % 10 == 0:
                print(f"Frame {frame_count}: {len(detections)} objects, FPS: {fps:.1f}")
                if detections:
                    for det in detections:
                        print(f"  - {det['class']} ({det['confidence']:.2f})")
                if override.should_stop():
                    print("  >>> STOP REQUIRED <<<")
            
            # Visualize
            if show_viewer:
                annotated = visualize_detections(
                    frame, detections, fps, override.get_status()
                )
                cv2.imshow("Object Detection", annotated)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\nQuitting (q pressed)...")
                    break
            else:
                # No viewer, just print occasionally
                if frame_count % 30 == 0:
                    print(f"Frame {frame_count}: {len(detections)} objects detected")
                
                time.sleep(0.1)  # Small delay when no viewer
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        # Cleanup
        if show_viewer:
            cv2.destroyAllWindows()
        detector.cleanup()
        
        print("\n" + "=" * 60)
        print("Object detection test complete!")
        print(f"Total frames processed: {frame_count}")
        print(f"Average FPS: {fps:.1f}")
        print("=" * 60)


def test_object_detection():
    """Test object detection system (no viewer, quick test)"""
    print("=" * 60)
    print("Object Detection Test (Quick)")
    print("=" * 60)
    
    # Create detector (auto-selects best available)
    detector = ObjectDetector(method='auto')
    
    print(f"\nUsing backend: {detector.detection_backend}")
    print(f"Running on: {'Raspberry Pi' if is_raspberry_pi() else 'PC'}\n")
    
    # Test detection
    print("Testing object detection...")
    for i in range(5):
        detections = detector.detect_objects()
        
        if detections:
            print(f"  Frame {i+1}: Detected {len(detections)} object(s)")
            for det in detections:
                print(f"    - {det['class']} (confidence: {det['confidence']:.2f})")
        else:
            print(f"  Frame {i+1}: No objects detected")
        
        time.sleep(0.5)
    
    # Test stop logic
    print("\nTesting stop logic...")
    detections = [
        {'class': 'person', 'confidence': 0.9, 'bbox': (100, 100, 50, 100)},
        {'class': 'stop sign', 'confidence': 0.7, 'bbox': (200, 150, 30, 50)}
    ]
    
    should_stop, detected_class = detector.should_stop(detections)
    print(f"  Should stop: {should_stop}")
    print(f"  Detected class: {detected_class}")
    
    # Test VisionOverride
    print("\nTesting VisionOverride integration...")
    override = VisionOverride()
    override.update(person_present=True, stop_sign_present=False)
    print(f"  Should stop (person): {override.should_stop()}")
    
    override.update(person_present=False, stop_sign_present=True)
    print(f"  Should stop (stop sign): {override.should_stop()}")
    print(f"  Status: {override.get_status()}")
    
    # Cleanup
    detector.cleanup()
    
    print("\n" + "=" * 60)
    print("Object detection test complete!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Object Detection Test')
    parser.add_argument('--viewer', action='store_true', 
                       help='Show viewer window with detections')
    parser.add_argument('--no-viewer', action='store_true',
                       help='Run without viewer (quick test)')
    args = parser.parse_args()
    
    if args.viewer or (not args.no_viewer and OPENCV_AVAILABLE):
        # Run with viewer
        test_object_detection_with_viewer(show_viewer=True)
    else:
        # Quick test without viewer
        test_object_detection()
