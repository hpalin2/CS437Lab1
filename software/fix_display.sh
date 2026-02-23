#!/bin/bash
# Try to fix DISPLAY variable for X11 forwarding

echo "Attempting to fix DISPLAY variable..."
echo ""

# Check current DISPLAY
echo "Current DISPLAY: ${DISPLAY:-NOT SET}"
echo ""

# Common X11 display values to try
DISPLAY_VALUES=("localhost:10.0" ":10.0" "localhost:0" ":0" "127.0.0.1:10.0")

for display_val in "${DISPLAY_VALUES[@]}"; do
    export DISPLAY=$display_val
    echo "Trying DISPLAY=$display_val..."
    
    # Test if it works
    if xset q &>/dev/null 2>&1; then
        echo "✓ SUCCESS! DISPLAY=$display_val works!"
        echo ""
        echo "Add this to your ~/.bashrc:"
        echo "  export DISPLAY=$display_val"
        echo ""
        echo "Or run this command now:"
        echo "  export DISPLAY=$display_val"
        echo ""
        echo "Then try:"
        echo "  python3 object_detection.py --viewer"
        exit 0
    fi
done

echo "✗ Could not find working DISPLAY value"
echo ""
echo "Troubleshooting steps:"
echo "1. On your Windows machine, ensure X server is running (VcXsrv/Xming)"
echo "2. Check X server settings - it should allow connections from localhost"
echo "3. Try reconnecting: exit, then ssh -Y hraspi"
echo "4. After reconnecting, check: echo \$DISPLAY"
echo "5. If still empty, try manually: export DISPLAY=localhost:10.0"
