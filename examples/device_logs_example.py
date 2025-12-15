#!/usr/bin/env python3
"""
Example script demonstrating device log capture from connected iOS devices.
"""

import sys
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from console_monitor import XcodeConsoleMonitor

def main():
    """Demonstrate device log monitoring and saving."""
    print("Device Log Monitoring Example")
    print("=" * 40)
    
    # Create console monitor
    monitor = XcodeConsoleMonitor()
    
    # Check for connected devices
    print("1. Checking for connected devices...")
    devices = monitor.get_connected_devices()
    
    if devices:
        print(f"Found {len(devices)} connected iOS devices:")
        for i, device in enumerate(devices, 1):
            print(f"   {i}. {device['name']} (Type: {device['type']})")
            if device.get('product_id'):
                print(f"      Product ID: {device['product_id']}")
    else:
        print("   No connected iOS devices found.")
        print("   Make sure your device is connected via USB and trusted.")
    
    print("\n2. Starting log monitoring...")
    
    # Set up log callback to show real-time logs
    def log_callback(log):
        timestamp = log.timestamp.strftime('%H:%M:%S.%f')[:-3]
        level_icon = {
            'debug': '🔍',
            'info': 'ℹ️', 
            'warning': '⚠️',
            'error': '❌',
            'fault': '💥'
        }.get(log.level, '•')
        
        print(f"[{timestamp}] {level_icon} {log.process}: {log.message}")
    
    monitor.add_callback(log_callback)
    
    # Start monitoring with device support
    # Replace 'com.yourcompany.yourapp' with your actual app bundle ID
    app_bundle_id = input("Enter your app bundle ID (or press Enter to monitor all): ").strip()
    if not app_bundle_id:
        app_bundle_id = None
    
    monitor.start_monitoring(app_bundle_id=app_bundle_id, include_devices=True)
    
    print(f"Monitoring logs{f' for {app_bundle_id}' if app_bundle_id else ''}...")
    print("Press Ctrl+C to stop and save logs to file\n")
    
    try:
        # Monitor for a while
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n3. Stopping monitoring and saving logs...")
        monitor.stop_monitoring()
        
        # Get recent logs and save to file
        recent_logs = monitor.get_recent_logs(1000)
        
        if recent_logs:
            log_file = Path.home() / "Desktop" / f"xcode_device_logs_{int(time.time())}.txt"
            success = monitor.save_logs_to_file(recent_logs, str(log_file))
            
            if success:
                print(f"✅ Saved {len(recent_logs)} logs to: {log_file}")
                print(f"📁 You can now use this log file with your MCP server!")
            else:
                print("❌ Failed to save logs to file")
        else:
            print("No logs captured during monitoring session")

if __name__ == "__main__":
    main()
