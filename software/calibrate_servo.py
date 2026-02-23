"""
Interactive servo calibration for PiCar-X cam_pan and cam_tilt.

Commands (type and press Enter):
  +N   nudge N degrees positive  (e.g. +5)
  -N   nudge N degrees negative  (e.g. -3)
  0    reset offset to zero
  s    save current offset and move to next axis
  q    quit without saving
"""
from picarx import Picarx
import time


def calibrate_axis(px, axis='pan'):
    if axis == 'pan':
        offset  = px.cam_pan_cali_val
        set_fn  = px.set_cam_pan_angle
        save_fn = px.cam_pan_servo_calibrate
        label   = "PAN  (left / right)"
    else:
        offset  = px.cam_tilt_cali_val
        set_fn  = px.set_cam_tilt_angle
        save_fn = px.cam_tilt_servo_calibrate
        label   = "TILT (up / down)  — negative = points DOWN"

    # Apply current offset and command 0° so servo moves to calibrated center
    if axis == 'pan':
        px.cam_pan_cali_val = offset
    else:
        px.cam_tilt_cali_val = offset
    set_fn(0)
    time.sleep(0.3)

    print(f"\n{'='*55}")
    print(f"  Calibrating {label}")
    print(f"  Current offset: {offset:+.1f}°")
    print(f"  Commands:  +N / -N  to nudge  |  0  to reset  |  s  to save  |  q  to skip")
    print()

    while True:
        print(f"  offset = {offset:+.1f}°  > ", end='', flush=True)
        try:
            cmd = input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return offset

        if not cmd:
            continue
        elif cmd == '0':
            offset = 0.0
        elif cmd == 's':
            save_fn(offset)
            print(f"  ✓ Saved {axis} offset = {offset:+.1f}° to /opt/picar-x/picar-x.conf")
            return offset
        elif cmd == 'q':
            print(f"  Skipped — {axis} calibration unchanged.")
            return offset
        else:
            try:
                delta = float(cmd)
                offset += delta
            except ValueError:
                print(f"  Unknown command '{cmd}'")
                continue

        # Move servo to show the new offset
        if axis == 'pan':
            px.cam_pan_cali_val = offset
        else:
            px.cam_tilt_cali_val = offset
        set_fn(0)
        time.sleep(0.2)


def main():
    print("PiCar-X Servo Calibration")
    print("==========================")
    print("Initialising picarx (servo will move to current calibration position)...")
    px = Picarx()
    time.sleep(0.5)

    print(f"\nLoaded calibration from /opt/picar-x/picar-x.conf:")
    print(f"  cam_pan_cali_val  = {px.cam_pan_cali_val:+.1f}°")
    print(f"  cam_tilt_cali_val = {px.cam_tilt_cali_val:+.1f}°")

    print("\n--- Step 1: PAN ---")
    print("Nudge until the sensor head points STRAIGHT FORWARD.")
    calibrate_axis(px, 'pan')

    print("\n--- Step 2: TILT ---")
    print("Nudge until the sensor is LEVEL or very slightly downward.")
    print("Tip: -5° to -10° typically fixes upward tilt on PiCar-X.")
    calibrate_axis(px, 'tilt')

    # Return to center with saved calibration
    px.set_cam_pan_angle(0)
    px.set_cam_tilt_angle(0)

    print(f"\nFinal calibration values:")
    print(f"  cam_pan_cali_val  = {px.cam_pan_cali_val:+.1f}°")
    print(f"  cam_tilt_cali_val = {px.cam_tilt_cali_val:+.1f}°")
    print("\nDone. Values are saved and will persist across reboots.")


if __name__ == "__main__":
    main()
