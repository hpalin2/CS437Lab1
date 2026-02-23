# X11 Forwarding Setup Guide

This guide helps you set up X11 forwarding so you can see the object detection viewer window when running on Raspberry Pi via SSH.

## Quick Setup

Run the setup script:
```bash
cd /home/hpalin/CS437Lab1/software
./setup_x11_forwarding.sh
```

## Step-by-Step Setup

### 1. On Your Local Machine (Where You SSH From)

#### Linux
- X server is usually already running
- Just use `ssh -X` or `ssh -Y`

#### macOS
- Install XQuartz: `brew install --cask xquartz`
- Restart your terminal
- XQuartz should start automatically

#### Windows
- Install one of:
  - **VcXsrv** (recommended): https://sourceforge.net/projects/vcxsrv/
  - **Xming**: https://sourceforge.net/projects/xming/
- Start the X server before SSH'ing

### 2. Configure SSH Server (on Raspberry Pi)

Edit `/etc/ssh/sshd_config`:
```bash
sudo nano /etc/ssh/sshd_config
```

Ensure these lines are present and uncommented:
```
X11Forwarding yes
X11DisplayOffset 10
X11UseLocalhost no  # or yes, depending on your setup
```

Restart SSH service:
```bash
sudo systemctl restart ssh
```

### 3. Connect with X11 Forwarding

**Trusted forwarding (recommended):**
```bash
ssh -Y username@raspberry-pi-ip
```

**Untrusted forwarding:**
```bash
ssh -X username@raspberry-pi-ip
```

**With specific display:**
```bash
ssh -Y -o ForwardX11=yes username@raspberry-pi-ip
```

### 4. Test X11 Forwarding

Once connected, test with a simple X11 app:
```bash
# Install a test app if needed
sudo apt-get install -y x11-apps

# Test
xeyes
# or
xclock
```

If you see a window, X11 forwarding is working!

### 5. Run Object Detection with Viewer

```bash
source /home/hpalin/py311/bin/activate
cd /home/hpalin/CS437Lab1/software
python3 object_detection.py --viewer
```

You should see the camera feed with bounding boxes!

## Troubleshooting

### "Could not connect to display"

**Check DISPLAY variable:**
```bash
echo $DISPLAY
# Should show something like: localhost:10.0 or :10.0
```

**If empty, set it manually:**
```bash
export DISPLAY=localhost:10.0
# or
export DISPLAY=:10.0
```

**Check xauth:**
```bash
xauth list
# Should show entries
```

### "No protocol specified"

**Fix permissions:**
```bash
xhost +local:
# Or more securely:
xhost +SI:localuser:$(whoami)
```

### "qt.qpa.xcb: could not connect to display"

This means X11 forwarding isn't working. Try:
1. Reconnect with `ssh -Y` flag
2. Check `echo $DISPLAY` is set
3. Test with `xeyes` first
4. Check SSH server config has `X11Forwarding yes`

### Performance Issues

X11 forwarding can be slow over network. Options:
- Use `--no-viewer` mode (headless)
- Use VNC instead: `sudo apt-get install tightvncserver`
- Use X11 compression: `ssh -XC username@host`

## Alternative: VNC (Better for Remote Desktop)

If X11 forwarding is too slow or problematic:

```bash
# Install VNC server
sudo apt-get install -y tightvncserver

# Start VNC server
vncserver :1

# Connect from local machine using VNC viewer
# Then run object detection normally
```

## Quick Reference

**Connect with X11:**
```bash
ssh -Y username@raspberry-pi-ip
```

**Test X11:**
```bash
xeyes
```

**Run detection with viewer:**
```bash
source /home/hpalin/py311/bin/activate
cd /home/hpalin/CS437Lab1/software
python3 object_detection.py --viewer
```

**Run without viewer (headless):**
```bash
python3 object_detection.py --no-viewer
```
