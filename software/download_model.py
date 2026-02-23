"""
Download EfficientDet-Lite model for MediaPipe Object Detection.
Run this script to download the model file needed for object_detection.py
"""

import os
import urllib.request

MODEL_DIR = "models"

# Available models — ordered best-to-fastest for this lab's use case (stop signs, people)
# Lite2: best stop-sign accuracy, ~40ms/frame on Pi 5 — recommended
# Lite0: fastest (~15ms), weaker on small/rotated signs — fallback
MODELS = {
    "lite2": {
        "name": "efficientdet_lite2.tflite",
        "url": "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite2/float16/1/efficientdet_lite2.tflite",
        "size_mb": 7.2,
        "notes": "Recommended — best stop-sign accuracy, ~40ms/frame on Pi 5",
    },
    "lite0": {
        "name": "efficientdet_lite0.tflite",
        "url": "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float16/1/efficientdet_lite0.tflite",
        "size_mb": 4.4,
        "notes": "Fastest (~15ms/frame) but weaker on small or angled signs",
    },
}

DEFAULT_MODEL = "lite2"


def download_model(model_key=DEFAULT_MODEL):
    """Download an EfficientDet-Lite model for MediaPipe."""
    model_info = MODELS[model_key]
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, model_info["name"])
    
    print(f"\nModel    : {model_info['name']}")
    print(f"Notes    : {model_info['notes']}")
    print(f"Size     : ~{model_info['size_mb']} MB")
    print(f"Target   : {model_path}")
    
    if os.path.exists(model_path):
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        print(f"\nAlready downloaded ({size_mb:.1f} MB). Skipping.")
            return model_path
    
    print(f"\nDownloading from {model_info['url']} ...")
    try:
        urllib.request.urlretrieve(model_info["url"], model_path)
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        print(f"Downloaded successfully ({size_mb:.1f} MB) → {model_path}")
        return model_path
    except Exception as e:
        print(f"Download failed: {e}")
        print("Please download manually from:")
        print("https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/python")
        return None

if __name__ == "__main__":
    import sys
    key = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    if key not in MODELS:
        print(f"Unknown model '{key}'. Choose from: {list(MODELS.keys())}")
        sys.exit(1)
    download_model(key)
