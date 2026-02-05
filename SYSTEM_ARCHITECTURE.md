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
- **Used in**: Part 2 (object detection - Step 7)

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

### Part 1: Basic Obstacle Avoidance

```
┌─────────────┐
│ Ultrasonic  │ → Distance reading (cm)
│   Sensor    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Simple Threshold│ → Compare: distance < 20cm?
│   Comparison    │
└──────┬──────────┘
       │
       ├─ YES → Stop → Back up → Turn → Continue
       │
       └─ NO  → Continue forward
```

**Processing Steps**:
1. **Read sensor**: Get distance from ultrasonic sensor
2. **Threshold check**: `if distance < OBSTACLE_THRESHOLD`
3. **Action decision**: Simple if/else logic
4. **Motor control**: Execute movement commands

**Algorithm**: Simple reactive control (no mapping, no planning)

---

### Part 2: Advanced Mapping (Step 6)

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

### Part 2: Object Detection (Step 7)

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

### Part 2: A* Pathfinding (Step 8)

```
┌─────────────────┐
│  Advanced Map   │ → 100×100 numpy array
│  (from Step 6)  │   (0s and 1s)
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

#### **Simple Reactive Control** (Step 4)
- **Location**: `obstacle_avoidance.py`
- **Algorithm**: Threshold-based reactive control
- **Complexity**: O(1) per iteration
- **Input**: Single distance reading
- **Output**: Motor commands (forward/backward/turn/stop)

**Pseudocode**:
```
while True:
    distance = ultrasonic.read()
    if distance < threshold:
        stop()
        backup()
        turn(random_direction)
    else:
        forward()
```

---

### Part 2 Algorithms

#### **Non-Probabilistic Mapping** (Step 6)
- **Location**: `advanced_mapping.py` (to be created)
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

#### **Object Detection** (Step 7)
- **Location**: `object_detection.py` (to be created)
- **Algorithm**: Deep learning CNN (Convolutional Neural Network)
- **Model**: Pre-trained TensorFlow Lite model (e.g., COCO)
- **Complexity**: O(W×H×C) where W×H = image size, C = channels
- **Input**: Image frame (numpy array)
- **Output**: List of detections (bounding boxes + class labels)

**Pipeline**:
1. Image preprocessing (OpenCV)
2. Neural network inference (TensorFlow Lite)
3. Post-processing (filtering, NMS)

#### **A* Pathfinding** (Step 8)
- **Location**: `astar_routing.py` (to be created)
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

---

## 4. System Integration Flow

### Full Self-Driving System (Step 9)

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
│  (Step 6) │ │ Detection │ │  Sensors  │
│           │ │ (Step 7)  │ │           │
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
            │  (Step 8)     │
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
- Part 1: Simple reactive control
- Part 2: Mapping (coordinate transform), Object detection (CNN), Pathfinding (A*)

**Integration**: Combine all sensors and algorithms for full self-driving capability.
