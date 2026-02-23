"""
Simple HC-SR04 ultrasonic distance reader.
Talks directly to robot_hat — no Picarx(), no servo reset.
Prints live distance readings. Press Ctrl+C to stop.
"""
from robot_hat import Ultrasonic, Pin
import time

# Same pins the PiCar-X uses internally (D2=trig, D3=echo)
us = Ultrasonic(Pin("D2"), Pin("D3", mode=Pin.IN, pull=Pin.PULL_DOWN))

print("HC-SR04 Distance Monitor — Ctrl+C to stop")
print("-" * 40)

try:
    while True:
        d = us.read()
        if d < 0:
            print(f"  {d:6.1f} cm  [INVALID]")
        elif d > 400:
            print(f"  {d:6.1f} cm  [OUT OF RANGE]")
        else:
            bar = "#" * int(d / 2)
            print(f"  {d:6.1f} cm  {bar}")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopped.")
