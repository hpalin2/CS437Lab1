# SSH Config Update for X11 Forwarding

## Your Current Config

```
Host hraspi
  HostName 192.168.40.90
  User hpalin
  IdentityFile C:\Users\nippu\Downloads\Key\raspkey
```

## Updated Config (Add X11 Forwarding)

Add these two lines to enable X11 forwarding:

```
Host hraspi
  HostName 192.168.40.90
  User hpalin
  IdentityFile C:\Users\nippu\Downloads\Key\raspkey
  ForwardX11 yes
  ForwardX11Trusted yes
```

## Full Recommended Config

```
Host hraspi
  HostName 192.168.40.90
  User hpalin
  IdentityFile C:\Users\nippu\Downloads\Key\raspkey
  ForwardX11 yes
  ForwardX11Trusted yes
  Compression yes
```

## What Each Option Does

- **ForwardX11 yes** - Enables X11 forwarding (equivalent to `ssh -X`)
- **ForwardX11Trusted yes** - Enables trusted X11 forwarding (equivalent to `ssh -Y`)
  - Trusted forwarding is more permissive and recommended for local networks
- **Compression yes** - Optional: Compresses data for better performance over network

## How to Update

### On Windows (using your config location)

1. **Find your SSH config file:**
   - Usually at: `C:\Users\nippu\.ssh\config`
   - Or: `%USERPROFILE%\.ssh\config`

2. **Edit the file** and add the two lines:
   ```
   ForwardX11 yes
   ForwardX11Trusted yes
   ```

3. **Save the file**

4. **Connect normally:**
   ```bash
   ssh hraspi
   ```
   X11 forwarding will now be automatic!

## Alternative: Use Command Line Flags

If you don't want to modify the config file, you can still use:
```bash
ssh -Y hraspi
```

But adding it to the config is more convenient - you won't need the `-Y` flag anymore.

## Testing

After updating, connect and test:
```bash
ssh hraspi
cd /home/hpalin/CS437Lab1/software
./test_x11.sh
```

If xeyes works, you're all set!
