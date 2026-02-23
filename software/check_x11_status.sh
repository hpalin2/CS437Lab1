#!/bin/bash
# Comprehensive X11 forwarding status check

echo "============================================================"
echo "X11 Forwarding Status Check"
echo "============================================================"
echo ""

# Check DISPLAY
echo "1. DISPLAY variable:"
if [ -z "$DISPLAY" ]; then
    echo "   ✗ NOT SET"
    echo "   → X11 forwarding is not active in this session"
    echo "   → Reconnect with: ssh -Y hraspi (or ssh -Y hpalin@192.168.40.90)"
else
    echo "   ✓ SET to: $DISPLAY"
fi
echo ""

# Check SSH connection
echo "2. SSH Connection:"
if [ -n "$SSH_CONNECTION" ]; then
    echo "   ✓ Connected via SSH"
    echo "   Connection: $SSH_CONNECTION"
else
    echo "   ✗ Not in SSH session"
fi
echo ""

# Check xauth
echo "3. xauth status:"
if command -v xauth &> /dev/null; then
    echo "   ✓ xauth is installed"
    if [ -f ~/.Xauthority ]; then
        echo "   ✓ .Xauthority file exists"
        entries=$(xauth list 2>/dev/null | wc -l)
        if [ "$entries" -gt 0 ]; then
            echo "   ✓ xauth has $entries entries"
            echo "   Entries:"
            xauth list 2>/dev/null | sed 's/^/     /'
        else
            echo "   ✗ xauth has no entries"
        fi
    else
        echo "   ✗ .Xauthority file does not exist"
        echo "   → This is normal if X11 forwarding wasn't enabled"
    fi
else
    echo "   ✗ xauth is not installed"
fi
echo ""

# Check SSH server config
echo "4. SSH Server Configuration:"
if sudo grep -q "^X11Forwarding yes" /etc/ssh/sshd_config 2>/dev/null; then
    echo "   ✓ X11Forwarding is enabled on server"
else
    echo "   ✗ X11Forwarding may not be enabled"
    echo "   → Check: sudo grep X11Forwarding /etc/ssh/sshd_config"
fi
echo ""

# Summary and recommendations
echo "============================================================"
echo "Summary & Next Steps"
echo "============================================================"
echo ""

if [ -z "$DISPLAY" ]; then
    echo "⚠️  X11 forwarding is NOT active in this session"
    echo ""
    echo "To enable X11 forwarding:"
    echo ""
    echo "1. On your LOCAL machine, ensure X server is running:"
    echo "   - Linux: Usually already running"
    echo "   - macOS: Install and start XQuartz"
    echo "   - Windows: Install and start VcXsrv or Xming"
    echo ""
    echo "2. Disconnect and reconnect with X11 forwarding:"
    echo "   exit"
    echo "   ssh -Y hraspi"
    echo "   # OR if you updated SSH config:"
    echo "   ssh hraspi"
    echo ""
    echo "3. After reconnecting, test:"
    echo "   cd /home/hpalin/CS437Lab1/software"
    echo "   ./test_x11.sh"
    echo "   # or: xeyes"
    echo ""
else
    echo "✓ X11 forwarding appears to be active!"
    echo ""
    echo "Test it:"
    echo "  xeyes"
    echo "  # or"
    echo "  cd /home/hpalin/CS437Lab1/software"
    echo "  source /home/hpalin/py311/bin/activate"
    echo "  python3 object_detection.py --viewer"
fi
echo ""
