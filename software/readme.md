# PiCar-X Self-Driving Car — Lab 1

**Hardware:**
- Raspberry Pi 5 (16 GB RAM)
- PiCar-X car chassis with servo-mounted ultrasonic sensor
- Raspberry Pi Camera Module (connected via ribbon cable)
- 64 GB microSD card

---

## Project Structure

```
software/
├── advanced_mapping.py    # Step 2.1 — Ultrasonic scan → 100×100 occupancy grid
├── object_detection.py    # Step 2.2 — MediaPipe EfficientDet-Lite2 (80 COCO classes)
├── astar_routing.py       # Step 2.3 — A* pathfinding + PathFollower
├── self_driving.py        # Step 2.4 — Full autonomous controller (integrates all)
├── navigation.py          # Step 1.4 — Reactive obstacle avoidance (Roomba mode)
├── hardware_mock.py       # Hardware abstraction: picar-x on Pi, mocks on PC
├── test_locomotion.py     # Quick motor/servo test
├── calibrate_servo.py     # Interactive servo calibration
├── download_model.py      # Download efficientdet_lite2.tflite
├── models/
│   └── efficientdet_lite2.tflite
├── requirements.txt       # Python dependencies (see setup below)
├── project.md             # Lab spec and rubric
└── SYSTEM_ARCHITECTURE.md # Data-flow and algorithm documentation
```

---

## Setup

### PC Development

```bash
pip install numpy mediapipe opencv-python
```

Run any script — `hardware_mock.py` auto-detects that you're not on a Pi and uses
mock hardware (printed console output instead of real motors/servos).

### Raspberry Pi — Full Setup (one-time)

> **Key constraint:** MediaPipe requires Python 3.11. The Pi system Python is 3.13.
> Always use the `py311` venv.

**1. Create the venv (skip if `~/py311` already exists):**
```bash
python3.11 -m venv ~/py311
```

**2. Install pip packages:**
```bash
~/py311/bin/pip install --upgrade pip
~/py311/bin/pip install -r requirements.txt
```

**3. Install picar-x and robot_hat from local source:**
```bash
~/py311/bin/pip install ~/picar-x
~/py311/bin/pip install ~/robot-hat
```

**4. Install system camera package (required for Picamera2):**
```bash
sudo apt-get install -y python3-libcamera
```
> `picamera2` is a pip package but depends on `libcamera` bindings that only exist
> as a system `.deb`. Installing `python3-libcamera` first makes it work from the venv.

**5. Fix GPIO permissions (run once per session, or make permanent):**
```bash
newgrp gpio
# Permanent fix (requires re-login):
sudo usermod -aG gpio $USER
```

**6. Verify everything works:**
```bash
cd ~/CS437Lab1/software
/home/hpalin/py311/bin/python -c "
from hardware_mock import get_hardware
hw = get_hardware()
print('Hardware:', hw['hardware_type'], '| Mock:', hw['is_mock'])
"
```
Expected output: `Hardware: picar-x | Mock: False`

---

## Running the Scripts

All commands use the `py311` Python explicitly. Never use the bare `python3` or
`python` on the Pi — those point to Python 3.13 which lacks MediaPipe support.

```bash
cd ~/CS437Lab1/software

# Step 1.4 — Reactive obstacle avoidance
/home/hpalin/py311/bin/python navigation.py

# Step 2.1 — Ultrasonic mapping (car will scan and print ASCII map)
/home/hpalin/py311/bin/python advanced_mapping.py

# Step 2.2 — Object detection test (press q to quit viewer)
/home/hpalin/py311/bin/python object_detection.py --viewer
/home/hpalin/py311/bin/python object_detection.py --no-viewer

# Step 2.3 — A* routing standalone test (mock mode safe)
/home/hpalin/py311/bin/python astar_routing.py

# Step 2.4 — Full self-driving (⚠️ CAR WILL MOVE)
/home/hpalin/py311/bin/python self_driving.py --goal 70,65 --yes

# Download model if missing
/home/hpalin/py311/bin/python download_model.py
```

**`self_driving.py` arguments:**
| Flag | Default | Description |
|------|---------|-------------|
| `--goal X,Y` | 70,65 | Grid cell goal (car starts at 50,50) |
| `--clearance N` | 3 | Obstacle inflation radius (cells) |
| `--rescan N` | 5 | Replan every N path steps |
| `--max-time S` | 300 | Timeout in seconds |
| `--yes` | — | Skip "Ready to start?" prompt |

---

## Hardware Notes

### Ultrasonic Sensor
- Mounted on the **camera pan servo** (not fixed) using toothpicks + rubber bands
- Scanning range: −90° to +90° in 5° steps
- Map scale: 2 cm per cell → 100×100 grid = 2 m × 2 m area

### Camera
- Uses `rpicam-vid` workaround (OpenCV cannot directly read Pi 5 camera)
- This is handled automatically in `object_detection.py` — no user action needed
- To verify camera works at system level: `libcamera-hello -t 2000`

### Servo Initialization
- `Picarx()` resets the MCU on construction — all servos snap to default angles
- `hardware_mock.py` / `advanced_mapping.py` implement a slow centering sweep
  after init to prevent the snap from jerking the car

### Turning in Place
- PiCar-X turns by driving wheels in opposing directions
- Configured in `astar_routing.py` → `_turn_to_heading()`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ImportError: No module named mediapipe` | Use py311 venv, not system Python |
| `ImportError: No module named picarx` | `~/py311/bin/pip install ~/picar-x` |
| `GPIO access denied` / `Pin factory error` | `newgrp gpio` then re-run |
| Camera opens but no frames | `sudo apt-get install -y python3-libcamera` |
| `libcamera-hello` fails | Check ribbon cable connection |
| Car snaps on startup | Expected — MCU resets servos; slow sweep follows |
| A* finds very long paths | Accumulated map obstacles; restart clears the map |
| Vision always triggering | Confidence or bbox area filter too low in `self_driving.py` |
| `termios.error` in calibrate_servo | Use `calibrate_servo.py` only from a real TTY |

---

## Architecture Summary

```
Ultrasonic (servo scan)
    └─→ advanced_mapping.py ─→ 100×100 occupancy grid
                                    │
Camera (rpicam-vid)                 ▼
    └─→ object_detection.py ─→ astar_routing.py ─→ PathFollower
         (EfficientDet-Lite2)      (A* + inflate)       │
                                                         ▼
                                                   self_driving.py
                                                   (main loop:
                                                    scan→plan→drive
                                                    +vision override
                                                    +sonar bump guard)
```

See `SYSTEM_ARCHITECTURE.md` for full data-flow and algorithm documentation.
