#!/usr/bin/env python3
"""
Test script for the Xcode parser and console monitor.
Run this to test the components before using the full MCP server.
"""

import sys
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xcode_parser import XcodeLogParser
from console_monitor import XcodeConsoleMonitor


def test_parser():
    """Test the Xcode log parser."""
    print("🔍 Testing Xcode Log Parser")
    print("=" * 40)
    
    parser = XcodeLogParser()
    
    print(f"DerivedData path: {parser.derived_data_path}")
    print(f"DerivedData exists: {parser.derived_data_path.exists()}")
    print()
    
    # List recent projects
    projects = parser.find_recent_projects(5)
    print(f"Recent projects ({len(projects)}):")
    for i, project in enumerate(projects, 1):
        print(f"  {i}. {project}")
    print()
    
    if projects:
        # Get diagnostics for the most recent project
        print("Getting diagnostics for most recent project...")
        diagnostics = parser.get_current_diagnostics()
        
        if diagnostics:
            print(f"Found {len(diagnostics)} diagnostic(s):")
            for diag in diagnostics:
                location = ""
                if diag.file_path and diag.line_number:
                    location = f" at {Path(diag.file_path).name}:{diag.line_number}"
                    if diag.column_number:
                        location += f":{diag.column_number}"
                
                severity_icon = {
                    'error': '❌',
                    'warning': '⚠️', 
                    'note': 'ℹ️'
                }.get(diag.severity, '•')
                
                print(f"  {severity_icon} [{diag.severity.upper()}]{location}: {diag.message}")
        else:
            print("  No diagnostics found (no recent build errors)")
    else:
        print("  No recent projects found")


def test_console_monitor():
    """Test the console monitor."""
    print("\n🖥️  Testing Console Monitor")
    print("=" * 40)
    
    monitor = XcodeConsoleMonitor()
    
    def log_callback(log):
        timestamp = log.timestamp.strftime("%H:%M:%S.%f")[:-3]
        level_icon = {
            'debug': '🔍',
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'fault': '💥'
        }.get(log.level, '•')
        
        print(f"[{timestamp}] {level_icon} {log.process}: {log.message}")
    
    monitor.add_callback(log_callback)
    
    print("Starting console monitoring for 10 seconds...")
    print("(Try building something in Xcode to see logs)")
    print()
    
    monitor.start_monitoring()
    
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    
    monitor.stop_monitoring()
    print("\nConsole monitoring stopped.")


def main():
    """Run tests."""
    print("🧪 Xcode MCP Server Test Suite")
    print("=" * 50)
    
    test_parser()
    
    # Ask if user wants to test console monitor
    response = input("\nTest console monitor? This will run for 10 seconds (y/n): ")
    if response.lower().startswith('y'):
        test_console_monitor()
    
    print("\n✅ Tests completed!")


if __name__ == "__main__":
    main()
