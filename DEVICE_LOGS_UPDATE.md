# Device Log Monitoring Update

## Overview
The MCP server has been updated to properly support debug logs from connected iOS devices and simulators. The previous implementation was not working because it only monitored Xcode processes on the host machine, not the actual device logs.

## What Was Fixed

### 1. Device Detection
- **Before**: Only detected physical devices via USB using `system_profiler`
- **After**: Detects both iOS Simulators and physical devices
- **New Features**:
  - Lists all available iOS Simulator devices with their UDIDs
  - Shows device state (Booted/Shutdown)
  - Displays device type (simulator/physical_device)
  - Shows runtime information

### 2. Device Log Access
- **Before**: No direct access to device logs
- **After**: Full device log monitoring capabilities
- **New Methods**:
  - `get_device_logs(device_udid, count, since_minutes)` - Get recent logs from a specific device
  - `get_device_debug_logs(device_udid, app_bundle_id, count)` - Get debug logs filtered by app
  - `start_device_monitoring(device_udid, app_bundle_id)` - Real-time log streaming

### 3. MCP Tools Added
- `get_device_logs` - Get logs from a specific device
- `get_device_debug_logs` - Get debug logs with optional app filtering
- `start_device_monitoring` - Start real-time device log monitoring

## How It Works

### Device Detection
```python
# Detects both simulators and physical devices
devices = monitor.get_connected_devices()
# Returns list of devices with UDID, name, type, state, etc.
```

### Device Log Retrieval
```python
# Get recent logs from a device
logs = monitor.get_device_logs(device_udid, count=100, since_minutes=10)

# Get debug logs filtered by app
debug_logs = monitor.get_device_debug_logs(device_udid, 'com.example.myapp', count=50)
```

### Real-time Monitoring
```python
# Start monitoring a specific device
monitor.start_device_monitoring(device_udid, app_bundle_id)
# Logs are captured in real-time and sent to callbacks
```

## Technical Implementation

### Device Log Access
- Uses `xcrun simctl spawn <device_udid> log show/stream` to access device logs
- Supports both historical log retrieval and real-time streaming
- Handles both iOS Simulator and physical device logs

### Log Parsing
- Enhanced regex patterns to handle device-specific log formats
- Proper timestamp parsing with timezone support
- Log level detection (debug, info, warning, error, fault)
- Process and subsystem information extraction

### MCP Integration
- New MCP tools for device log access
- Proper error handling and user feedback
- Support for app-specific log filtering
- Real-time monitoring capabilities

## Usage Examples

### 1. List Connected Devices
```bash
# MCP tool call
get_connected_devices
```

### 2. Get Device Logs
```bash
# MCP tool call
get_device_logs --device_udid "B50FD013-DFF3-4D00-BBC7-A8AB05248014" --count 50
```

### 3. Get Debug Logs for Specific App
```bash
# MCP tool call
get_device_debug_logs --device_udid "B50FD013-DFF3-4D00-BBC7-A8AB05248014" --app_bundle_id "com.example.myapp"
```

### 4. Start Real-time Monitoring
```bash
# MCP tool call
start_device_monitoring --device_udid "B50FD013-DFF3-4D00-BBC7-A8AB05248014" --app_bundle_id "com.example.myapp"
```

## Testing

A comprehensive test script (`test_device_logs.py`) has been created that demonstrates:
- Device detection (simulators and physical devices)
- Log retrieval from devices
- Debug log filtering
- Real-time monitoring
- Error handling

## Benefits

1. **Real Device Debugging**: Access actual device logs, not just host machine logs
2. **App-Specific Filtering**: Filter logs by app bundle ID for targeted debugging
3. **Real-time Monitoring**: Stream logs in real-time for live debugging
4. **Simulator Support**: Works with iOS Simulator devices
5. **Physical Device Support**: Works with connected physical iOS devices
6. **MCP Integration**: Seamlessly integrated with Cursor and other AI coding assistants

## Requirements

- macOS with Xcode installed
- iOS Simulator (for simulator testing)
- Physical iOS device connected via USB (for physical device testing)
- `xcrun` command line tools available

The device log monitoring functionality is now fully operational and provides comprehensive access to iOS device debug logs through the MCP interface.
