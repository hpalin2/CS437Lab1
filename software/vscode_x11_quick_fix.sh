#!/bin/bash
# Quick fix to enable X11 in VS Code terminal

echo "VS Code Remote SSH X11 Setup"
echo "=============================="
echo ""

# Check if we're in VS Code
if [ -n "$VSCODE_INJECTION" ] || [ -n "$VSCODE_IPC_HOOK_CLI" ]; then
    echo "✓ Detected VS Code Remote SSH"
else
    echo "ℹ Not detected as VS Code terminal (may still work)"
fi
echo ""

# Check current DISPLAY
echo "Current DISPLAY: ${DISPLAY:-NOT SET}"
echo ""

# Try to set DISPLAY if not set
if [ -z "$DISPLAY" ]; then
    echo "Attempting to set DISPLAY..."
    
    # Common X11 display values
    for display in "localhost:10.0" ":10.0" "localhost:0" ":0"; do
        export DISPLAY=$display
        if xset q &>/dev/null; then
            echo "✓ DISPLAY set to: $DISPLAY"
            echo ""
            echo "Add this to your ~/.bashrc or ~/.profile:"
            echo "  export DISPLAY=$display"
            exit 0
        fi
    done
    
    echo "✗ Could not auto-detect DISPLAY"
    echo ""
    echo "Manual setup options:"
    echo "1. Use separate terminal: ssh -Y hraspi"
    echo "2. Configure VS Code Remote SSH settings (see vscode_x11_setup.md)"
    echo "3. Set DISPLAY manually: export DISPLAY=localhost:10.0"
else
    echo "✓ DISPLAY is already set: $DISPLAY"
    echo ""
    echo "Test X11:"
    echo "  xeyes"
fi
