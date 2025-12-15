"""
Console monitor for capturing Xcode debug output and runtime logs.
"""

import subprocess
import re
import threading
import queue
from typing import List, Optional, Callable, NamedTuple, Dict
from datetime import datetime
import time

class ConsoleLog(NamedTuple):
    """Represents a console log entry."""
    timestamp: datetime
    level: str  # 'debug', 'info', 'warning', 'error', 'fault'
    subsystem: str
    category: str
    message: str
    process: str

class XcodeConsoleMonitor:
    """Monitors Xcode console output and debug logs using macOS log system."""
    
    def __init__(self, log_file_path: Optional[str] = None):
        self.is_monitoring = False
        self.log_queue = queue.Queue()
        self.monitor_thread = None
        self.callbacks = []
        self.log_file_path = log_file_path
        self.log_file = None
        
        # Patterns for parsing log entries
        # Updated pattern to match actual macOS log format with timezone and localhost
        self.log_pattern = re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+[-+]\d{4})\s+'
            r'(?P<hostname>\w+)\s+'
            r'(?P<process>[\w\-\.]+)\[(?P<pid>\d+)\]:\s+'
            r'(?:\((?P<framework>[\w\.]+)\)\s+)?'
            r'(?:\[(?P<subsystem>[\w\.]+):(?P<category>[\w\.]+)\]\s+)?'
            r'(?P<message>.*)'
        )
        
        # Xcode-related process names to monitor
        self.xcode_processes = [
            'Xcode',
            'xcodebuild',
            'xctest',
            'Simulator',
            'iOS Simulator',
            'iPhone Simulator',
            'iPad Simulator',
            'swift',
            'clang',
            'ld',
            'Metal',
            'ibtool',
            'actool',
            'assetutil',
            'debugserver',  # Debug server for device debugging
            'lldb',         # LLDB debugger
            'DTDeviceServiceBase',  # Device service
            'DTServiceHub',         # Device service hub
            'com.apple.dt.DeviceKit',  # Device kit
            'com.apple.dt.IDE.IDEiOSSupportCore'  # iOS support core
        ]
        
        # Patterns for build errors and warnings
        self.build_error_patterns = [
            r'error:',
            r'warning:',
            r'note:',
            r'BUILD FAILED',
            r'Compile Swift',
            r'CompileC',
            r'Ld ',
            r'CodeSign',
            r'PhaseScriptExecution'
        ]
    
    def start_monitoring(self, app_bundle_id: Optional[str] = None, include_devices: bool = True):
        """Start monitoring console logs.
        
        Args:
            app_bundle_id: Optional app bundle ID to filter logs
            include_devices: Whether to include logs from connected devices
        """
        if self.is_monitoring:
            print("Already monitoring logs...")
            return
        
        device_info = " (including connected devices)" if include_devices else ""
        print(f"Starting console monitoring{f' for bundle ID: {app_bundle_id}' if app_bundle_id else ''}{device_info}...")
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_logs,
            args=(app_bundle_id, include_devices),
            daemon=True
        )
        self.monitor_thread.start()
        print("Console monitoring started successfully.")
    
    def stop_monitoring(self):
        """Stop monitoring console logs."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
    
    def add_callback(self, callback: Callable[[ConsoleLog], None]):
        """Add a callback to be called when new logs are received."""
        self.callbacks.append(callback)
    
    def get_recent_logs(self, count: int = 100) -> List[ConsoleLog]:
        """Get recent console logs."""
        logs = []
        try:
            while len(logs) < count and not self.log_queue.empty():
                logs.append(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        return logs
    
    def _monitor_logs(self, app_bundle_id: Optional[str], include_devices: bool = True):
        """Monitor logs using macOS log command."""
        # Build the log command
        cmd = ['log', 'stream', '--style', 'syslog', '--level', 'debug']
        
        # Add predicate to filter for relevant processes
        predicates = []
        
        # Filter by Xcode-related processes
        process_predicates = [f'process == "{proc}"' for proc in self.xcode_processes]
        if process_predicates:
            predicates.append(f'({" OR ".join(process_predicates)})')
        
        # Filter by app bundle ID if provided
        if app_bundle_id:
            # Include both subsystem and sender predicates for better device log capture
            app_predicates = [
                f'subsystem == "{app_bundle_id}"',
                f'sender == "{app_bundle_id}"',
                f'processImagePath CONTAINS "{app_bundle_id}"'
            ]
            predicates.append(f'({" OR ".join(app_predicates)})')
        
        # Add device-specific filtering if enabled
        if include_devices and app_bundle_id:
            # This helps capture logs from apps running on connected devices
            predicates.append('eventType == logEvent OR eventType == traceEvent')
        
        if predicates:
            predicate_str = ' AND '.join(predicates) if len(predicates) > 1 else predicates[0]
            cmd.extend(['--predicate', predicate_str])
            print(f"Using predicate: {predicate_str}")
        else:
            print("No predicate specified - monitoring all processes")
        
        print(f"Running command: {' '.join(cmd)}")
        
        try:
            # Start the log streaming process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            print("Log streaming process started, waiting for logs...")
            
            # Read logs line by line
            line_count = 0
            while self.is_monitoring and process.poll() is None:
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    if line and not line.startswith("Filtering"):
                        line_count += 1
                        if line_count <= 3:  # Show first few lines for debugging
                            print(f"Raw log line {line_count}: {line}")
                        
                        log_entry = self._parse_log_line(line)
                        if log_entry:
                            if line_count <= 3:
                                print(f"Parsed log entry: {log_entry}")
                            
                            # Add to queue
                            self.log_queue.put(log_entry)
                            
                            # Call callbacks
                            for callback in self.callbacks:
                                try:
                                    callback(log_entry)
                                except Exception as e:
                                    print(f"Error in log callback: {e}")
                        elif line_count <= 3:
                            print(f"Failed to parse line: {line}")
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
            
            print(f"Stopping log monitoring. Processed {line_count} lines.")
            
            # Clean up
            process.terminate()
            process.wait(timeout=5)
            
        except Exception as e:
            print(f"Error monitoring logs: {e}")
    
    def _parse_log_line(self, line: str) -> Optional[ConsoleLog]:
        """Parse a single log line."""
        match = self.log_pattern.match(line)
        if not match:
            return None
        
        try:
            timestamp_str = match.group('timestamp')
            # Handle timezone in timestamp (remove timezone for parsing)
            timestamp_base = timestamp_str[:-5]  # Remove timezone part like "-0400"
            timestamp = datetime.strptime(timestamp_base, '%Y-%m-%d %H:%M:%S.%f')
            
            # Determine log level from context (macOS logs don't have explicit levels in syslog style)
            # We'll infer the level from the message content or default to 'info'
            level = 'info'  # Default level
            message = match.group('message')
            
            # Try to infer level from message content
            message_lower = message.lower()
            if any(word in message_lower for word in ['error', 'failed', 'exception', 'crash']):
                level = 'error'
            elif any(word in message_lower for word in ['warning', 'warn']):
                level = 'warning'
            elif any(word in message_lower for word in ['debug', 'trace']):
                level = 'debug'
            
            return ConsoleLog(
                timestamp=timestamp,
                level=level,
                subsystem=match.group('subsystem') or match.group('framework') or '',
                category=match.group('category') or '',
                message=message,
                process=match.group('process')
            )
        except Exception as e:
            print(f"Error parsing log line '{line}': {e}")
            return None
    
    def get_error_logs(self, since_minutes: int = 10) -> List[ConsoleLog]:
        """Get error logs from the last N minutes."""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(minutes=since_minutes)
        
        error_logs = []
        logs = self.get_recent_logs(1000)  # Get more logs to search through
        
        for log in logs:
            if (log.timestamp >= cutoff_time and 
                log.level in ['error', 'fault'] and
                any(proc in log.process for proc in self.xcode_processes)):
                error_logs.append(log)
        
        return error_logs
    
    def get_debug_logs(self, filter_text: Optional[str] = None, since_minutes: int = 5) -> List[ConsoleLog]:
        """Get debug logs, optionally filtered by text."""
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(minutes=since_minutes)
        
        debug_logs = []
        logs = self.get_recent_logs(1000)
        
        for log in logs:
            if log.timestamp >= cutoff_time:
                if filter_text and filter_text.lower() not in log.message.lower():
                    continue
                debug_logs.append(log)
        
        return debug_logs
    
    def get_build_errors(self, since_minutes: int = 10) -> List[ConsoleLog]:
        """Get build-related error logs from the last N minutes."""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(minutes=since_minutes)
        
        build_errors = []
        logs = self.get_recent_logs(1000)
        
        for log in logs:
            if log.timestamp >= cutoff_time:
                # Check if it's a build-related process
                is_build_process = any(proc in log.process for proc in self.xcode_processes)
                
                # Check if message contains build error patterns
                is_build_error = any(
                    re.search(pattern, log.message, re.IGNORECASE) 
                    for pattern in self.build_error_patterns
                )
                
                if is_build_process and (is_build_error or log.level in ['error', 'fault']):
                    build_errors.append(log)
        
        return build_errors
    
    def start_build_monitoring(self, project_name: Optional[str] = None):
        """Start monitoring specifically for build errors and warnings."""
        print(f"Starting build monitoring{f' for project: {project_name}' if project_name else ''}...")
        
        # Use a more targeted predicate for build monitoring
        predicates = []
        
        # Monitor Xcode and build tools
        build_processes = ['Xcode', 'xcodebuild', 'swift', 'clang', 'ld']
        process_predicates = [f'process == "{proc}"' for proc in build_processes]
        if process_predicates:
            predicates.append(f'({" OR ".join(process_predicates)})')
        
        # Add project-specific filtering if provided
        if project_name:
            predicates.append(f'eventMessage CONTAINS "{project_name}"')
        
        # Monitor for build-related events
        predicates.append('eventType == logEvent')
        
        if predicates:
            predicate_str = ' AND '.join(predicates)
            print(f"Build monitoring predicate: {predicate_str}")
            
            # Start monitoring with the build-specific predicate
            self._start_build_log_monitoring(predicate_str)
        else:
            print("No build monitoring predicate - monitoring all processes")
            self.start_monitoring()
    
    def _start_build_log_monitoring(self, predicate: str):
        """Start monitoring with a specific predicate for build logs."""
        if self.is_monitoring:
            print("Already monitoring logs...")
            return
        
        self.is_monitoring = True
        
        # Build the log command with the predicate
        cmd = ['log', 'stream', '--style', 'syslog', '--level', 'debug', '--predicate', predicate]
        
        print(f"Running build monitoring command: {' '.join(cmd)}")
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_build_logs,
            args=(cmd,),
            daemon=True
        )
        self.monitor_thread.start()
        print("Build monitoring started successfully.")
    
    def _monitor_build_logs(self, cmd):
        """Monitor build logs using the specified command."""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            print("Build log streaming process started...")
            
            line_count = 0
            while self.is_monitoring and process.poll() is None:
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    if line and not line.startswith("Filtering"):
                        line_count += 1
                        
                        log_entry = self._parse_log_line(line)
                        if log_entry:
                            # Add to queue
                            self.log_queue.put(log_entry)
                            
                            # Call callbacks
                            for callback in self.callbacks:
                                try:
                                    callback(log_entry)
                                except Exception as e:
                                    print(f"Error in build log callback: {e}")
                
                time.sleep(0.01)
            
            print(f"Build monitoring stopped. Processed {line_count} lines.")
            
            process.terminate()
            process.wait(timeout=5)
            
        except Exception as e:
            print(f"Error in build log monitoring: {e}")
    
    def get_connected_devices(self) -> List[Dict[str, str]]:
        """Get list of connected iOS devices including simulators and physical devices."""
        devices = []
        
        # Get iOS Simulator devices
        try:
            result = subprocess.run(
                ['xcrun', 'simctl', 'list', 'devices', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                import json
                try:
                    data = json.loads(result.stdout)
                    devices_data = data.get('devices', {})
                    
                    for runtime, device_list in devices_data.items():
                        if 'iOS' in runtime or 'iPadOS' in runtime:
                            for device in device_list:
                                devices.append({
                                    'name': device.get('name', 'Unknown Device'),
                                    'udid': device.get('udid', ''),
                                    'state': device.get('state', 'Unknown'),
                                    'type': 'simulator',
                                    'runtime': runtime,
                                    'product_id': device.get('productType', '')
                                })
                    
                except json.JSONDecodeError:
                    pass
                    
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        
        # Get connected physical devices using xcrun devicectl (preferred method)
        try:
            result = subprocess.run(
                ['xcrun', 'devicectl', 'list', 'devices'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header line
                    for line in lines[1:]:  # Skip header
                        parts = line.split()
                        if len(parts) >= 5:
                            name = parts[0]
                            state = parts[3]
                            model = ' '.join(parts[4:]) if len(parts) > 4 else 'Unknown Model'
                            
                            # Extract device ID from the line (it's in the third column)
                            device_id = parts[2] if len(parts) > 2 else ''
                            
                            # Check if it's an iOS device
                            if ('iPhone' in model or 'iPad' in model or 'iPod' in model or 
                                'iPhone' in name or 'iPad' in name or 'iPod' in name):
                                devices.append({
                                    'name': name,
                                    'udid': device_id,
                                    'state': state,
                                    'type': 'physical_device',
                                    'runtime': 'Physical Device',
                                    'product_id': model
                                })
                    
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Fallback: Get connected physical devices using system_profiler
        try:
            result = subprocess.run(
                ['system_profiler', 'SPUSBDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                import json
                try:
                    data = json.loads(result.stdout)
                    usb_data = data.get('SPUSBDataType', [])
                    
                    def find_ios_devices(items):
                        ios_devices = []
                        for item in items:
                            # Look for iOS devices
                            if 'vendor_id' in item and item.get('vendor_id') == '0x05ac':  # Apple vendor ID
                                product_id = item.get('product_id', '')
                                device_name = item.get('_name', 'Unknown iOS Device')
                                
                                # Common iOS device product IDs and names
                                ios_indicators = [
                                    '0x12a8', '0x12ab', '0x1281', '0x1227', '0x1290', '0x1291', '0x1292', '0x1293',
                                    '0x12a9', '0x12aa', '0x12ac', '0x12ad', '0x12ae', '0x12af', '0x12b0', '0x12b1'
                                ]
                                if (any(pid in product_id for pid in ios_indicators) or 
                                    'iPhone' in device_name or 'iPad' in device_name or 'iPod' in device_name):
                                    ios_devices.append({
                                        'name': device_name,
                                        'product_id': product_id,
                                        'type': 'physical_device',
                                        'state': 'connected',
                                        'udid': '',  # Physical devices don't have UDID in USB data
                                        'runtime': 'Physical Device'
                                    })
                            
                            # Recursively search in sub-items
                            if '_items' in item:
                                ios_devices.extend(find_ios_devices(item['_items']))
                        
                        return ios_devices
                    
                    devices.extend(find_ios_devices(usb_data))
                    
                except json.JSONDecodeError:
                    pass
                    
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        
        return devices
    
    def get_device_logs(self, device_udid: str, count: int = 100, since_minutes: int = 10) -> List[ConsoleLog]:
        """Get logs from a specific iOS device (simulator or physical)."""
        logs = []
        
        try:
            # Use xcrun simctl spawn to get device logs
            cmd = [
                'xcrun', 'simctl', 'spawn', device_udid,
                'log', 'show', '--last', f'{since_minutes}m', '--style', 'syslog'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line:
                        log_entry = self._parse_log_line(line)
                        if log_entry:
                            logs.append(log_entry)
                            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"Error getting device logs for {device_udid}: {e}")
        
        return logs[-count:] if logs else []
    
    def get_device_debug_logs(self, device_udid: str, app_bundle_id: str = None, count: int = 100) -> List[ConsoleLog]:
        """Get debug logs from a specific device, optionally filtered by app bundle ID."""
        logs = []
        
        try:
            # Build command for device-specific log streaming
            cmd = ['xcrun', 'simctl', 'spawn', device_udid, 'log', 'stream', '--style', 'syslog', '--level', 'debug']
            
            # Add app-specific filtering if provided
            if app_bundle_id:
                cmd.extend(['--predicate', f'subsystem == "{app_bundle_id}" OR sender == "{app_bundle_id}"'])
            
            # Start the process and collect logs for a short time
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Collect logs for a few seconds
            import time
            start_time = time.time()
            while time.time() - start_time < 5:  # Collect for 5 seconds
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    if line:
                        log_entry = self._parse_log_line(line)
                        if log_entry:
                            logs.append(log_entry)
                            if len(logs) >= count:
                                break
                time.sleep(0.01)
            
            process.terminate()
            process.wait(timeout=2)
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"Error getting device debug logs for {device_udid}: {e}")
        
        return logs[-count:] if logs else []
    
    def get_device_debug_logs_from_xcode(self, device_name: str = None, app_bundle_id: str = None, count: int = 100) -> List[ConsoleLog]:
        """Get debug logs from connected devices that are being debugged through Xcode."""
        logs = []
        
        try:
            # Use log command to get recent Xcode debug logs
            cmd = ['log', 'show', '--last', '10m', '--style', 'syslog', '--level', 'debug']
            
            # Build predicate for Xcode debug processes and device-related logs
            predicates = []
            
            # Monitor Xcode debug processes
            debug_processes = [
                'Xcode', 'debugserver', 'lldb', 'DTDeviceServiceBase', 
                'DTServiceHub', 'com.apple.dt.DeviceKit', 'com.apple.dt.IDE.IDEiOSSupportCore'
            ]
            process_predicates = [f'process == "{proc}"' for proc in debug_processes]
            if process_predicates:
                predicates.append(f'({" OR ".join(process_predicates)})')
            
            # Add device-specific filtering if provided
            if device_name:
                predicates.append(f'eventMessage CONTAINS "{device_name}"')
            
            # Add app-specific filtering if provided
            if app_bundle_id:
                predicates.append(f'(eventMessage CONTAINS "{app_bundle_id}" OR subsystem == "{app_bundle_id}" OR sender == "{app_bundle_id}")')
            
            # Add patterns for device debug logs (use OR instead of AND for better matching)
            debug_patterns = [
                'device', 'debug', 'console', 'log', 'print', 'NSLog', 'os_log',
                'debugger', 'breakpoint', 'exception', 'crash'
            ]
            if debug_patterns:
                pattern_predicates = [f'eventMessage CONTAINS "{pattern}"' for pattern in debug_patterns]
                predicates.append(f'({" OR ".join(pattern_predicates)})')
            
            if predicates:
                predicate_str = ' AND '.join(predicates) if len(predicates) > 1 else predicates[0]
                cmd.extend(['--predicate', predicate_str])
            
            print(f"Running debug log command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line:
                        log_entry = self._parse_log_line(line)
                        if log_entry:
                            logs.append(log_entry)
                            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"Error getting device debug logs from Xcode: {e}")
        
        return logs[-count:] if logs else []
    
    def start_device_debug_monitoring(self, device_name: str = None, app_bundle_id: str = None):
        """Start monitoring debug logs from connected devices through Xcode."""
        if self.is_monitoring:
            print("Already monitoring logs...")
            return
        
        print(f"Starting device debug monitoring{f' for device: {device_name}' if device_name else ''}")
        if app_bundle_id:
            print(f"Filtering for app: {app_bundle_id}")
        
        self.is_monitoring = True
        
        # Build command for Xcode debug log monitoring
        cmd = ['log', 'stream', '--style', 'syslog', '--level', 'debug']
        
        # Build predicate for Xcode debug processes
        predicates = []
        
        # Monitor Xcode debug processes
        debug_processes = [
            'Xcode', 'debugserver', 'lldb', 'DTDeviceServiceBase', 
            'DTServiceHub', 'com.apple.dt.DeviceKit', 'com.apple.dt.IDE.IDEiOSSupportCore'
        ]
        process_predicates = [f'process == "{proc}"' for proc in debug_processes]
        if process_predicates:
            predicates.append(f'({" OR ".join(process_predicates)})')
        
        # Add device-specific filtering if provided
        if device_name:
            predicates.append(f'eventMessage CONTAINS "{device_name}"')
        
        # Add app-specific filtering if provided
        if app_bundle_id:
            predicates.append(f'(eventMessage CONTAINS "{app_bundle_id}" OR subsystem == "{app_bundle_id}" OR sender == "{app_bundle_id}")')
        
        # Add patterns for device debug logs (use OR instead of AND for better matching)
        debug_patterns = [
            'device', 'debug', 'console', 'log', 'print', 'NSLog', 'os_log',
            'debugger', 'breakpoint', 'exception', 'crash'
        ]
        if debug_patterns:
            pattern_predicates = [f'eventMessage CONTAINS "{pattern}"' for pattern in debug_patterns]
            predicates.append(f'({" OR ".join(pattern_predicates)})')
        
        if predicates:
            predicate_str = ' AND '.join(predicates) if len(predicates) > 1 else predicates[0]
            cmd.extend(['--predicate', predicate_str])
        
        print(f"Running debug monitoring command: {' '.join(cmd)}")
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_device_debug_logs,
            args=(cmd,),
            daemon=True
        )
        self.monitor_thread.start()
        print("Device debug monitoring started successfully.")
    
    def _monitor_device_debug_logs(self, cmd):
        """Monitor device debug logs using the specified command."""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            print("Device debug log streaming process started...")
            
            line_count = 0
            while self.is_monitoring and process.poll() is None:
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    if line and not line.startswith("Filtering"):
                        line_count += 1
                        
                        log_entry = self._parse_log_line(line)
                        if log_entry:
                            # Add to queue
                            self.log_queue.put(log_entry)
                            
                            # Call callbacks
                            for callback in self.callbacks:
                                try:
                                    callback(log_entry)
                                except Exception as e:
                                    print(f"Error in device debug log callback: {e}")
                
                time.sleep(0.01)
            
            print(f"Device debug monitoring stopped. Processed {line_count} lines.")
            
            process.terminate()
            process.wait(timeout=5)
            
        except Exception as e:
            print(f"Error in device debug log monitoring: {e}")
    
    def start_device_monitoring(self, device_udid: str, app_bundle_id: str = None):
        """Start monitoring logs from a specific device."""
        if self.is_monitoring:
            print("Already monitoring logs...")
            return
        
        print(f"Starting device log monitoring for device: {device_udid}")
        if app_bundle_id:
            print(f"Filtering for app: {app_bundle_id}")
        
        self.is_monitoring = True
        
        # Build device-specific monitoring command
        cmd = ['xcrun', 'simctl', 'spawn', device_udid, 'log', 'stream', '--style', 'syslog', '--level', 'debug']
        
        if app_bundle_id:
            cmd.extend(['--predicate', f'subsystem == "{app_bundle_id}" OR sender == "{app_bundle_id}"'])
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_device_logs,
            args=(cmd,),
            daemon=True
        )
        self.monitor_thread.start()
        print("Device log monitoring started successfully.")
    
    def _monitor_device_logs(self, cmd):
        """Monitor device logs using the specified command."""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            print("Device log streaming process started...")
            
            line_count = 0
            while self.is_monitoring and process.poll() is None:
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    if line and not line.startswith("Filtering"):
                        line_count += 1
                        
                        log_entry = self._parse_log_line(line)
                        if log_entry:
                            # Add to queue
                            self.log_queue.put(log_entry)
                            
                            # Call callbacks
                            for callback in self.callbacks:
                                try:
                                    callback(log_entry)
                                except Exception as e:
                                    print(f"Error in device log callback: {e}")
                
                time.sleep(0.01)
            
            print(f"Device monitoring stopped. Processed {line_count} lines.")
            
            process.terminate()
            process.wait(timeout=5)
            
        except Exception as e:
            print(f"Error in device log monitoring: {e}")
    
    def save_logs_to_file(self, logs: List[ConsoleLog], file_path: str):
        """Save console logs to a file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# Xcode Device Console Logs - {datetime.now().isoformat()}\n\n")
                
                for log in logs:
                    timestamp = log.timestamp.isoformat()
                    f.write(f"[{timestamp}] {log.level.upper()} {log.process}: {log.message}\n")
                    if log.subsystem:
                        f.write(f"  Subsystem: {log.subsystem}\n")
                    if log.category:
                        f.write(f"  Category: {log.category}\n")
                    f.write("\n")
                    
            print(f"Saved {len(logs)} logs to {file_path}")
            return True
            
        except Exception as e:
            print(f"Error saving logs to file: {e}")
            return False


def main():
    """Test the console monitor."""
    monitor = XcodeConsoleMonitor()
    
    def log_callback(log: ConsoleLog):
        print(f"[{log.timestamp.strftime('%H:%M:%S')}] {log.level.upper()} "
              f"{log.process}: {log.message}")
    
    monitor.add_callback(log_callback)
    
    print("Starting console monitoring (press Ctrl+C to stop)...")
    monitor.start_monitoring()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop_monitoring()


if __name__ == "__main__":
    main()
