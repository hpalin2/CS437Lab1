# X11 Forwarding with VS Code Remote SSH

## Setup for VS Code Remote SSH

VS Code Remote SSH can forward X11, but it requires configuration in your VS Code settings.

### Method 1: VS Code Settings (Recommended)

1. **Open VS Code Settings:**
   - Press `Ctrl+,` (or `Cmd+,` on Mac)
   - Or: File → Preferences → Settings

2. **Search for:** `remote.SSH.remoteServerListenOnSocket`

3. **Add to your VS Code settings.json:**
   ```json
   {
     "remote.SSH.remoteServerListenOnSocket": false,
     "remote.SSH.enableX11Forwarding": true,
     "remote.SSH.showLoginTerminal": true
   }
   ```

4. **Or add to your SSH config** (on your local Windows machine):
   ```
   Host hraspi
     HostName 192.168.40.90
     User hpalin
     IdentityFile C:\Users\nippu\Downloads\Key\raspkey
     ForwardX11 yes
     ForwardX11Trusted yes
     RequestTTY yes
   ```

### Method 2: Use VS Code Integrated Terminal with X11

1. **In VS Code, open a terminal** (Terminal → New Terminal)

2. **Check if X11 is forwarded:**
   ```bash
   echo $DISPLAY
   ```

3. **If DISPLAY is not set, you can manually set it:**
   ```bash
   export DISPLAY=localhost:10.0
   # or try:
   export DISPLAY=:10.0
   ```

### Method 3: Use External Terminal (Easiest)

1. **Keep VS Code for editing code**

2. **Use a separate terminal** (Windows Terminal, PowerShell, or CMD) for running the viewer:
   ```bash
   ssh -Y hraspi
   ```

3. **In that terminal:**
   ```bash
   source /home/hpalin/py311/bin/activate
   cd /home/hpalin/CS437Lab1/software
   python3 object_detection.py --viewer
   ```

### Method 4: VS Code Tasks (Automated)

Create a VS Code task to run object detection with proper X11 setup.

## Recommended Approach

**For development:** Use VS Code Remote SSH for editing
**For running viewer:** Use a separate terminal with `ssh -Y hraspi`

This gives you:
- VS Code for code editing
- Separate terminal with X11 forwarding for the viewer

## Quick Test

In VS Code terminal, try:
```bash
echo $DISPLAY
```

If it's empty, X11 forwarding isn't active in VS Code's terminal. Use Method 3 (separate terminal) instead.
