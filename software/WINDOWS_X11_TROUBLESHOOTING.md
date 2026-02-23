# Windows X11 Forwarding Troubleshooting

## Current Issue
X11 forwarding is not working - DISPLAY is not set or X server can't connect.

## Step-by-Step Fix

### 1. On Windows: Install and Configure X Server

**Option A: VcXsrv (Recommended)**
1. Download: https://sourceforge.net/projects/vcxsrv/
2. Install VcXsrv
3. Start "XLaunch"
4. **Important settings:**
   - Display number: 0 (or leave default)
   - **Check "Disable access control"** (or add your IP to access list)
   - Start no client: checked
   - Clipboard: checked
   - Primary Selection: checked
5. Click "Finish"

**Option B: Xming**
1. Download: https://sourceforge.net/projects/xming/
2. Install Xming
3. Start Xming
4. Configure firewall if needed

### 2. Verify X Server is Running

On Windows, you should see the X server icon in the system tray.

### 3. Reconnect SSH with X11 Forwarding

In PowerShell:
```powershell
# Disconnect current session
exit

# Reconnect with X11 forwarding
ssh -Y hraspi
```

### 4. Check DISPLAY Variable

After reconnecting:
```bash
echo $DISPLAY
# Should show: localhost:10.0 or :10.0
```

If empty, try:
```bash
export DISPLAY=localhost:10.0
# or
export DISPLAY=:10.0
```

### 5. Test X11 Forwarding

```bash
xeyes
# Should open a window on Windows
```

If xeyes doesn't work, X11 forwarding isn't set up correctly.

### 6. Common Issues

**Issue: "Could not connect to display"**
- X server not running on Windows
- X server not configured to accept connections
- DISPLAY variable not set

**Fix:**
1. Ensure X server is running
2. Check X server settings (disable access control or add IP)
3. Set DISPLAY: `export DISPLAY=localhost:10.0`
4. Reconnect with `ssh -Y`

**Issue: "No protocol specified"**
- X server access control blocking connection

**Fix:**
- In VcXsrv: Check "Disable access control" when starting
- Or on Windows: Run `xhost +` (if available)

**Issue: DISPLAY not set after reconnecting**
- SSH X11 forwarding not working

**Fix:**
1. Check SSH config has `ForwardX11 yes`
2. Try `ssh -Y` explicitly
3. Check SSH server config: `sudo grep X11Forwarding /etc/ssh/sshd_config`

### 7. Alternative: Use Headless Mode

If X11 forwarding is too problematic, use headless mode:
```bash
python3 object_detection.py --no-viewer
```

This works perfectly and is faster!

### 8. Quick Test Script

Run this to diagnose:
```bash
cd /home/hpalin/CS437Lab1/software
./check_x11_status.sh
./fix_display.sh
```

## Recommended: VcXsrv Settings

When starting VcXsrv XLaunch:
- **Multiple windows** or **One large window** (your choice)
- **Display number: 0**
- **Start no client: ✓**
- **Clipboard: ✓**
- **Primary Selection: ✓**
- **Disable access control: ✓** ← IMPORTANT!

## Still Not Working?

1. **Use headless mode** - it works great:
   ```bash
   python3 object_detection.py --no-viewer
   ```

2. **Check Windows Firewall** - may be blocking X11

3. **Try different DISPLAY values:**
   ```bash
   export DISPLAY=localhost:10.0
   export DISPLAY=:10.0
   export DISPLAY=127.0.0.1:10.0
   ```

4. **Verify SSH config** on Windows has:
   ```
   Host hraspi
     ForwardX11 yes
     ForwardX11Trusted yes
   ```
