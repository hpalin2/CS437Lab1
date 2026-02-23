# Quick X11 Forwarding Setup

## ✅ Current Status

- ✅ SSH server configured (`X11Forwarding yes`)
- ✅ X11 packages installed
- ✅ xauth installed
- ⚠️  Current session doesn't have X11 forwarding (need to reconnect)

## 🚀 Quick Start

### Step 1: Reconnect with X11 Forwarding

**From your local machine, disconnect and reconnect:**
```bash
exit  # Disconnect from current SSH session

# Reconnect with X11 forwarding (trusted)
ssh -Y hpalin@192.168.40.90

# OR with untrusted forwarding
ssh -X hpalin@192.168.40.90
```

### Step 2: Test X11 Forwarding

Once reconnected, test:
```bash
cd /home/hpalin/CS437Lab1/software
./test_x11.sh
```

Or manually:
```bash
xeyes  # Should open a window on your local machine
```

### Step 3: Run Object Detection with Viewer

```bash
source /home/hpalin/py311/bin/activate
cd /home/hpalin/CS437Lab1/software
python3 object_detection.py --viewer
```

## 📋 What You Need on Your Local Machine

### Linux
- X server usually already running
- Just use `ssh -Y`

### macOS
- Install XQuartz: `brew install --cask xquartz`
- Restart terminal after installation
- XQuartz should auto-start

### Windows
- Install **VcXsrv** or **Xming**
- Start the X server before SSH'ing
- Use `ssh -Y` to connect

## 🔧 Troubleshooting

**If DISPLAY is not set after reconnecting:**
```bash
export DISPLAY=localhost:10.0
# or
export DISPLAY=:10.0
```

**If you get "No protocol specified":**
```bash
# On your LOCAL machine (not Pi):
xhost +local:
```

**If viewer still doesn't work:**
- Test with `xeyes` first to verify X11 works
- Check `echo $DISPLAY` shows a value
- Try `ssh -YC` for compression if network is slow

## 📝 Files Created

- `setup_x11_forwarding.sh` - Setup script
- `test_x11.sh` - Test X11 forwarding
- `X11_FORWARDING_GUIDE.md` - Detailed guide
- `QUICK_X11_SETUP.md` - This file

## 💡 Tip

If X11 forwarding is too slow or problematic, you can always use:
```bash
python3 object_detection.py --no-viewer
```

This works perfectly in headless mode and is faster!
