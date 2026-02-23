# Running Object Detection on Raspberry Pi's Own Display

## Quick Start

If you're logged in directly on the Raspberry Pi (not via SSH), you can use the Pi's own display/monitor.

### Method 1: Desktop Environment (Easiest)

If your Pi has a desktop environment (like Raspberry Pi OS Desktop):

1. **Login to the desktop** (GUI login or auto-login)

2. **Open a terminal** in the desktop

3. **Run object detection:**
   ```bash
   source /home/hpalin/py311/bin/activate
   cd /home/hpalin/CS437Lab1/software
   python3 object_detection.py --viewer
   ```

The viewer window will appear on the Pi's display!

### Method 2: Command Line with X Server

If you're logged in via console (text mode) but have a display connected:

1. **Start X server:**
   ```bash
   startx
   ```
   This will start the desktop environment.

2. **Or start just X server without desktop:**
   ```bash
   startx -- :0
   ```

3. **In the X session, open terminal and run:**
   ```bash
   source /home/hpalin/py311/bin/activate
   cd /home/hpalin/CS437Lab1/software
   python3 object_detection.py --viewer
   ```

### Method 3: Set DISPLAY Variable

If X server is already running but DISPLAY isn't set:

```bash
# Check if X server is running
ps aux | grep Xorg

# Set DISPLAY (usually :0 for local display)
export DISPLAY=:0

# Test
xeyes  # Should open on Pi's display

# Run object detection
source /home/hpalin/py311/bin/activate
cd /home/hpalin/CS437Lab1/software
python3 object_detection.py --viewer
```

### Method 4: Auto-start Desktop on Boot

If you want the desktop to start automatically:

```bash
# Enable desktop on boot
sudo systemctl set-default graphical.target

# Or disable (boot to console)
sudo systemctl set-default multi-user.target
```

## Checking Your Setup

### Check if display is connected:
```bash
# List connected displays
xrandr 2>/dev/null || echo "No X server running"

# Or check framebuffer
ls -la /dev/fb* 2>/dev/null
```

### Check if X server is running:
```bash
ps aux | grep -i xorg | grep -v grep
```

### Check DISPLAY variable:
```bash
echo $DISPLAY
# Should be :0 or :0.0 for local display
```

## Common Scenarios

### Scenario 1: Pi with HDMI Monitor
- Connect HDMI monitor to Pi
- Boot Pi (desktop should start automatically)
- Login and run object detection
- Viewer appears on monitor

### Scenario 2: Pi Headless (No Monitor)
- Use SSH (what you were doing)
- Use `--no-viewer` mode for headless operation
- Or set up VNC for remote desktop

### Scenario 3: Pi with Touchscreen
- Same as HDMI monitor
- Desktop should work automatically
- Run viewer normally

## Troubleshooting

### "Could not connect to display"
```bash
# Set DISPLAY
export DISPLAY=:0

# Or start X server
startx
```

### "No display detected"
- Check HDMI cable connection
- Check monitor is powered on
- Try: `sudo raspi-config` → Display Options

### Desktop not starting
```bash
# Enable desktop
sudo systemctl set-default graphical.target
sudo reboot
```

## Quick Reference

**Direct login on Pi with display:**
```bash
# Usually just works if desktop is running
source /home/hpalin/py311/bin/activate
cd /home/hpalin/CS437Lab1/software
python3 object_detection.py --viewer
```

**If DISPLAY not set:**
```bash
export DISPLAY=:0
python3 object_detection.py --viewer
```

**Headless (no display):**
```bash
python3 object_detection.py --no-viewer
```
