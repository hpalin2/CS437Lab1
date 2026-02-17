# PiCar System Architecture & Data Flow

## Overview

This document explains how the PiCar self-driving system works: what sensors it uses, how data is processed, and what algorithms are applied at each stage.

---

## 1. Input Sensors

The PiCar uses several sensors to perceive its environment:

### Primary Sensors (Used in Lab)

#### 1. **Ultrasonic Sensor** (HC-SR04)
- **Location**: Mounted on servo motor, can rotate ±90°
- **Function**: Measures distance to obstacles using sound waves
- **How it works**:
  - Sends ultrasonic pulse (40kHz)
  - Measures time for echo to return
  - Calculates distance: `distance = (time × speed_of_sound) / 2`
  - Range: ~2-400cm
- **Data output**: Distance in centimeters
- **Used in**: Part 1 (obstacle avoidance), Part 2 (advanced mapping)

#### 2. **Servo Motor** (for Ultrasonic)
- **Function**: Rotates ultrasonic sensor to scan environment
- **Range**: -90° to +90° (180° total)
- **Control**: Set angle programmatically
- **Used in**: Part 2 (advanced mapping - scanning surroundings)

#### 3. **Raspberry Pi Camera**
- **Function**: Captures images/video for object detection
- **Resolution**: Varies (typically 640x480 or higher)
- **Frame rate**: ~1 FPS on Pi (limited by processing power)
- **Data output**: Image frames (numpy arrays)
- **Used in**: Part 2 (object detection - Step 2.2)

### Secondary Sensors (Available but not required for core lab)

#### 4. **Grayscale Sensors** (3x ADC sensors)
- **Function**: Detect line following (for track_line functionality)
- **Location**: Front of car, left/center/right
- **Used in**: Optional line-following features (not required for main lab)

#### 5. **Speed Sensors** (Photo-interrupters)
- **Function**: Measure wheel rotation speed
- **How it works**: Counts interruptions in light beam as wheel rotates
- **Data output**: Speed in cm/s
- **Used in**: Part 2 (localization - tracking car position)

---

## 2. Data Processing Pipeline

### Part 1: Enhanced Obstacle Avoidance

```
┌─────────────┐
│ Ultrasonic  │ → Distance reading (cm)
│   Sensor    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Median Filter   │ → 5-sample window for noise reduction
│ (5 samples)     │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Emergency Check │ → Raw reading < 5cm? (bypasses filter)
│                 │
└──────┬──────────┘
       │
       ├─ YES → Emergency stop → Avoidance maneuver
       │
       ▼
┌─────────────────┐
│ Threshold Check │ → Filtered distance < 15cm?
│ + Slowdown Zone │ → 15-30cm: Gradual speed reduction
└──────┬──────────┘
       │
       ├─ YES → Stop → Back up → Turn (with direction memory) → Continue
       │
       └─ NO  → Continue forward (variable speed based on distance)
```

**Processing Steps**:
1. **Read sensor**: Get distance from ultrasonic sensor (with validation)
2. **Median filtering**: 5-sample sliding window for noise reduction
3. **Emergency stop**: Raw reading < 5cm bypasses filter for immediate stop
4. **Slowdown zone**: Gradual speed reduction between 15-30cm (30% → 15% power)
5. **Threshold check**: `if filtered_distance < OBSTACLE_THRESHOLD (15cm)`
6. **Direction memory**: Reuses successful turn directions, flips on failure
7. **Turn escalation**: Increases turn duration when repeatedly stuck
8. **Motor control**: Execute movement commands with proper sequencing

**Enhanced Features**:
- **Emergency stop**: Bypasses filter for dangerously close readings (<5cm)
- **Slowdown zone**: Gradual speed reduction (30% → 15%) as approaching obstacles
- **Direction memory**: Remembers and reuses successful turn directions
- **Turn escalation**: Increases turn duration (up to 1.5s) when stuck repeatedly
- **Bad-read failsafe**: Stops if sensor fails 5 consecutive times while moving
- **5-sample median filter**: Better noise rejection than 3-sample

**Algorithm**: Enhanced reactive control with adaptive behavior (no mapping, no planning)

---

### Part 2: Advanced Mapping (Step 2.1)

```
┌─────────────┐
│   Servo     │ → Rotate to angle θ
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Ultrasonic  │ → Distance d at angle θ
│   Sensor    │
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ Coordinate Transform │ → Convert (θ, d) → (x, y)
│  Polar to Cartesian  │   x = d × cos(θ)
│                      │   y = d × sin(θ)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Numpy Array Map     │ → Mark obstacle at (x, y)
│  100×100 grid        │   map[x, y] = 1 (obstacle)
│  1 = obstacle        │   map[x, y] = 0 (free)
│  0 = free space      │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Interpolation       │ → Fill gaps between scan points
│  (Optional)          │   Linear interpolation between angles
└──────────────────────┘
```

**Processing Steps**:
1. **Scan environment**: Rotate servo from -90° to +90°, take distance readings every 15-30°
2. **Coordinate conversion**: Convert polar coordinates (angle, distance) to Cartesian (x, y)
3. **Map building**: Store obstacles in 100×100 numpy array (1cm per cell)
4. **Interpolation**: Fill in gaps between scan points using linear interpolation
5. **Localization**: Track car position using speed sensors (optional)

**Algorithm**: Non-probabilistic mapping (simplified SLAM)

---

### Part 2: Object Detection (Step 2.2)

```
┌─────────────┐
│   Camera    │ → Raw image frame
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  OpenCV         │ → Image preprocessing
│  Preprocessing  │   - Resize to model input size
│                 │   - Normalize pixel values
│                 │   - Convert color space if needed
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ TensorFlow Lite │ → Object detection
│  CNN Model      │   - Pre-trained model (COCO, etc.)
│  (Quantized)    │   - Output: bounding boxes + classes
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Post-processing│ → Filter results
│                 │   - Confidence threshold
│                 │   - Non-maximum suppression
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Decision Logic │ → React to detected objects
│                 │   - Person detected → Stop
│                 │   - Stop sign → Stop
│                 │   - Traffic cone → Avoid
└─────────────────┘
```

**Processing Steps**:
1. **Image capture**: Get frame from camera (~1 FPS on Pi)
2. **Preprocessing**: Resize, normalize for neural network
3. **Inference**: Run TensorFlow Lite model (quantized 8-bit)
4. **Post-processing**: Filter detections by confidence
5. **Action**: React based on detected object type

**Algorithm**: Deep learning object detection (CNN - Convolutional Neural Network)

---

### Part 2: A* Pathfinding (Step 2.3)

```
┌─────────────────┐
│  Advanced Map   │ → 100×100 numpy array
│  (from Step 2.1)│   (0s and 1s)
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Graph Creation │ → Convert map to graph
│                 │   - Each cell = node
│                 │   - Edges = 4 directions (up/down/left/right)
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  A* Algorithm   │ → Find shortest path
│                 │   - Start: current position
│                 │   - Goal: target destination
│                 │   - Heuristic: Euclidean distance
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Path Execution │ → Follow path step by step
│                 │   - Move to next node
│                 │   - Rescan periodically
│                 │   - Replan if obstacles change
└─────────────────┘
```

**Processing Steps**:
1. **Graph representation**: Convert 2D map to graph (nodes = cells, edges = movements)
2. **A* search**: Find optimal path using:
   - `f(n) = g(n) + h(n)`
   - `g(n)` = cost from start to node n
   - `h(n)` = heuristic (Euclidean distance to goal)
3. **Path following**: Execute path step by step
4. **Replanning**: Periodically rescan and recompute path

**Algorithm**: A* (A-star) pathfinding algorithm

---

## 3. Algorithms Used and Where

### Part 1 Algorithms

#### **Enhanced Reactive Control** (Step 1.4)
- **Location**: `navigation.py`
- **Algorithm**: Threshold-based reactive control with adaptive features
- **Complexity**: O(1) per iteration
- **Input**: Single distance reading (with median filtering)
- **Output**: Motor commands (forward/backward/turn/stop) with variable speed

**Enhanced Features**:
- Emergency stop bypass (raw < 5cm)
- Slowdown zone (gradual speed reduction 15-30cm)
- Direction memory (reuses successful turns)
- Turn escalation (increases turn duration when stuck)
- 5-sample median filter
- Bad-read failsafe

**Pseudocode**:
```
while True:
    raw_distance = ultrasonic.read()
    filtered_distance = median_filter(raw_distance)  # 5-sample window
    
    # Emergency stop (bypasses filter)
    if raw_distance < 5cm:
        stop()
        backup()
        direction = choose_turn_with_memory()
        turn(direction, escalated_duration)
        continue
    
    # Slowdown zone
    if 15cm < filtered_distance < 30cm:
        speed = interpolate_speed(filtered_distance)  # 30% → 15%
    
    # Obstacle detection
    if filtered_distance < 15cm:
        stop()
        backup()
        direction = choose_turn_with_memory()  # Reuses successful directions
        turn(direction, escalated_duration)
    else:
        forward(speed)  # Variable speed based on distance
```

---

### Part 2 Algorithms

#### **Non-Probabilistic Mapping** (Step 2.1)
- **Location**: `advanced_mapping.py`
- **Algorithm**: Polar-to-Cartesian conversion + grid mapping
- **Complexity**: O(n) where n = number of scan angles
- **Input**: Array of (angle, distance) pairs
- **Output**: 100×100 numpy array (occupancy grid)

**Key Operations**:
1. **Coordinate transform**: `(θ, d) → (x, y)`
   - `x = d × cos(θ)`
   - `y = d × sin(θ)`
2. **Grid mapping**: Mark obstacles in discrete grid
3. **Interpolation**: Fill gaps between scan points

#### **Object Detection** (Step 2.2)
- **Location**: `object_detection.py`
- **Algorithm**: Deep learning CNN (Convolutional Neural Network)
- **Model**: Pre-trained TensorFlow Lite model (e.g., COCO)
- **Complexity**: O(W×H×C) where W×H = image size, C = channels
- **Input**: Image frame (numpy array)
- **Output**: List of detections (bounding boxes + class labels)

**Pipeline**:
1. Image preprocessing (OpenCV)
2. Neural network inference (TensorFlow Lite)
3. Post-processing (filtering, NMS)

#### **A* Pathfinding** (Step 2.3)
- **Location**: `astar_routing.py`
- **Algorithm**: A* (A-star) graph search
- **Complexity**: O(b^d) worst case, but much better with good heuristic
- **Input**: Start position, goal position, occupancy map
- **Output**: List of waypoints (path)

**A* Algorithm**:
```
f(n) = g(n) + h(n)
where:
  g(n) = actual cost from start to node n
  h(n) = heuristic estimate from n to goal (Euclidean distance)
```

**Data Structures**:
- Open set: Priority queue (min-heap) of nodes to explore
- Closed set: Set of explored nodes
- Came from: Dictionary tracking path

A\* search on the 100×100 occupancy grid with Euclidean distance heuristic
4-connected grid movement (up/down/left/right)
Priority queue (min-heap) with tie-breaking counter
Key features:
inflate_obstacles() — dilates obstacles by a configurable clearance radius so the car doesn't clip corners
astar() — returns the full cell-by-cell path; allow_unknown flag lets it traverse unexplored cells
simplify_path() — removes colinear intermediate waypoints so the car only turns when direction changes
PathFollower — drives the car along waypoints, integrating with:
AdvancedMapper for periodic rescanning
ObjectDetector + VisionOverride for stopping on person/stop sign detection
visualize_path_ascii() — compact ASCII view of the map with path overlay
Standalone tests — synthetic map test + integration test with mapper, both pass in mock mode

---

## 4. System Integration Flow

### Full Self-Driving System (Step 2.4)

```
┌─────────────────────────────────────────────────┐
│              Main Control Loop                    │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│  Mapping  │ │  Object   │ │  Speed    │
│  (Step 2.1)│ │ Detection │ │  Sensors  │
│           │ │ (Step 2.2)│ │           │
└─────┬─────┘ └─────┬─────┘ └─────┬─────┘
      │             │             │
      └─────────────┼─────────────┘
                    │
                    ▼
            ┌───────────────┐
            │  Decision     │
            │  Fusion       │
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  A* Routing   │
            │  (Step 2.3)   │
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  Motor        │
            │  Control      │
            └───────────────┘
```

**Integration Logic**:
1. **Mapping**: Continuously scan and update environment map
2. **Object Detection**: Check for people, stop signs, etc.
3. **Decision Fusion**: Combine mapping + object detection
   - If person detected → Stop (override routing)
   - If stop sign detected → Stop (override routing)
   - Otherwise → Follow A* path
4. **Path Planning**: Use A* to find route to goal
5. **Path Execution**: Move car along planned path
6. **Replanning**: Periodically rescan and recompute path

---

## 5. Data Structures

### Key Data Structures Used

1. **Numpy Array (Map)**: `np.array(shape=(100, 100), dtype=int)`
   - 0 = free space
   - 1 = obstacle

2. **Graph**: Implicit (2D grid)
   - Nodes: (x, y) coordinates
   - Edges: 4-directional movement

3. **Priority Queue**: For A* open set
   - Stores: `(f_score, (x, y))`
   - Ordered by: f_score (lowest first)

4. **Dictionary**: For A* path tracking
   - Key: node (x, y)
   - Value: parent node

---

## 6. Performance Considerations

### Computational Constraints (Raspberry Pi)

- **CPU**: Limited processing power
- **Memory**: Limited RAM
- **Frame Rate**: ~1 FPS for object detection (not 25 FPS)
- **Optimization**: Use quantized models (8-bit integers)

### Optimization Strategies

1. **Object Detection**:
   - Use TensorFlow Lite (not full TensorFlow)
   - Quantized models (8-bit)
   - Lower resolution input
   - Skip frames if needed

2. **Mapping**:
   - Reduce scan resolution (fewer angles)
   - Smaller map size if possible
   - Cache previous scans

3. **Pathfinding**:
   - Limit A* search depth
   - Use simpler heuristic
   - Replan less frequently

---

## Summary

**Sensors** → **Data Processing** → **Algorithms** → **Actions**

1. **Ultrasonic** → Distance readings → Threshold check / Mapping → Motor control
2. **Camera** → Image frames → CNN inference → Object detection → Decision logic
3. **Speed sensors** → Velocity → Position tracking → Localization
4. **Servo** → Angle control → Scanning → Mapping

**Algorithms**:
- Part 1: Enhanced reactive control (with emergency stop, slowdown zone, direction memory, turn escalation)
- Part 2: Mapping (coordinate transform), Object detection (CNN), Pathfinding (A*)

**Integration** (`self_driving.py`): Combine all sensors and algorithms for full self-driving capability.
