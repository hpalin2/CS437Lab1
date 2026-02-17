CS437: Internet of Things
Lab1 Part1

Name: Nicky Chen, Hugh Palin, Siddarth Natarajan, Nippun Sabharwal	
NetIDs (include NetID of all group members):
Nickywc2, hpalin2, sn28, nippuns2
Late days used:
Video Link:
lab 1 demo
Link text(in-case hyper-link fails): https://drive.google.com/file/d/10EjC2aaFvNvbkd1Kf5Bya2AZ455-GV3m/view?usp=sharing	

Note: In the rubric for the navigation this is mentioned for a “6” score.
The car is doing some form of navigation but incomplete, e.g., it crashes into objects or scrapes them, doesn't stop quickly enough

During the navigation demo, the vehicle occasionally bumps into objects or becomes stuck. This behavior is primarily due to the limited field of view of the fixed ultrasonic sensor. Because the sensor is forward-facing and not mounted on a servo, it only detects obstacles that fall within a narrow detection cone. Objects located above the sensor’s height, very close to the sides of the vehicle, or outside the central detection region may not be detected, creating blind spots that can lead to contact or immobilization.

One potential improvement would be to mount the ultrasonic sensor on a servo and perform a scanning sweep to increase the effective field of view and provide more robust obstacle detection.

To demonstrate that the navigation logic functions correctly when valid sensor data is available, I added the segment where I walked directly in front of the vehicle. This better demonstrates how the vehicle successfully detects and attempts to navigate around objects within its field of view. This shows that the navigation behavior operates as intended within the sensing constraints of the current hardware configuration.







PCB:
This board is a two-layer PCB created specifically as a GPIO supplement to the Raspberry Pi HAT (Hardware Attached on Top) standard to interface with the Picar-4WD self-driving vehicle platform. The board has an approximate dimension of 65mm × 56mm, has a standard Raspberry Pi HAT configuration, and has holes at all corners for mounting in accordance with the Raspberry Pi mounting pattern. Design of the Picar-4WD GPIO Board was completed using the KiCAD design program.
The primary interface from the Raspberry Pi to the Picar-4WD GPIO board is via a 40-pin GPIO header (J1) which provides access to all I2C communication lines (SDA/SCL), power (+3V3 & +5V), ground and all other GPIO signals from the Raspberry Pi. There is also a written ID contained in a CAT24C256 256Kbit I2C EEPROM (U1) connected to the ID_SDA and ID_SCL (physical pins 27 and 28) for the Picar-4WD GPIO board to allow for proper HAT identification along with a set of 3.9kΩ resistors (R1, R2) for use as pull-ups, a 100nF decoupling capacitor (C1), and a soldering bridge (JP1) to control write protection of the ID information in the CAT24C256 EEPROM.
Motor control is accomplished by the PCA9685BS 16-channel 12-bit I2C PWM driver (U2) which operates at an I²C address of 0x40. The PCA9685BS communicates with the Raspberry Pi via GPIO2/SDA1 and GPIO3/SCL1. The PWM output (LED0 - LED7) signals from the PCA9685BS drive the DC motors (M1 - M4) through a 2-pin connection for each DC motor utility. Each motor will utilize a pair of PWM outputs for the control of motor speed and the control of motor direction.
The board has been designed to feature a 4-pin connector for connecting to an I2C gray scale sensor module that runs off of the same I2C bus as the PCA9685 and is powered by VCC, GND, SDA and SCL. Additionally, there are two 3-pin connectors for photo interrupter speed sensor devices that measure wheel speed; Speed_Sensor1 connects to GPIO4 (physical pin 7) for the left-rear wheel, and Speed_Sensor2 connects to GPIO25 (physical pin 22) for the right-rear wheel.

Power is supplied via a 2-pin battery holder connector that can accept an 18650 battery pack. The (+5V) rail of the battery supplies power to the Raspberry Pi via GPIO pins two and four, as well as to the PCA9684 motor driver. The (+3V3) regulated voltage rail from the Raspberry Pi supplies power to the gray scale module, speed sensors and EEPROM identification circuit.

The 2-layer stackup contains the front Copper (F.Cu) and back Copper (B.Cu) layers, both of which have been used for routing signals and providing ground return paths. The signal traces route between the various components and the GPIO header, with the I2C bus shared between the PCA9685 motor driver and gray scale sensor module.





Design Consideration:

Chassis Assembly:





Naive Mapping:

**Hardware Abstraction Layer (`hardware_mock.py`):**
A hardware abstraction layer provides a unified API for PiCar-X hardware. The module automatically detects the platform (via `/proc/cpuinfo` and `RPi.GPIO` import checks) and creates wrapper functions that normalize the PiCar-X API. Key wrappers include: (1) **Motor control** - `forward()`, `backward()`, `stop()` map directly to `px.forward()`, `px.backward()`, `px.stop()`, (2) **Turning abstraction** - `turn_left()` and `turn_right()` convert to steering servo control (`px.set_dir_servo_angle(-30)` and `px.set_dir_servo_angle(30)`) combined with forward movement, (3) **Servo wrapper** - provides `set_angle()` and `get_angle()` methods that map to camera pan servo (`px.set_cam_pan_angle()`) for ultrasonic scanning, (4) **Ultrasonic wrapper** - provides both `read()` and `get_distance()` methods that map to `px.ultrasonic.read()`. The abstraction layer returns a unified dictionary interface ensuring identical code works on both PC (with realistic mocks including sensor noise simulation) and Raspberry Pi (with real hardware).

**Obstacle Avoidance (`obstacle_avoidance.py`):**
Implemented Roomba-like reactive obstacle avoidance behavior (Part 1, Step 1.4). The system continuously monitors the ultrasonic sensor for obstacles within a 20cm threshold. When an obstacle is detected, the car executes a sequence: (1) stop immediately, (2) back up for 1 second, (3) randomly choose left or right direction, (4) turn in that direction for 0.5 seconds, and (5) continue forward. The implementation includes distance filtering to handle sensor noise, stuck detection to prevent infinite loops, and configurable thresholds for different environments. The code uses the hardware abstraction layer, making it work identically across different hardware platforms.

**Technical Implementation Details:**

The obstacle avoidance system uses a three-state finite state machine (`'stopped'`, `'forward'`, `'avoiding'`) to prevent race conditions and ensure proper motor control sequencing. The main control loop runs at 10 Hz (CHECK_INTERVAL = 0.1 seconds), providing real-time responsiveness while maintaining computational efficiency.

**Sensor Processing Pipeline:**
Readings are validated (2-400cm range) and invalid values are skipped. Valid readings are stored in a sliding window buffer (`deque` with maxlen=3) and filtered using median filtering (selecting middle value) rather than averaging for better noise spike rejection. Total filtering delay is 0.3 seconds (3 samples × 0.1s interval).

**Stuck Detection Algorithm:**
When moving forward, the system tracks if distance changes by more than 3cm within 2.0 seconds. If distance remains constant (±3cm) for more than 2 seconds, the car is likely stuck, triggering a recovery maneuver identical to obstacle avoidance.

**Obstacle Avoidance Sequence:**
When obstacle detected (< 20cm) or stuck condition triggered: (a) transition to `'avoiding'` state, (b) stop and wait 0.3s, (c) back up at 30% power for 1.0s, (d) randomly select left/right direction, (e) turn at 30% power for 0.5s, (f) clear buffers and reset state, (g) return to `'stopped'` state. The 0.3s delays between commands ensure motors have time to respond.

**State Management:**
The state machine prevents redundant commands and ensures proper sequencing. Error handling includes graceful shutdown and always stops motors in the `finally` block for safety.





Naive Self-driving:

The naive self-driving implementation combines the hardware abstraction layer with the obstacle avoidance algorithm to create a complete autonomous navigation system. The car continuously moves forward while monitoring for obstacles, automatically navigating around them using the reactive control strategy described above. The system operates in a loop: sense → decide → act, where sensing uses the ultrasonic sensor, decision-making uses simple threshold-based logic, and action involves motor control commands. This reactive approach requires no mapping or path planning, making it simple and robust for basic obstacle avoidance scenarios. The implementation successfully demonstrates autonomous navigation within the constraints of the forward-facing ultrasonic sensor's limited field of view.

**Control Loop Architecture:**
The main loop runs synchronously at 10 Hz, executing sensor reading, validation/filtering, stuck detection, obstacle threshold comparison, state machine transitions, and motor commands. Includes graceful shutdown handling ensuring motors always stop safely.

**Sensor Integration:**
The interface abstracts API differences between PiCar-X and PiCar-4WD with automatic fallback. Readings are validated (2-400cm range) and filtered using median filtering (3-sample window) for noise reduction. Sensor failures are handled gracefully without crashing.

**Decision Logic:**
Uses threshold-based reactive control: `if (distance < 20cm) OR (stuck_detected)`. Random direction selection (50/50) prevents getting stuck in symmetric configurations. State machine prevents concurrent avoidance maneuvers.

**Motor Control Synchronization:**
Commands are sequenced with 0.3s delays between stop/start operations to account for motor inertia. Power levels set to 30% for smooth operation and battery conservation.

**Performance Characteristics:**
System achieves < 100ms per iteration (10 Hz). Median filter latency is 0.3s. Stuck detection timeout (2.0s) balances responsiveness with false positive prevention. Successfully demonstrates autonomous navigation within the forward-facing ultrasonic sensor's limited field of view (~15-30°), though blind spots can cause occasional collisions as noted in the video demo.





Name
Contribution
Nicky Chen
Assembled picar, developed the navigation script, recorded demo
Hugh Palin
Worked on PCB and recorded code demo video
Nippun Sabharwal
hardware abstraction layer, obstacle avoidance, advanced 2D mapping (3-state occupancy grid)







