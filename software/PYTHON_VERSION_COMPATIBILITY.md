# Python Version Compatibility Summary

## Current Setup

**Virtual Environment:** `py311` (Python 3.11.14)
- ✅ MediaPipe 0.10.14
- ✅ OpenCV 4.13.0.92
- ✅ NumPy, and other dependencies

**System Python:** Python 3.13.5
- ✅ picar-x installed system-wide
- ✅ robot_hat, vilib dependencies

## Python Version Support

### MediaPipe
- ✅ **Python 3.11** - Fully supported
- ❌ **Python 3.13** - NOT supported (this is why we use py311)

### OpenCV
- ✅ **Python 3.11** - Fully supported
- ✅ **Python 3.13** - Supported

### picar-x
- ✅ **Python 3.13** - Currently installed system-wide
- ⚠️  **Python 3.11** - Not installed in venv (version mismatch issue)

## The Problem

1. **MediaPipe requires Python 3.11** (doesn't work with 3.13)
2. **picar-x is installed for Python 3.13** (system-wide)
3. **We're using py311 venv** for MediaPipe/OpenCV
4. **Result:** picar-x can't be imported in py311 venv

## Solutions

### Option 1: Install picar-x in py311 venv (Recommended)

According to the picar-x README, dependencies are:
- robot_hat
- vilib  
- sunfounder_controller

**Steps:**
```bash
source /home/hpalin/py311/bin/activate
cd ~/picar-x
pip install . --break --no-deps --no-build-isolation
```

**Pros:** Everything in one venv
**Cons:** May need to install robot_hat, vilib in venv too

### Option 2: Use system-site-packages (Current workaround)

The `hardware_mock.py` already tries to access system packages:
```python
sys.path.insert(0, '/usr/local/lib/python3.13/dist-packages')
```

**Pros:** Uses existing system installation
**Cons:** Version mismatch, dependency issues (pyaudio)

### Option 3: Create separate venv for picar-x (Not recommended)

Use Python 3.13 venv for picar-x, but then MediaPipe won't work.

## Recommendation

**Stick with py311 venv** for MediaPipe/OpenCV (required).

For picar-x, we have two paths:

1. **Best:** Install picar-x and dependencies in py311 venv
2. **Current:** Use system packages via sys.path workaround (has pyaudio issues)

## Current Status

✅ **Working:**
- MediaPipe object detection (Python 3.11)
- OpenCV (Python 3.11)
- Camera access via rpicam workaround
- Advanced mapping (using mocks)

⚠️  **Needs work:**
- picar-x hardware access (pyaudio dependency issue)
- Real hardware mapping (currently using mocks)

## Next Steps

1. Try installing picar-x in py311 venv:
   ```bash
   source /home/hpalin/py311/bin/activate
   # Install dependencies first
   pip install gpiozero smbus2 pyaudio
   cd ~/picar-x
   pip install . --break --no-deps --no-build-isolation
   ```

2. Or fix pyaudio for system Python 3.13 installation

3. Or continue using mocks for development (works fine for testing)
