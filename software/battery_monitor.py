#!/usr/bin/env python3
"""
Battery Monitor - Check PiCar-X battery status

Reads the battery voltage from the Robot HAT board and displays:
- Current voltage
- Estimated battery percentage
- Status indicator (Good/Low/Critical)

The PiCar-X uses a 2-cell Li-ion battery pack (7.4V nominal):
- Full charge: ~8.4V
- Nominal: 7.4V
- Low: 7.0V
- Critical: 6.5V (cutoff at 6.0V for protection)

Usage:
    python3 battery_monitor.py              # Single reading
    python3 battery_monitor.py --watch      # Continuous monitoring
    python3 battery_monitor.py --watch 2    # Update every 2 seconds
"""

import sys
import time
import argparse


def get_battery_info():
    """
    Read battery voltage and calculate status.
    
    Returns:
        dict: {
            'voltage': float (volts),
            'percentage': int (0-100),
            'status': str ('Good', 'Low', 'Critical', or 'Unknown'),
            'is_mock': bool
        }
    """
    try:
        # Try to import robot_hat (only available on Pi)
        from robot_hat import utils
        voltage = utils.get_battery_voltage()
        is_mock = False
    except ImportError:
        # Mock mode for PC testing
        voltage = 7.8  # Simulated voltage
        is_mock = True
    except Exception as e:
        # Error reading - could be hardware issue
        return {
            'voltage': 0.0,
            'percentage': 0,
            'status': 'Error',
            'is_mock': False,
            'error': str(e)
        }
    
    # Calculate percentage based on Li-ion discharge curve
    # 2-cell Li-ion: 8.4V (full) → 6.0V (empty)
    V_FULL = 8.4
    V_EMPTY = 6.0
    V_LOW = 7.0
    V_CRITICAL = 6.5
    
    # Linear approximation (real Li-ion curve is non-linear but this is close enough)
    if voltage >= V_FULL:
        percentage = 100
    elif voltage <= V_EMPTY:
        percentage = 0
    else:
        percentage = int(((voltage - V_EMPTY) / (V_FULL - V_EMPTY)) * 100)
    
    # Determine status
    if voltage >= V_LOW:
        status = 'Good'
    elif voltage >= V_CRITICAL:
        status = 'Low'
    elif voltage > V_EMPTY:
        status = 'Critical'
    else:
        status = 'Empty'
    
    return {
        'voltage': voltage,
        'percentage': percentage,
        'status': status,
        'is_mock': is_mock
    }


def format_battery_display(info):
    """
    Format battery info for terminal display with color coding.
    
    Args:
        info: dict from get_battery_info()
    
    Returns:
        str: Formatted display string
    """
    if 'error' in info:
        return f"❌ Error reading battery: {info['error']}"
    
    voltage = info['voltage']
    percentage = info['percentage']
    status = info['status']
    is_mock = info['is_mock']
    
    # ANSI color codes
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    GRAY = '\033[90m'
    
    # Color based on status
    if status == 'Good':
        color = GREEN
        icon = '🔋'
    elif status == 'Low':
        color = YELLOW
        icon = '🔋'
    elif status == 'Critical':
        color = RED
        icon = '⚠️ '
    else:
        color = RED
        icon = '❌'
    
    # Progress bar (10 blocks)
    bar_length = 10
    filled = int((percentage / 100) * bar_length)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    # Build display
    lines = []
    lines.append(f"{color}{icon}  Battery Status: {status}{RESET}")
    lines.append(f"   Voltage:    {voltage:.2f}V")
    lines.append(f"   Percentage: {percentage}%")
    lines.append(f"   [{color}{bar}{RESET}]")
    
    if is_mock:
        lines.append(f"{GRAY}   (Mock mode - simulated reading){RESET}")
    
    return '\n'.join(lines)


def watch_battery(interval=1.0):
    """
    Continuously monitor battery and update display.
    
    Args:
        interval: Update interval in seconds
    """
    print("Battery Monitor - Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Clear previous output (move cursor up and clear)
            if watch_battery.first_run:
                watch_battery.first_run = False
            else:
                # Move cursor up 6 lines and clear
                print('\033[6A\033[J', end='')
            
            info = get_battery_info()
            display = format_battery_display(info)
            print(display)
            
            # Warning messages
            if info['status'] == 'Low':
                print("\n⚠️  Battery low - consider charging soon")
            elif info['status'] == 'Critical':
                print("\n🚨 Battery critical - charge immediately!")
            elif info['status'] == 'Empty':
                print("\n❌ Battery empty - system may shut down")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nBattery monitoring stopped.")

watch_battery.first_run = True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Monitor PiCar-X battery voltage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                  # Single reading
  %(prog)s --watch          # Continuous monitoring (1s updates)
  %(prog)s --watch 5        # Update every 5 seconds
        """
    )
    
    parser.add_argument(
        '--watch', '-w',
        nargs='?',
        const=1.0,
        type=float,
        metavar='SECONDS',
        help='Continuously monitor battery (default: 1 second interval)'
    )
    
    args = parser.parse_args()
    
    if args.watch is not None:
        watch_battery(args.watch)
    else:
        # Single reading
        info = get_battery_info()
        display = format_battery_display(info)
        print(display)
        
        # Exit code based on status
        if info['status'] in ['Critical', 'Empty']:
            sys.exit(2)  # Critical status
        elif info['status'] == 'Low':
            sys.exit(1)  # Warning status
        else:
            sys.exit(0)  # Good status


if __name__ == '__main__':
    main()
