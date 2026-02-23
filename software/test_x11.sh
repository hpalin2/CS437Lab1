#!/bin/bash
# Quick test script for X11 forwarding

echo "Testing X11 forwarding setup..."
echo ""

# Check DISPLAY
if [ -z "$DISPLAY" ]; then
    echo "✗ DISPLAY is not set"
    echo "  You need to reconnect via SSH with X11 forwarding:"
    echo "  ssh -Y username@raspberry-pi-ip"
else
    echo "✓ DISPLAY is set: $DISPLAY"
fi

# Check xauth
if command -v xauth &> /dev/null; then
    echo "✓ xauth is installed"
    if xauth list | grep -q .; then
        echo "✓ xauth has entries"
    else
        echo "✗ xauth has no entries (X11 forwarding may not be active)"
    fi
else
    echo "✗ xauth is not installed"
fi

# Test with xeyes if available
if command -v xeyes &> /dev/null; then
    echo ""
    echo "Testing with xeyes (will open a window if X11 works)..."
    echo "Press Ctrl+C to close xeyes"
    timeout 3 xeyes 2>&1 || echo "xeyes test completed"
else
    echo ""
    echo "xeyes not installed. Install with: sudo apt-get install x11-apps"
fi

echo ""
echo "If xeyes worked, you can run:"
echo "  source /home/hpalin/py311/bin/activate"
echo "  cd /home/hpalin/CS437Lab1/software"
echo "  python3 object_detection.py --viewer"
