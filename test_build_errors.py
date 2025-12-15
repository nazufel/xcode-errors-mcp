#!/usr/bin/env python3
"""
Test script to verify Xcode build error detection improvements.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from xcode_parser import XcodeLogParser
from console_monitor import XcodeConsoleMonitor

def test_parser():
    """Test the enhanced Xcode parser."""
    print("🔍 Testing Xcode Parser...")
    parser = XcodeLogParser()
    
    # Test finding recent projects
    projects = parser.find_recent_projects(5)
    print(f"Found {len(projects)} recent projects:")
    for i, project in enumerate(projects, 1):
        print(f"  {i}. {project}")
    
    # Test getting current diagnostics
    print("\n🔍 Testing live build diagnostics...")
    diagnostics = parser.get_current_diagnostics()
    print(f"Found {len(diagnostics)} current diagnostics:")
    
    for i, diag in enumerate(diagnostics, 1):
        location = ""
        if diag.file_path and diag.line_number:
            location = f" at {diag.file_path}:{diag.line_number}"
            if diag.column_number:
                location += f":{diag.column_number}"
        
        severity_icon = {
            'error': '❌',
            'warning': '⚠️',
            'note': 'ℹ️'
        }.get(diag.severity, '•')
        
        print(f"  {i}. {severity_icon} [{diag.severity.upper()}]{location}: {diag.message}")

def test_console_monitor():
    """Test the enhanced console monitor."""
    print("\n🔍 Testing Console Monitor...")
    monitor = XcodeConsoleMonitor()
    
    # Test getting connected devices
    devices = monitor.get_connected_devices()
    print(f"Found {len(devices)} connected devices:")
    for i, device in enumerate(devices, 1):
        print(f"  {i}. {device['name']} ({device['type']})")
    
    # Test getting recent logs
    logs = monitor.get_recent_logs(10)
    print(f"\nFound {len(logs)} recent console logs:")
    for i, log in enumerate(logs, 1):
        timestamp = log.timestamp.strftime("%H:%M:%S")
        level_icon = {
            'debug': '🔍',
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'fault': '💥'
        }.get(log.level, '•')
        print(f"  {i}. [{timestamp}] {level_icon} {log.process}: {log.message}")
    
    # Test getting build errors
    build_errors = monitor.get_build_errors(10)
    print(f"\nFound {len(build_errors)} build errors in last 10 minutes:")
    for i, log in enumerate(build_errors, 1):
        timestamp = log.timestamp.strftime("%H:%M:%S")
        print(f"  {i}. [{timestamp}] {log.process}: {log.message}")

def main():
    """Run all tests."""
    print("🚀 Testing Xcode Errors MCP Server Improvements\n")
    
    try:
        test_parser()
        test_console_monitor()
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
