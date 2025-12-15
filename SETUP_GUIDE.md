# Setup Guide for Users

This guide explains how to configure the Xcode MCP Server after cloning the repository.

## Quick Start

1. **Clone and install:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/xcode-errors-mcp.git
   cd xcode-errors-mcp
   ./install.sh
   ```

2. **Find your installation path:**
   ```bash
   pwd  # Copy this path for the next step
   ```

3. **Configure Cursor:**
   - Open Cursor Settings → Features → Model Context Protocol
   - Copy the contents of `cursor_config.json`
   - **CRITICAL**: Replace all `/path/to/your/xcode-errors-mcp` with your actual path from step 2
   - Paste into your MCP configuration
   - Restart Cursor completely (⌘+Q and reopen)

## Required Path Updates

You must update these placeholders in `cursor_config.json`:

| Placeholder | Replace with |
|------------|-------------|
| `/path/to/your/xcode-errors-mcp/venv/bin/python` | `YOUR_PATH/venv/bin/python` |
| `/path/to/your/xcode-errors-mcp/src/xcode_mcp_server.py` | `YOUR_PATH/src/xcode_mcp_server.py` |
| `/path/to/your/xcode-errors-mcp/src` | `YOUR_PATH/src` |

## Example Configuration

If you installed to `/Users/yourname/xcode-errors-mcp`, your configuration should be:

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

## Testing Your Setup

1. **Test the parser:**
   ```bash
   source venv/bin/activate
   python examples/test_parser.py
   ```

2. **Verify MCP server:**
   - Check Cursor settings for green indicator next to "xcode-errors"
   - Try using a tool in Cursor: "Use the list_recent_projects tool"

## Troubleshooting

If you see a red indicator in Cursor:
1. Double-check all paths in your configuration
2. Make sure you restarted Cursor completely
3. See `TROUBLESHOOTING.md` for detailed solutions

## Usage

Once configured, you can use these tools in Cursor:
- `get_build_errors()` - Get current build errors and warnings
- `get_console_logs()` - Get recent console output  
- `list_recent_projects()` - List recently built Xcode projects
