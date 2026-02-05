# Hardware-Specific Notes

## Your Hardware Configuration

- **Raspberry Pi 5** (16 GB RAM)
- **PiCar-X Car Chassis Kit**
- **Raspberry Pi Camera Module**
- **64 GB microSD card**

## Important Differences from Documentation

### 1. Raspberry Pi 5 vs Pi 4

**Advantages of Pi 5:**
- More powerful CPU - better for object detection
- More RAM (16 GB) - can handle larger models
- Should achieve better than 1 FPS for object detection
- Better overall performance

**Compatibility:**
- Most software works the same
- Camera interface is compatible
- GPIO pins are compatible
- May need updated drivers/libraries

### 2. PiCar-X vs PiCar-4WD

**Key Differences:**

| Feature | PiCar-4WD | PiCar-X (Your Hardware) |
|---------|-----------|-------------------------|
| Library | `picar-4wd` | `picar-x` (different library) |
| Installation | `sudo python3 setup.py install` | Follow PiCar-X docs |
| Ultrasonic | Mounted on servo | May be fixed position |
| Object Detection | TensorFlow Lite | Consider `vilib` (easier) |
| API | `picar_4wd` module | `picar_x` module (may differ) |

**PiCar-X Specific Setup:**

1. **Installation:**
   - Follow: https://docs.sunfounder.com/projects/picar-x/
   - Different installation process than PiCar-4WD
   - May use different package manager

2. **Ultrasonic Sensor:**
   - On PiCar-X, ultrasonic may be fixed (not on servo)
   - **Solution**: Mount ultrasonic on camera pan servo
   - Use toothpicks/rubber bands to attach
   - Add weight to bottom if needed for balance

3. **Object Detection:**
   - **Recommended**: Use `vilib` instead of TensorFlow Lite
   - Easier to set up on PiCar-X
   - Better integration with PiCar-X ecosystem
   - Still provides object detection capabilities

4. **Turning:**
   - PiCar-X can turn in place
   - Use opposing wheel directions
   - May need different motor control than PiCar-4WD

## Installation Steps for Your Hardware

### On Raspberry Pi 5:

1. **Install PiCar-X Library:**
   ```bash
   # Follow PiCar-X specific instructions
   # Check: https://docs.sunfounder.com/projects/picar-x/
   ```

2. **Install Camera Support:**
   ```bash
   # Raspberry Pi 5 uses libcamera (same as Pi 4)
   sudo apt-get update
   sudo apt-get install -y python3-picamera2
   ```

3. **For Object Detection (Choose One):**

   **Option A: Use vilib (Recommended for PiCar-X)**
   ```bash
   # vilib is easier on PiCar-X
   # Follow vilib installation instructions
   ```

   **Option B: Use TensorFlow Lite (More complex)**
   ```bash
   # Standard TensorFlow Lite setup
   pip3 install tensorflow-lite
   # May need MediaPipe instead of tflite_support
   pip3 install mediapipe
   ```

4. **Test Your Setup:**
   ```bash
   # Test camera
   libcamera-hello
   
   # Test PiCar-X
   # Run example scripts from PiCar-X library
   ```

## Code Compatibility

### Your `hardware_mock.py` Should Still Work

The hardware abstraction layer you have should work with PiCar-X because:
- It abstracts the hardware interface
- On PC: Uses mocks (doesn't matter which car)
- On Pi: Will use actual PiCar-X library once installed
- The API calls (forward, backward, turn, etc.) are conceptually the same

### What You May Need to Adjust

1. **Import statements:**
   ```python
   # Instead of:
   import picar_4wd as fc
   
   # You may need:
   import picar_x as fc
   # Or whatever PiCar-X uses
   ```

2. **Hardware Mock Update:**
   - Update `hardware_mock.py` to import correct library when on Pi
   - Check PiCar-X API documentation for exact function names

3. **Object Detection:**
   - If using vilib, code structure will be different
   - But core concepts (image → preprocessing → detection → action) remain same

## Troubleshooting

### Raspberry Pi 5 Specific

- **Camera not working**: Ensure you're using `libcamera` commands, not old `raspistill`
- **GPIO issues**: Pi 5 GPIO is compatible but may need updated libraries
- **Performance**: Pi 5 should perform better - if slower, check thermal throttling

### PiCar-X Specific

- **Library not found**: Make sure you installed PiCar-X library, not PiCar-4WD
- **Ultrasonic can't scan**: Mount it on camera pan servo
- **Object detection fails**: Try vilib instead of TensorFlow Lite
- **Motors not working**: Check PiCar-X specific motor control API

## Resources

- **PiCar-X Documentation**: https://docs.sunfounder.com/projects/picar-x/
- **Raspberry Pi 5 Docs**: https://www.raspberrypi.com/documentation/
- **vilib (for object detection)**: Check SunFounder PiCar-X resources
- **MediaPipe** (alternative to TensorFlow Lite): https://ai.google.dev/edge/mediapipe/

## Next Steps

1. ✅ Your development setup on laptop is ready (hardware mocks work)
2. ⏭️ When ready, install PiCar-X library on Raspberry Pi 5
3. ⏭️ Test basic movement and sensors
4. ⏭️ Set up object detection (vilib recommended)
5. ⏭️ Deploy your code and test with real hardware

---

**Remember**: The algorithms and logic you develop on your laptop will work the same - only the hardware interface library differs!
