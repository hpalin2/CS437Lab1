# PiCar Development Setup Instructions

## For PC Development (Your Current Setup)

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Test Locomotion Script

Run the test script to verify everything works (in mock mode):

```bash
python test_locomotion.py
```

This will run in mock mode on your PC, simulating hardware calls.

### 3. Development Workflow

1. **Develop on PC**: Write and test your code using the mock hardware
2. **Commit to Git**: Push your changes to your repository
3. **Deploy to Pi**: Pull changes on Raspberry Pi and test with real hardware

## For Raspberry Pi Setup

### 1. Install picar-4wd Library

On your Raspberry Pi, you need to install the actual picar-4wd library:

```bash
# Clone the picar-4wd repository
git clone https://github.com/sunfounder/picar-4wd.git
cd picar-4wd

# Install the library
sudo python3 setup.py install
```

**Alternative**: If the above repository doesn't exist, check the SunFounder documentation:
- Visit: https://docs.sunfounder.com/projects/picar-4wd/
- Follow their installation instructions

### 2. Verify Installation

On the Pi, test that picar-4wd is installed:

```bash
python3 -c "from picar_4wd import forward; print('picar-4wd installed successfully')"
```

### 3. Pull Your Code

```bash
cd /path/to/your/project
git pull origin main  # or your branch name
```

### 4. Run Tests on Pi

```bash
python3 test_locomotion.py
```

**WARNING**: On the Pi, this will actually move the car! Make sure:
- The car is on a safe surface
- There's enough space around it
- You're ready to stop it if needed (Ctrl+C)

## Project Structure

```
.
├── readme.md              # Lab instructions
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── hardware_mock.py      # Mock hardware for PC development
├── test_locomotion.py    # Locomotion test script
├── setup_instructions.md # This file
└── [your code files]     # Your implementation files
```

## Next Steps

1. **Explore picar-4wd API**: Look at the example scripts mentioned in the readme:
   - `keyboard_control.py` - Manual control
   - `ultrasonic.py` - Distance sensing
   - `servo.py` - Servo control

2. **Implement Part 1 Requirements**:
   - Environment scanning (mapping)
   - Basic obstacle avoidance
   - Navigation around obstacles

3. **Test Incrementally**: 
   - Test each component separately
   - Then integrate them together

## Troubleshooting

### On PC:
- If you get import errors, make sure you're using the mock hardware
- The script should automatically detect you're on PC and use mocks

### On Raspberry Pi:
- If `picar_4wd` import fails, install the library (see above)
- Check that all hardware is properly connected
- Verify GPIO permissions: `sudo usermod -a -G gpio pi`

## Notes

- The `hardware_mock.py` module automatically detects if you're on a Pi or PC
- On PC, all hardware calls are simulated (printed to console)
- On Pi, it will use the real picar-4wd library
- This allows you to develop and test logic on PC before deploying to Pi
