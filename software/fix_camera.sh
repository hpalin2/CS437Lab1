#!/bin/bash
# Script to fix camera access on Raspberry Pi 5

echo "Installing libcamera Python bindings (requires sudo)..."
echo "This will install python3-libcamera system-wide"

sudo apt-get update
sudo apt-get install -y python3-libcamera

echo ""
echo "After installation, try running object detection again:"
echo "  source /home/hpalin/py311/bin/activate"
echo "  cd /home/hpalin/CS437Lab1/software"
echo "  python3 object_detection.py --viewer"
