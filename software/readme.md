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

## Small-Car Room Tuning (Design Configuration)

This project is tuned for a small PiCar-X driving on indoor floors (room-scale
obstacles like boxes, shoes, bottles, food containers) where distances are
typically short (about 10-80 cm). The defaults were adjusted to prioritize
robust local navigation over perfect object labels.

### Vision Policy (Proximity-First, Label-Agnostic)
- In `self_driving.py`, navigation does **not** depend on correct class labels.
- A detection becomes actionable mainly from geometry + confidence:
  - confidence threshold (`VISION_MIN_CONFIDENCE`)
  - bbox area threshold (`VISION_MIN_BBOX_AREA`, ratio threshold)
  - bbox center near image center (`VISION_CENTER_X_TOL_RATIO`)
  - bbox lower in frame (`VISION_MIN_BBOX_BOTTOM_RATIO`)
- This reduces false stops from side/background detections and focuses on
  "is something close in front of the car?".

### Ultrasonic Policy for HC-SR04
- In `advanced_mapping.py`, HC-SR04 value `-2` is treated as a timeout/open
  ray (likely empty space in this setup), not an obstacle hit.
- Aggressive self-detection filtering is intentionally avoided; only impossible
  near-field echoes are discarded.
- Noisy angle reads with large spread are skipped to reduce map corruption.

### Mapping/Planning Robustness Defaults
- Full scans can rebuild the local map each cycle (`MAP_REBUILD_EACH_FULL_SCAN`)
  so stale obstacles do not accumulate and seal valid corridors.
- If A* fails with the current clearance, planner retries once with relaxed
  inflation (`clearance - 1`) before giving up.
- Pose/heading are kept in sync after reactive dodge turns to improve replan
  consistency.

### Practical Guidance for Demo Runs
- Keep obstacles at least one car-width apart where possible.
- Avoid highly reflective surfaces close to the ultrasonic sensor.
- If route is still too conservative in a tight layout, run:
  - `--clearance 1`
  - `--rescan 3`

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

---

## Next Steps — Accuracy & Resilience Improvements

The current system works end-to-end but has several areas where accuracy and
resilience can be significantly improved. These are ordered by impact.

### 1. 8-Connected A\* Grid (Quick Win)

**Problem:** The A\* planner only allows 4-directional movement (up/down/left/right).
Diagonal goals produce staircase paths that force the car into many unnecessary
90° micro-turns, each of which accumulates heading drift on real hardware.

**Fix:** Add diagonal neighbours to A\* with cost √2. This produces much smoother
real-world paths with far fewer turns.

```python
# astar_routing.py — astar() function
# Replace:
neighbours = [(0, 1), (0, -1), (1, 0), (-1, 0)]
tentative_g = g_score[current] + 1.0

# With:
neighbours = [
    (0, 1), (0, -1), (1, 0), (-1, 0),       # cardinal
    (1, 1), (1, -1), (-1, 1), (-1, -1),      # diagonal
]
cost = 1.414 if (dx != 0 and dy != 0) else 1.0
tentative_g = g_score[current] + cost
```

**Effort:** ~5 lines changed. **Impact:** Halves unnecessary turns.

---

### 2. Log-Odds Probabilistic Occupancy Grid

**Problem:** The map uses binary states (`-1`/`0`/`1`). A single noisy ultrasonic
reading places a phantom wall; a single missed reading erases a real one. The full
map wipe every scan cycle (`MAP_REBUILD_EACH_FULL_SCAN`) throws away all spatial
memory each time the car rescans.

**Fix:** Replace the `np.int8` grid with a `float32` log-odds grid. Each scan ray
*increments* (hit) or *decrements* (miss) a cell's belief. A cell only becomes
"occupied" after multiple consistent observations, naturally filtering noise.

```python
# advanced_mapping.py
LOG_ODDS_PRIOR   = 0.0    # 50% prior (no information)
LOG_ODDS_OCC     = 0.85   # increment per hit observation
LOG_ODDS_FREE    = -0.40  # decrement per free-ray observation
LOG_ODDS_CLAMP   = 3.5    # saturation limit (prevents permanent walls)

# On each scan ray:
#   cells along the ray  → log_odds[y, x] += LOG_ODDS_FREE
#   cell at the hit point → log_odds[y, x] += LOG_ODDS_OCC
# A* passability threshold: log_odds > 1.0 → treat as OCCUPIED
```

**Also:** Stop wiping the full map each cycle. Instead, only decay cells *within
the current scan arc*. This preserves knowledge about areas behind the car.

**Effort:** Medium. **Impact:** Eliminates most phantom-obstacle problems; gives
the car persistent spatial memory.

---

### 3. Speed Sensor Integration (Closed-Loop Driving)

**Problem:** All movement is open-loop. The car drives at a fixed power for a fixed
duration and *assumes* it moved exactly one cell. On carpet vs. tile vs. slight
inclines, actual displacement varies 30–50%, causing position drift that compounds
over time and eventually makes A\* plan against a map that no longer matches reality.

**Fix:** The PiCar has photo-interrupter speed sensors (already wired!) but they are
never read. Use them to measure actual distance traveled and stop when the desired
distance is reached, not after a fixed time.

```python
# astar_routing.py — PathFollower._drive_forward_one_cell()
# Instead of: drive for STEP_DURATION seconds
# Do:         drive until speed_sensor reports CELL_SIZE_CM of travel
# Also use differential wheel speed to detect and correct heading drift
```

**Effort:** Medium (need to interface with speed sensor API).
**Impact:** Largest single accuracy improvement — fixes the root cause of most
navigation failures (localization drift).

---

### 4. Smart Dodge with Sonar Scan

**Problem:** `_reactive_dodge()` alternates left/right blindly when the car bumps
an obstacle. Half the time it turns *toward* the wall.

**Fix:** After backing up, do a quick 3-point sonar check (−45°, 0°, +45°) and
turn toward the direction with the most clearance.

```python
# astar_routing.py — PathFollower._reactive_dodge()
self.hw['backward'](DODGE_BACKUP_SPEED)
time.sleep(DODGE_BACKUP_TIME)
self.hw['stop']()

# Quick look left and right
self.hw['servo'].set_angle(-45); time.sleep(0.15)
left_dist = self._read_sonar() or 0
self.hw['servo'].set_angle(45);  time.sleep(0.15)
right_dist = self._read_sonar() or 0
self.hw['servo'].set_angle(0)

direction = 'left' if left_dist > right_dist else 'right'
```

**Effort:** Small (~15 lines). **Impact:** Eliminates blind-dodge failures.

---

### 5. Sonar-Vision Fusion

**Problem:** Vision operates independently of sonar. A person detected at 5 meters
triggers the same hard stop as one at 30 cm. The bbox-area heuristic is a rough
proxy for distance with no cross-check.

**Fix:** When a detection passes the bbox filters, read the ultrasonic at 0° to get
actual forward distance. Cross-check:
- Sonar > 80 cm → downgrade `proximity_hard` to `proximity`
- Sonar > 150 cm → skip the stop entirely (object is far away)

```python
# self_driving.py — _vision_check()
sonar_d = self.follower._read_sonar()
if sonar_d and sonar_d > 80:
    hard = []                    # no hard stops for distant objects
    if sonar_d > 150:
        actionable = []          # don't stop at all
```

**Effort:** Small. **Impact:** Stops false vision-triggered halts for distant objects.

---

### 6. Graduated Cost Field Near Obstacles

**Problem:** Obstacle inflation is binary — a cell is passable or blocked. A\* may
thread the needle through a narrow gap that the real car can't fit through cleanly.

**Fix:** Add a traversal-cost gradient around obstacles. Cells closer to walls have
higher traversal cost, making A\* naturally prefer wider corridors and centered paths.

```python
# astar_routing.py — after inflate_obstacles()
# Build a cost_map where:
#   on obstacle          → infinity (impassable)
#   within clearance     → infinity (impassable, same as now)
#   clearance+1 to +3   → cost 3.0 → 1.5 (graduated penalty)
#   far from obstacles   → cost 1.0 (normal)
```

**Effort:** Medium. **Impact:** Safer corridor navigation with more margin.

---

### 7. Partial Map Update Instead of Full Wipe

**Problem:** `MAP_REBUILD_EACH_FULL_SCAN = True` clears the entire map before each
scan. The car forgets everything behind it, including obstacles it just navigated
around.

**Fix:** Only clear cells within the current scan's field of view (the swept arc
from `angle_min` to `angle_max`), then update those cells. Cells outside the
scanned sector retain their accumulated evidence.

**Effort:** Small. **Impact:** Preserves spatial memory, reduces redundant scans.

---

### 8. Progress Watchdog + Multi-Strategy Stuck Recovery

**Problem:** If the car gets stuck navigating in circles, the only recovery is
`MAX_REPLAN_FAILURES = 5` then abort. There's no detection of "making no progress."

**Fix:** Track `distance_to_goal` over time. If it hasn't decreased in 15 seconds
despite active navigation, trigger escalating recovery:

1. Full 360° scan and replan
2. Try intermediate sub-goals (route to a free cell halfway to the goal first)
3. Random exploration (drive to a random nearby free cell, rescan, retry)
4. Backtrack to last known-good position where A\* previously succeeded

**Effort:** Medium. **Impact:** Resilience to getting stuck or circling.

---

### 9. Simple Object Tracker (Centroid-Based)

**Problem:** Each camera frame is processed independently. A one-frame false positive
(e.g., a chair leg briefly classified as a person) triggers a full stop + replan.
No tracking of objects across frames.

**Fix:** Implement a simple centroid tracker across 3–5 consecutive frames:
- **False positive rejection:** A detection that doesn't appear in the next 2 frames
  is filtered out.
- **Approach detection:** If a person's bbox is growing across frames, they are
  approaching → stop sooner. If shrinking, they are leaving → resume faster.
- **Direction awareness:** If a person is consistently on the edge of the frame and
  moving away from center, they are leaving the car's path — no need to stop.

**Effort:** Medium. **Impact:** Fewer false-positive vision stops.

---

### 10. Adaptive Rescan Interval

**Problem:** `RESCAN_EVERY_N_STEPS = 5` is fixed. In open space, this wastes time
stopping to scan. Near dense obstacles, it may not be frequent enough.

**Fix:** Make the interval adaptive based on the last scan's results:

```python
# self_driving.py
nearby_obstacles = count_obstacles_within(inflated, car_pos, radius=10)
rescan_interval = 2 if nearby_obstacles > 3 else 8
```

**Effort:** Small. **Impact:** Better trade-off between scan frequency and driving
progress.

---

### Summary Table

| # | Change | Impact | Effort |
|---|--------|--------|--------|
| 1 | 8-connected A\* grid | High — halves unnecessary turns | Tiny (~5 lines) |
| 2 | Log-odds occupancy grid | High — eliminates phantom obstacles | Medium |
| 3 | Speed sensor integration | Highest — fixes position drift | Medium |
| 4 | Smart dodge with sonar scan | High — stops blind recovery failures | Small |
| 5 | Sonar-vision fusion | High — stops false vision-stops | Small |
| 6 | Cost gradient near obstacles | Medium — safer corridor navigation | Medium |
| 7 | Partial map update (no wipe) | Medium — preserves spatial memory | Small |
| 8 | Progress watchdog + stuck recovery | Medium — resilience to circling | Medium |
| 9 | Centroid object tracker | Medium — fewer false positives | Medium |
| 10 | Adaptive rescan interval | Low–Med — better scan efficiency | Small |
