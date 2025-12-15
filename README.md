# Xcode Errors MCP Server (WIP)

An MLOps pipeline using MCP (Model Context Protocol) server that bridges Xcode and Cursor, enabling real-time access to Xcode build errors, warnings, and debug output directly within Cursor.

⚠️ This repo is still under development and things may break without warning.

## Features

- **Real-time Error Monitoring**: Automatically detects and parses Xcode build errors and warnings
- **Debug Log Streaming**: Captures and streams Xcode console output and debug logs
- **Project Analysis**: Analyzes Swift/SwiftUI projects for common issues
- **File Integration**: Provides tools to read and modify project files based on diagnostics
- **Live Updates**: Monitors DerivedData for new build results

## How It Works

1. **DerivedData Monitoring**: Watches Xcode's DerivedData directory for new build logs
2. **Log Parsing**: Extracts structured diagnostic information from build logs
3. **Console Integration**: Captures real-time debug output from Xcode's console
4. **MCP Interface**: Exposes diagnostics and file operations through MCP protocol
5. **Cursor Integration**: Allows Cursor to query errors and make fixes automatically

## Architecture

```
Xcode Build System
       ↓
DerivedData Logs → MCP Server → Cursor/LLM
       ↓                ↑
Console Output ←--------┘
```

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/xcode-errors-mcp.git  # Replace YOUR_USERNAME with actual GitHub username
   cd xcode-errors-mcp
   ```

2. Run the installation script:
   ```bash
   ./install.sh
   ```

3. Configure Cursor MCP settings:
   - Open Cursor settings
   - Navigate to MCP configuration
   - Copy the contents of `cursor_config.json` to your MCP configuration
   - **IMPORTANT**: Replace `/path/to/your/xcode-errors-mcp` with your actual installation path
   - Example: If you cloned to `/Users/yourname/xcode-errors-mcp`, update all paths accordingly

4. Restart Cursor completely (⌘+Q and reopen) to activate the MCP server connection

## Usage

Once connected, Cursor can:
- Query current build errors: `get_build_errors()`
- Monitor debug output: `get_console_logs()`
- Analyze project structure: `analyze_project()`
- Read/write project files: `read_file()`, `write_file()`

## Quick Start

1. **Install dependencies:**
   ```bash
   ./install.sh
   ```

2. **Test the installation:**
   ```bash
   python3 examples/test_parser.py
   ```

3. **Configure Cursor:**
   - Open Cursor Settings → Features → Model Context Protocol
   - Copy the contents of `cursor_config.json` to your MCP configuration
   - **CRITICAL:** Replace all instances of `/path/to/your/xcode-errors-mcp` with your actual installation path
   - Example configuration for installation in `/Users/yourname/xcode-errors-mcp`:
     ```json
     {
       "mcpServers": {
         "xcode-errors": {
           "command": "/Users/yourname/xcode-errors-mcp/venv/bin/python",
           "args": [
             "/Users/yourname/xcode-errors-mcp/src/xcode_mcp_server.py"
           ],
           "env": {
             "PYTHONPATH": "/Users/yourname/xcode-errors-mcp/src"
           }
         }
       }
     }
     ```
   - Restart Cursor completely (⌘+Q and reopen)

4. **Verify it's working:**
   - Check that the MCP server shows a green indicator in Cursor settings
   - If you see a red indicator, check `TROUBLESHOOTING.md`

5. **Start using it:**
   - Build a project in Xcode (to generate some logs)
   - In Cursor, you can now use tools like:
     - `get_build_errors()` - Get current build errors
     - `get_console_logs()` - Get debug output
     - `list_recent_projects()` - See your projects
     - `analyze_project("ProjectName")` - Analyze issues

## Configuration Placeholders

After cloning this repository, you **must** update the following placeholders with your actual paths:

### 1. cursor_config.json
Replace `/path/to/your/xcode-errors-mcp` with your installation directory:
- `command`: Path to your Python virtual environment
- `args`: Path to the MCP server script
- `env.PYTHONPATH`: Path to the src directory

### 2. Finding Your Installation Path
```bash
cd xcode-errors-mcp
pwd  # This shows your full installation path
```

### 3. Example Configuration
If you installed to `/Users/yourname/xcode-errors-mcp`, your `cursor_config.json` should look like:
```json
{
  "mcpServers": {
    "xcode-errors": {
      "command": "/Users/yourname/xcode-errors-mcp/venv/bin/python",
      "args": [
        "/Users/yourname/xcode-errors-mcp/src/xcode_mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/yourname/xcode-errors-mcp/src"
      }
    }
  }
}
```

## For Publishers

Before publishing this repository, update the following placeholders:

1. **README.md**: Replace `YOUR_USERNAME` with your actual GitHub username in the clone URL
2. **cursor_config.json**: Already contains placeholder paths that users will need to update
3. **TROUBLESHOOTING.md**: Already uses placeholder paths

## Development Status

✅ **Ready for Testing** - Core functionality implemented and tested!
