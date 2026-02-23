#!/bin/bash
# Quick start script for object detection using py311 virtual environment

# Activate virtual environment
source /home/hpalin/py311/bin/activate

# Change to software directory
cd /home/hpalin/CS437Lab1/software

# Run object detection
# Use --viewer to show camera feed with detections
# Use --no-viewer for quick test without display
python3 object_detection.py "$@"
