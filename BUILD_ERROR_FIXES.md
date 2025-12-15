# Xcode Build Error Detection Fixes

## Problem
The MCP server couldn't detect Xcode build errors that were clearly visible in Xcode's Issue Navigator.

## Root Causes Identified

1. **Binary Log Format Issue**: The parser tried to read `.xcactivitylog` files as text, but these are binary files requiring special handling
2. **Missing Real-time Monitoring**: Only looked at completed build logs, not live build errors
3. **Incorrect Log Parsing**: Regex patterns weren't comprehensive enough for all error types
4. **Limited Process Monitoring**: Didn't monitor all Xcode build tools

## Solutions Implemented

### 1. Fixed Binary Log Parsing ✅
- Added proper handling for `.xcactivitylog` files using `xcrun xcactivitylog`
- Implemented fallback text extraction for binary files
- Enhanced error pattern matching

### 2. Added Live Build Monitoring ✅
- Integrated `xcodebuild` command for real-time error detection
- Added project file discovery across common locations
- Implemented scheme detection and live building

### 3. Enhanced Console Monitoring ✅
- Expanded process monitoring to include all build tools (swift, clang, ld, etc.)
- Added build-specific error pattern detection
- Implemented targeted log filtering for build events

### 4. New MCP Tools ✅
- `get_live_build_errors` - Get real-time build errors from console monitoring
- Enhanced `get_build_errors` - Now tries live detection first, falls back to logs
- Improved error formatting with better icons and timestamps

## Key Improvements

### Xcode Parser (`xcode_parser.py`)
- **Live Build Detection**: Uses `xcodebuild` to get current errors
- **Project Discovery**: Automatically finds `.xcodeproj`/`.xcworkspace` files
- **Binary Log Support**: Properly handles `.xcactivitylog` files
- **Enhanced Patterns**: Better regex for Swift, Objective-C, and build errors

### Console Monitor (`console_monitor.py`)
- **Build-Focused Monitoring**: Specifically targets build processes
- **Extended Process List**: Monitors swift, clang, ld, Metal, etc.
- **Build Error Patterns**: Detects compilation, linking, and signing errors
- **Real-time Filtering**: Uses macOS log predicates for targeted monitoring

### MCP Server (`xcode_mcp_server.py`)
- **New Tool**: `get_live_build_errors` for real-time error detection
- **Enhanced Error Detection**: Tries live monitoring first, falls back to logs
- **Better Formatting**: Improved error display with timestamps and icons

## Usage

### For Live Build Errors
```python
# The MCP server now automatically tries live detection first
diagnostics = parser.get_current_diagnostics(project_name)
```

### For Console Build Monitoring
```python
# Start build-focused monitoring
monitor.start_build_monitoring(project_name)

# Get recent build errors
build_errors = monitor.get_build_errors(since_minutes=10)
```

### New MCP Tool
```
get_live_build_errors(since_minutes=10)
```

## Testing

Run the test script to verify improvements:
```bash
python test_build_errors.py
```

## Expected Results

The MCP server should now be able to:
1. ✅ Detect live build errors as they occur in Xcode
2. ✅ Parse binary `.xcactivitylog` files properly
3. ✅ Monitor all Xcode build tools and processes
4. ✅ Provide real-time error detection via console monitoring
5. ✅ Fall back to log file parsing when live detection fails

## Dependencies

- `xcrun` command (part of Xcode Command Line Tools)
- `xcodebuild` command (part of Xcode)
- macOS `log` command for console monitoring
