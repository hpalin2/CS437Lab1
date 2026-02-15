#!/usr/bin/env python3
"""
Obstacle Avoidance - Straight Line Driving with Roomba-style Recovery

Drives the car forward in a straight line. When an obstacle is detected
by the ultrasonic sensor within the threshold distance, the car stops,
backs up, turns, and continues forward.

Safety features:
  - Emergency stop on any single close raw reading (bypasses filter)
  - Slowdown zone: speed tapers as the car approaches the threshold
  - Median filter rejects noisy outlier readings
  - Consecutive bad-read failsafe: stops if sensor goes silent
  - Direction memory with escalation: reuses successful turns, flips on
    quick failure, and increases turn angle when repeatedly stuck
Usage:
    python3 navigation.py
    Press Ctrl+C to stop at any time.
"""

import time
import random
import logging
from collections import deque
from hardware_mock import get_hardware

# thresholds
OBSTACLE_THRESHOLD_CM = 15
SLOWDOWN_THRESHOLD_CM = 30
EMERGENCY_STOP_CM = 5
SLOWDOWN_MIN_SPEED = 15

# movement
BACKUP_SPEED = 30
BACKUP_DURATION = 0.8
TURN_SPEED = 30
TURN_DURATION = 0.6
FORWARD_SPEED = 30
SENSOR_INTERVAL = 0.05

# sensor filtering
FILTER_WINDOW = 5
MIN_VALID_CM = 2
MAX_VALID_CM = 400
MAX_CONSECUTIVE_BAD_READS = 5

# direction memory
MIN_SUCCESS_TIME = 2.0
# each consecutive stuck adds this much to the turn
TURN_ESCALATION_STEP = 0.3
TURN_ESCALATION_CAP = 1.5


def setup_logging():
    """Configure basic console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("navigation")


def read_distance(ultrasonic, logger):
    """
    Read and validate a single distance measurement from the ultrasonic sensor.

    Returns:
        Distance in cm, or None if the reading is invalid.
    """
    try:
        if hasattr(ultrasonic, "get_distance"):
            raw = ultrasonic.get_distance()
        else:
            raw = ultrasonic.read()
    except Exception as exc:
        logger.warning(f"Sensor read error: {exc}")
        return None

    if raw is None or raw < MIN_VALID_CM or raw > MAX_VALID_CM:
        logger.debug(f"invalid reading discarded: {raw}")
        return None

    return raw


def filtered_distance(ultrasonic, buf, logger):
    """
    Get a median-filtered distance reading.

    Median rejects single-sample noise spikes while still responding
    quickly to real obstacles. The raw emergency-stop threshold handles
    genuinely dangerous close readings independently.

    Returns:
        (filtered_cm, raw_cm) or (None, None) if no valid reading.
    """
    raw = read_distance(ultrasonic, logger)
    if raw is None:
        return None, None

    buf.append(raw)
    # median of the buffer
    ordered = sorted(buf)
    median = ordered[len(ordered) // 2]
    return median, raw


def compute_speed(distance):
    """
    Compute forward speed based on distance to nearest obstacle.

    Returns:
        Motor power percentage (int).
    """
    if distance >= SLOWDOWN_THRESHOLD_CM:
        return FORWARD_SPEED
    if distance <= OBSTACLE_THRESHOLD_CM:
        return 0
    ratio = (distance - OBSTACLE_THRESHOLD_CM) / (
        SLOWDOWN_THRESHOLD_CM - OBSTACLE_THRESHOLD_CM
    )
    return int(SLOWDOWN_MIN_SPEED + ratio * (FORWARD_SPEED - SLOWDOWN_MIN_SPEED))


def choose_turn(last_direction, forward_start_time, consecutive_stuck, logger):
    """
    Decide which direction to turn and for how long.

    Three cases:
      1. No history yet: pick randomly, base duration.
      2. Car never reached forward after the last turn (direction failed
         to clear the obstacle): flip to opposite direction and escalate
         turn duration so the car rotates further each retry.
      3. Car did reach forward:
         a. Drove for >= MIN_SUCCESS_TIME: direction worked, reuse it.
         b. Hit a new obstacle quickly: flip to the opposite direction.

    Args:
        last_direction:     Previous turn ("left"/"right") or None.
        forward_start_time: When the car last began moving forward after
                            an avoidance, or None if it never got there.
        consecutive_stuck:  How many times in a row the car failed to
                            reach forward movement after turning.
        logger:             Logger instance.

    Returns:
        (direction, turn_duration, new_consecutive_stuck)
    """
    now = time.time()

    if last_direction is None:
        direction = random.choice(["left", "right"])
        logger.info(f"  first obstacle, picking random: {direction}")
        return direction, TURN_DURATION, 0

    # never made it to forward, that direction did not work
    if forward_start_time is None:
        flipped = "right" if last_direction == "left" else "left"
        stuck = consecutive_stuck + 1
        extra = min(stuck * TURN_ESCALATION_STEP, TURN_ESCALATION_CAP)
        duration = TURN_DURATION + extra
        logger.info(
            f"  {last_direction} didn't clear it "
            f"(stuck x{stuck}), switching to {flipped} ({duration:.1f}s)"
        )
        return flipped, duration, stuck

    time_forward = now - forward_start_time

    if time_forward >= MIN_SUCCESS_TIME:
        logger.info(
            f"  last turn ({last_direction}) worked "
            f"({time_forward:.1f}s clear), reusing"
        )
        return last_direction, TURN_DURATION, 0

    # reached forward briefly but hit something new, flip
    flipped = "right" if last_direction == "left" else "left"
    logger.info(
        f"  last turn ({last_direction}) led to quick hit "
        f"({time_forward:.1f}s), flipping to {flipped}"
    )
    return flipped, TURN_DURATION, 0


def avoid_obstacle(hw, logger, obstacle_count, distance, direction, turn_duration):
    """
    Execute the stop, back up, turn maneuver.

    Args:
        hw:             Hardware interface dict.
        logger:         Logger instance.
        obstacle_count: Running count of obstacles encountered.
        distance:       Distance at which the obstacle was detected (cm).
        direction:      "left" or "right".
        turn_duration:  How long to turn (seconds), may be escalated.
    """
    logger.warning(
        f"OBSTACLE #{obstacle_count} at {distance:.1f} cm"
    )

    logger.info("  stopping")
    hw["stop"]()
    time.sleep(0.3)

    logger.info(f"  backing up ({BACKUP_SPEED}% for {BACKUP_DURATION}s)")
    hw["backward"](BACKUP_SPEED)
    time.sleep(BACKUP_DURATION)
    hw["stop"]()
    time.sleep(0.2)

    logger.info(f"  turning {direction} ({TURN_SPEED}% for {turn_duration:.1f}s)")
    if direction == "left":
        hw["turn_left"](TURN_SPEED)
    else:
        hw["turn_right"](TURN_SPEED)
    time.sleep(turn_duration)
    hw["stop"]()
    time.sleep(0.2)

    logger.info("  avoidance complete\n")


def run(hw, run_time=None):
    """
    Drive forward in a straight line, avoiding obstacles.

    Args:
        hw:       Hardware dict from get_hardware().
        run_time: Maximum seconds to run (None = run until Ctrl+C).
    """
    logger = setup_logging()

    logger.info("OBSTACLE AVOIDANCE - Straight Line Driver")
    logger.info(f"hardware: {hw.get('hardware_type', 'unknown')} | "
                f"stop: {OBSTACLE_THRESHOLD_CM}cm | "
                f"emergency: {EMERGENCY_STOP_CM}cm | "
                f"speed: {FORWARD_SPEED}%\n")

    ultrasonic = hw["ultrasonic"]
    distance_buf = deque(maxlen=FILTER_WINDOW)

    if hw.get("px"):
        hw["px"].set_dir_servo_angle(0)
        logger.info("steering servo centered")

    start = time.time()
    obstacle_count = 0
    moving_forward = False
    current_speed = 0
    consecutive_bad_reads = 0

    # direction memory
    last_direction = None
    forward_start_time = None
    consecutive_stuck = 0

    try:
        while True:
            if run_time is not None and (time.time() - start) > run_time:
                logger.info("run time limit reached, stopping")
                break

            distance, raw = filtered_distance(ultrasonic, distance_buf, logger)
            elapsed = time.time() - start

            if distance is None:
                consecutive_bad_reads += 1
                logger.debug(f"no valid reading (streak: {consecutive_bad_reads})")
                if moving_forward and consecutive_bad_reads >= MAX_CONSECUTIVE_BAD_READS:
                    logger.warning(
                        f"  {MAX_CONSECUTIVE_BAD_READS} consecutive bad reads "
                        f"while moving, precautionary stop"
                    )
                    hw["stop"]()
                    moving_forward = False
                    current_speed = 0
                time.sleep(SENSOR_INTERVAL)
                continue

            consecutive_bad_reads = 0

            # emergency stop bypasses filter entirely
            if raw is not None and raw < EMERGENCY_STOP_CM:
                obstacle_count += 1
                logger.warning(
                    f"EMERGENCY STOP, raw={raw:.1f} cm (t={elapsed:.1f}s)"
                )
                hw["stop"]()
                moving_forward = False
                current_speed = 0
                distance_buf.clear()
                direction, turn_dur, consecutive_stuck = choose_turn(
                    last_direction, forward_start_time, consecutive_stuck, logger
                )
                avoid_obstacle(hw, logger, obstacle_count, raw, direction, turn_dur)
                last_direction = direction
                forward_start_time = None
                distance_buf.clear()
                continue

            # filtered obstacle detection
            if distance < OBSTACLE_THRESHOLD_CM:
                obstacle_count += 1
                hw["stop"]()
                moving_forward = False
                current_speed = 0
                direction, turn_dur, consecutive_stuck = choose_turn(
                    last_direction, forward_start_time, consecutive_stuck, logger
                )
                avoid_obstacle(hw, logger, obstacle_count, distance, direction, turn_dur)
                last_direction = direction
                forward_start_time = None
                distance_buf.clear()
                continue

            # clear path, drive forward
            desired_speed = compute_speed(distance)

            if not moving_forward or desired_speed != current_speed:
                was_moving = moving_forward

                if hw.get("px"):
                    hw["px"].set_dir_servo_angle(0)
                hw["forward"](desired_speed)
                current_speed = desired_speed

                # mark when we first start moving forward after avoidance
                if not was_moving:
                    forward_start_time = time.time()
                    consecutive_stuck = 0

                moving_forward = True

                if distance < SLOWDOWN_THRESHOLD_CM:
                    logger.info(
                        f"slowing: {distance:.1f} cm, speed {desired_speed}% "
                        f"(t={elapsed:.1f}s)"
                    )
                elif not was_moving:
                    logger.info(
                        f"forward: {distance:.1f} cm, speed {desired_speed}% "
                        f"(t={elapsed:.1f}s)"
                    )

            logger.debug(
                f"dist={distance:.1f} raw={raw:.1f} "
                f"speed={current_speed}% (t={elapsed:.1f}s)"
            )

            time.sleep(SENSOR_INTERVAL)

    except KeyboardInterrupt:
        logger.info("\nstopped by user")
    finally:
        hw["stop"]()
        if hw.get("px"):
            hw["px"].set_dir_servo_angle(0)
        elapsed = time.time() - start
        logger.info(
            f"motors stopped, ran {elapsed:.1f}s, "
            f"avoided {obstacle_count} obstacle(s)"
        )


def main():
    """Entry point. Detects hardware and starts the avoidance loop."""
    hw = get_hardware()

    if hw["is_mock"]:
        print("[INFO] running in mock mode (no real hardware)")
        run(hw, run_time=10)
    else:
        print("[INFO] running on raspberry pi, the car WILL move")
        confirm = input("ready to start? (y/n): ").strip().lower()
        if confirm != "y":
            print("aborted")
            return
        run(hw, run_time=None)


if __name__ == "__main__":
    main()
