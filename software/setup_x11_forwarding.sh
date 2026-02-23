#!/bin/bash
# Setup script for X11 forwarding on Raspberry Pi

echo "============================================================"
echo "X11 Forwarding Setup for Object Detection Viewer"
echo "============================================================"
echo ""

# Check if we're in an SSH session
if [ -z "$SSH_CONNECTION" ]; then
    echo "[INFO] Not in an SSH session. X11 forwarding is typically used when"
    echo "       connecting via SSH from another machine."
    echo ""
fi

# Check if xauth is installed
if ! command -v xauth &> /dev/null; then
    echo "[INSTALL] Installing xauth..."
    sudo apt-get update
    sudo apt-get install -y xauth
else
    echo "[OK] xauth is installed"
fi

# Check X11 packages
echo ""
echo "Checking X11 packages..."
if dpkg -l | grep -q "libx11-6"; then
    echo "[OK] X11 libraries installed"
else
    echo "[INSTALL] Installing X11 libraries..."
    sudo apt-get install -y libx11-6 x11-common
fi

# Check OpenCV GUI support
echo ""
echo "Checking OpenCV GUI support..."
if python3 -c "import cv2; print(cv2.getBuildInformation())" 2>/dev/null | grep -q "GUI:"; then
    echo "[OK] OpenCV has GUI support"
else
    echo "[WARNING] OpenCV GUI support may be limited"
fi

echo ""
echo "============================================================"
echo "Setup Complete!"
echo "============================================================"
echo ""
echo "To use X11 forwarding:"
echo ""
echo "1. On your LOCAL machine (where you SSH from), ensure:"
echo "   - X server is running (XQuartz on Mac, Xming/VcXsrv on Windows,"
echo "     or native X on Linux)"
echo "   - SSH client supports X11 forwarding"
echo ""
echo "2. Connect to Raspberry Pi with X11 forwarding:"
echo "   ssh -X username@raspberry-pi-ip"
echo "   OR"
echo "   ssh -Y username@raspberry-pi-ip  (trusted forwarding)"
echo ""
echo "3. Test X11 forwarding:"
echo "   xeyes  # or any X11 app"
echo ""
echo "4. Run object detection with viewer:"
echo "   source /home/hpalin/py311/bin/activate"
echo "   cd /home/hpalin/CS437Lab1/software"
echo "   python3 object_detection.py --viewer"
echo ""
echo "If you're already connected via SSH, you may need to reconnect"
echo "with the -X or -Y flag for X11 forwarding to work."
echo ""
