#!/bin/bash
# Script to download EfficientDet-Lite model for MediaPipe Object Detection
# Run this to get the model file needed for object_detection.py

MODEL_DIR="models"
MODEL_NAME="efficientdet_lite0.tflite"
MODEL_URL="https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float16/1/efficientdet_lite0.tflite"

# Create models directory if it doesn't exist
mkdir -p "$MODEL_DIR"

# Download model
echo "Downloading EfficientDet-Lite0 model..."
curl -L "$MODEL_URL" -o "$MODEL_DIR/$MODEL_NAME"

if [ $? -eq 0 ]; then
    echo "Model downloaded successfully to $MODEL_DIR/$MODEL_NAME"
    echo "You can now use object_detection.py with MediaPipe backend"
else
    echo "Download failed. Please download manually from:"
    echo "https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/python"
fi
