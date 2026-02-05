"""
Download EfficientDet-Lite model for MediaPipe Object Detection.
Run this script to download the model file needed for object_detection.py
"""

import os
import urllib.request

MODEL_DIR = "models"
MODEL_NAME = "efficientdet_lite0.tflite"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float16/1/efficientdet_lite0.tflite"

def download_model():
    """Download the EfficientDet-Lite model"""
    # Create models directory if it doesn't exist
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    model_path = os.path.join(MODEL_DIR, MODEL_NAME)
    
    # Check if model already exists
    if os.path.exists(model_path):
        print(f"Model already exists at {model_path}")
        response = input("Download again? (y/n): ")
        if response.lower() != 'y':
            return model_path
    
    print(f"Downloading EfficientDet-Lite0 model from {MODEL_URL}...")
    print(f"Target: {model_path}")
    
    try:
        urllib.request.urlretrieve(MODEL_URL, model_path)
        print(f"Model downloaded successfully to {model_path}")
        print(f"File size: {os.path.getsize(model_path) / (1024*1024):.2f} MB")
        return model_path
    except Exception as e:
        print(f"Download failed: {e}")
        print("\nPlease download manually from:")
        print("https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/python")
        return None

if __name__ == "__main__":
    download_model()
