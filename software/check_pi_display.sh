#!/bin/bash
# Check Raspberry Pi display setup

echo "============================================================"
echo "Raspberry Pi Display Setup Check"
echo "============================================================"
echo ""

# Check if we're on Pi
if [ -f /proc/device-tree/model ]; then
    model=$(cat /proc/device-tree/model)
    echo "Device: $model"
else
    echo "Device: Not detected as Raspberry Pi"
fi
echo ""

# Check DISPLAY
echo "1. DISPLAY variable:"
if [ -z "$DISPLAY" ]; then
    echo "   ✗ NOT SET"
    echo "   → Try: export DISPLAY=:0"
else
    echo "   ✓ SET to: $DISPLAY"
fi
echo ""

# Check X server
echo "2. X Server status:"
if pgrep -x "Xorg" > /dev/null || pgrep -x "X" > /dev/null; then
    echo "   ✓ X server is running"
    x_process=$(pgrep -x "Xorg" || pgrep -x "X")
    echo "   Process ID: $x_process"
else
    echo "   ✗ X server is NOT running"
    echo "   → Start with: startx"
fi
echo ""

# Check framebuffer (display hardware)
echo "3. Display hardware:"
if ls /dev/fb* 1>/dev/null 2>&1; then
    echo "   ✓ Framebuffer devices found:"
    ls -1 /dev/fb* | sed 's/^/     /'
else
    echo "   ✗ No framebuffer devices (no display connected?)"
fi
echo ""

# Check desktop environment
echo "4. Desktop environment:"
if pgrep -x "xfce4-session" > /dev/null || pgrep -x "lxpanel" > /dev/null || pgrep -x "openbox" > /dev/null; then
    echo "   ✓ Desktop environment is running"
else
    echo "   ℹ Desktop environment not detected (may be running X only)"
fi
echo ""

# Check boot target
echo "5. Boot target:"
boot_target=$(systemctl get-default 2>/dev/null)
echo "   Current: $boot_target"
if [ "$boot_target" = "graphical.target" ]; then
    echo "   ✓ Desktop will start on boot"
elif [ "$boot_target" = "multi-user.target" ]; then
    echo "   ℹ Boots to console (no desktop)"
    echo "   → Enable desktop: sudo systemctl set-default graphical.target"
fi
echo ""

# Recommendations
echo "============================================================"
echo "Recommendations"
echo "============================================================"
echo ""

if [ -z "$DISPLAY" ]; then
    echo "To use the Pi's display:"
    echo ""
    if pgrep -x "Xorg" > /dev/null; then
        echo "  export DISPLAY=:0"
        echo "  # Then run: python3 object_detection.py --viewer"
    else
        echo "  startx"
        echo "  # Then in X session: python3 object_detection.py --viewer"
    fi
else
    echo "✓ DISPLAY is set - you should be able to run the viewer!"
    echo ""
    echo "Test with:"
    echo "  xeyes"
    echo "  # or"
    echo "  source /home/hpalin/py311/bin/activate"
    echo "  python3 object_detection.py --viewer"
fi
echo ""
