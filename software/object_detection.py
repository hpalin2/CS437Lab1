"""
Part 2, Step 2.2: Object Detection
Detects objects using camera feed and reacts accordingly.

Backend: MediaPipe Tasks Object Detector
- Works on both PC (webcam) and Raspberry Pi (Picamera2 / rpicam-vid)
- Detects 80 COCO classes: person, stop sign, vehicles, furniture, etc.
- Model: efficientdet_lite2.tflite
"""

import time
import os
import sys
import warnings
import numpy as np
from collections import defaultdict
from hardware_mock import is_raspberry_pi

# Suppress protobuf deprecation warnings
warnings.filterwarnings('ignore', category=UserWarning, module='google.protobuf')

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

# Try Picamera2 for Raspberry Pi
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

# Check for rpicam command-line tools (Raspberry Pi 5 workaround)
RPICAM_AVAILABLE = False
try:
    import subprocess
    result = subprocess.run(['which', 'rpicam-vid'], 
                          capture_output=True, timeout=1)
    RPICAM_AVAILABLE = (result.returncode == 0)
except:
    RPICAM_AVAILABLE = False


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
            possible_paths = [
                'models/efficientdet_lite2.tflite',
                'efficientdet_lite2.tflite',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    model_path = path
                    break

            if model_path is None:
                raise FileNotFoundError(
                    "Model file not found: models/efficientdet_lite2.tflite\n"
                    "Run: python download_model.py"
                )
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Initialize MediaPipe object detector
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.ObjectDetectorOptions(
            base_options=base_options,
            score_threshold=0.3,  # Lowered from 0.5 for Pi camera compatibility
            max_results=5,
            running_mode=vision.RunningMode.IMAGE,
        )
        self.detector = vision.ObjectDetector.create_from_options(options)
        
        # Initialize camera
        self.camera = None
        self.camera_index = camera_index
        self.use_picamera2 = use_picamera2
        self.use_rpicam = False
        self.rpicam_process = None
        
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
            # On Raspberry Pi 5, try V4L2 backend explicitly
            if is_raspberry_pi():
                # Try V4L2 backend first
                self.camera = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
                if not self.camera.isOpened():
                    # Fallback to default backend
                    self.camera = cv2.VideoCapture(camera_index)
            else:
                self.camera = cv2.VideoCapture(camera_index)
            
            if not self.camera.isOpened():
                raise RuntimeError(f"Could not open camera {camera_index}")
            
            # Set camera properties for better compatibility
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 10)
            
            # Try to read a test frame to verify it works
            import time
            time.sleep(0.2)  # Give camera time to initialize
            ret, test_frame = self.camera.read()
            if not ret or test_frame is None:
                # OpenCV can't read frames - try rpicam-vid workaround on Raspberry Pi
                if is_raspberry_pi() and RPICAM_AVAILABLE:
                    print("[INFO] OpenCV cannot read frames, using rpicam-vid workaround")
                    self.use_rpicam = True
                    self.camera.release()
                    self.camera = None
                else:
                    print(f"[WARNING] Camera opened but cannot read frames.")
                    if is_raspberry_pi():
                        print(f"[WARNING] On Raspberry Pi 5, you may need rpicam-vid or libcamera Python bindings")
            
            if not self.use_rpicam:
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
                # Validate frame
                if frame is None or frame.size == 0:
                    print("[ERROR] Picamera2 returned empty frame")
                    return None
                # Picamera2 returns RGB, convert to BGR for OpenCV compatibility
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                return frame_bgr
            except Exception as e:
                print(f"[ERROR] Picamera2 capture failed: {e}")
                return None
        elif self.use_rpicam:
            # Use rpicam-vid as workaround (captures single frame)
            try:
                import subprocess
                import tempfile
                import os
                
                # Create temp file for frame
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                
                # Capture single frame using rpicam-vid
                cmd = ['rpicam-vid', '--width', '640', '--height', '480', 
                       '--nopreview', '--timeout', '100', '--output', tmp_path]
                result = subprocess.run(cmd, capture_output=True, timeout=2)
                
                if result.returncode == 0 and os.path.exists(tmp_path):
                    # Read the captured frame
                    frame = cv2.imread(tmp_path)
                    os.unlink(tmp_path)  # Clean up
                    if frame is not None:
                        return frame
                
                # If that failed, try rpicam-still instead
                cmd = ['rpicam-still', '--width', '640', '--height', '480', 
                       '--nopreview', '--timeout', '100', '--output', tmp_path]
                result = subprocess.run(cmd, capture_output=True, timeout=2)
                
                if result.returncode == 0 and os.path.exists(tmp_path):
                    frame = cv2.imread(tmp_path)
                    os.unlink(tmp_path)
                    return frame
                
                return None
            except Exception as e:
                print(f"[ERROR] rpicam capture failed: {e}")
                return None
        else:
            # OpenCV capture with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                ret, frame = self.camera.read()
                if ret and frame is not None and frame.size > 0:
                    return frame
                # If first attempt fails, try to reinitialize
                if attempt == 0 and not ret:
                    import time
                    time.sleep(0.1)
                    # Try to set properties again
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
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
        
        # Validate frame dimensions and format
        if frame.size == 0 or len(frame.shape) < 2:
            print("[WARNING] Invalid frame dimensions, skipping detection")
            return []
        
        frame_height, frame_width = frame.shape[:2]
        
        # Resize for speed (optional, but recommended for Pi)
        # Keep original size for better accuracy, or resize for speed
        # frame = cv2.resize(frame, (320, 240))  # Uncomment for faster processing
        
        try:
            # Convert BGR to RGB
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = frame
            
            # Create MediaPipe image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            
            # Detect objects
            detection_result = self.detector.detect(mp_image)
            
            # Convert to our format with normalized labels and validated bboxes
            detections = []
            for detection in detection_result.detections:
                bbox = detection.bounding_box
                category = detection.categories[0]
                
                # Validate and clamp bounding box coordinates
                x = max(0, min(bbox.origin_x, frame_width - 1))
                y = max(0, min(bbox.origin_y, frame_height - 1))
                w = max(1, min(bbox.width, frame_width - x))
                h = max(1, min(bbox.height, frame_height - y))
                
                # Skip invalid detections (bounding box too small or malformed)
                if w < 5 or h < 5:
                    continue
                
                # Normalize label (handles "stop sign" vs "stop_sign", etc.)
                label = normalize_label(category.category_name)
                
                detections.append({
                    'class': label,
                    'confidence': category.score,
                    'bbox': (x, y, w, h)
                })
            
            return detections
        
        except Exception as e:
            print(f"[ERROR] Detection failed: {e}")
            return []
    
    def cleanup(self):
        """Clean up resources"""
        if self.use_picamera2 and self.camera:
            try:
                self.camera.stop()
            except:
                pass
        elif self.use_rpicam:
            # rpicam cleanup (subprocess handles it)
                pass
        elif self.camera:
            try:
                self.camera.release()
            except:
                pass


class ObjectDetector:
    """
    Object detector interface.
    Backend: MediaPipe Tasks Object Detector (EfficientDet-Lite2, 80 COCO classes).
    Falls back to MockDetector if MediaPipe is unavailable.
    """

    def __init__(self, method='auto', model_path=None, camera_index=0):
        """
        Initialize detector.

        Args:
            method: 'auto', 'mediapipe', or 'mock'
            model_path: Path to .tflite model (default: models/efficientdet_lite2.tflite)
            camera_index: Camera index for OpenCV (PC)
        """
        self.method = method
        self.detector = None
        self.detection_backend = None
        # Temporal smoothing state for robustness (reduces one-frame false positives).
        self._critical_classes = {"person", "stop sign", "traffic light"}
        self._critical_hits = defaultdict(int)  # class -> recent consecutive hit count
        self._critical_last_seen_ts = defaultdict(float)

        if method == 'auto':
            method = 'mediapipe' if MEDIAPIPE_AVAILABLE else 'mock'

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
        raw = self.detector.detect_objects(frame)
        deduped = self._dedupe_detections(raw)
        return self._stabilize_critical_detections(deduped)
    
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

    @staticmethod
    def _bbox_iou(b1, b2):
        """Compute IoU between two bboxes (x, y, w, h)."""
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        ax1, ay1, ax2, ay2 = x1, y1, x1 + w1, y1 + h1
        bx1, by1, bx2, by2 = x2, y2, x2 + w2, y2 + h2

        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        inter = iw * ih
        if inter <= 0:
            return 0.0
        union = (w1 * h1) + (w2 * h2) - inter
        if union <= 0:
            return 0.0
        return inter / union

    def _dedupe_detections(self, detections, iou_threshold=0.55):
        """
        Remove overlapping duplicates of the same class.
        Keeps highest-confidence boxes first (simple class-wise NMS).
        """
        if not detections:
            return []

        sorted_dets = sorted(
            detections, key=lambda d: d.get('confidence', d.get('score', 0.0)), reverse=True
        )
        kept = []
        for det in sorted_dets:
            cls = normalize_label(det.get('class', ''))
            bbox = det.get('bbox', (0, 0, 0, 0))
            is_duplicate = False
            for kd in kept:
                if normalize_label(kd.get('class', '')) != cls:
                    continue
                if self._bbox_iou(bbox, kd.get('bbox', (0, 0, 0, 0))) >= iou_threshold:
                    is_duplicate = True
                    break
            if not is_duplicate:
                kept.append(det)
        return kept

    def _stabilize_critical_detections(self, detections):
        """
        Apply temporal confirmation for safety-critical classes:
        - High-confidence detections pass immediately.
        - Mid-confidence detections need to appear in >=2 nearby frames.
        Non-critical classes pass through unchanged.
        """
        now = time.time()
        stabilized = []
        seen_now = set()

        for det in detections:
            cls = normalize_label(det.get('class', ''))
            conf = det.get('confidence', det.get('score', 0.0))
            if cls in self._critical_classes:
                last_seen = self._critical_last_seen_ts[cls]
                if (now - last_seen) <= 0.8:
                    self._critical_hits[cls] += 1
                else:
                    self._critical_hits[cls] = 1
                self._critical_last_seen_ts[cls] = now
                seen_now.add(cls)

                # Immediate accept at strong confidence, otherwise require persistence.
                if conf >= 0.65 or self._critical_hits[cls] >= 2:
                    stabilized.append(det)
            else:
                stabilized.append(det)

        # Decay stale critical classes so old history does not leak indefinitely.
        for cls in list(self._critical_hits.keys()):
            if cls in seen_now:
                continue
            if (now - self._critical_last_seen_ts.get(cls, 0.0)) > 1.2:
                self._critical_hits[cls] = 0

        return stabilized


class VisionOverride:
    """
    Vision override state for integration with mapping/routing.
    Provides a clean interface for Step 2.2 to override Step 2.1/2.3 navigation.
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
        
        # If stop sign detected, stop for 2 seconds from NOW
        # (Don't extend indefinitely - reset to 2 seconds from current time)
        if stop_sign_present:
            self.stop_sign_present = True
            self.stop_until_ts = now + 2.0  # Fixed: was using max(), now resets properly
        else:
            # Clear stop sign flag if not currently detected
            if now >= self.stop_until_ts:
                self.stop_sign_present = False
    
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
    
    annotated = np.array(frame, dtype=np.uint8)
    annotated = np.ascontiguousarray(annotated)
    
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


def test_object_detection_with_viewer(show_viewer=True, target_fps=10):
    """
    Test object detection system with optional viewer window.
    
    Args:
        show_viewer: If True, shows OpenCV window with detections
        target_fps: Target FPS to limit CPU usage (None for unlimited)
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
    print(f"Viewer: {'Enabled' if show_viewer else 'Disabled'}")
    if target_fps:
        print(f"Target FPS: {target_fps} (CPU optimized)\n")
    else:
        print("Target FPS: Unlimited\n")
    
    # Create override for integration demo
    override = VisionOverride()
    
    # FPS tracking with better initialization
    fps = target_fps if target_fps else 10.0  # Better initial value
    frame_count = 0
    min_frame_time = (1.0 / target_fps) if target_fps else 0.0
    
    # Detection debouncing to reduce flicker
    person_debounce = 0  # Counter for person detections
    stop_sign_debounce = 0  # Counter for stop sign detections
    DEBOUNCE_THRESHOLD = 2  # Need N consecutive detections to trigger
    
    try:
        while True:
            frame_start = time.time()
            
            # Get frame with error recovery
            frame = detector.get_frame()
            if frame is None:
                print("[WARNING] Could not get frame, retrying...")
                time.sleep(0.1)
                continue
            
            # Detect objects
            detections = detector.detect_objects(frame)
            
            # Check for critical objects with debouncing
            person_detected = any('person' in normalize_label(d['class']) for d in detections)
            stop_sign_detected = any('stop sign' in normalize_label(d['class']) for d in detections)
            
            # Update debounce counters
            if person_detected:
                person_debounce = min(person_debounce + 1, DEBOUNCE_THRESHOLD)
            else:
                person_debounce = max(person_debounce - 1, 0)
            
            if stop_sign_detected:
                stop_sign_debounce = min(stop_sign_debounce + 1, DEBOUNCE_THRESHOLD)
            else:
                stop_sign_debounce = max(stop_sign_debounce - 1, 0)
            
            # Only trigger if debounce threshold met
            person_present = person_debounce >= DEBOUNCE_THRESHOLD
            stop_sign_present = stop_sign_debounce >= DEBOUNCE_THRESHOLD
            
            # Update override
            override.update(person_present, stop_sign_present, time.time())
            
            # Calculate FPS with exponential moving average
            frame_time = time.time() - frame_start
            if frame_time > 0:
                current_fps = 1.0 / frame_time
                # Smooth FPS calculation
                fps = 0.9 * fps + 0.1 * current_fps
            
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
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nQuitting (q pressed)...")
                    break
            else:
                # No viewer, just print occasionally
                if frame_count % 30 == 0:
                    print(f"Frame {frame_count}: {len(detections)} objects detected")
            
            # FPS limiting to reduce CPU usage
            if target_fps:
                elapsed = time.time() - frame_start
                sleep_time = max(0, min_frame_time - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
    
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
