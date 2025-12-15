# Troubleshooting Xcode MCP Server

## Common Issues and Solutions

### 1. Red Indicator / "No tools or prompts" in Cursor

**Symptoms:**
- MCP server shows red indicator in Cursor settings
- "No tools or prompts" message
- Server appears disconnected

**Solutions:**

#### A. Check File Paths
Ensure all paths in `cursor_config.json` are absolute and correct.

**IMPORTANT**: Replace `/path/to/your/xcode-errors-mcp` with your actual installation directory.

Example configuration:
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

To find your installation path, run:
```bash
cd xcode-errors-mcp
pwd
```

#### B. Test Server Manually
```bash
cd /path/to/your/xcode-errors-mcp  # Replace with your actual path
source venv/bin/activate
python src/xcode_mcp_server.py
```

If the server hangs (waiting for input), that's good - it means it's running correctly.

#### C. Check Virtual Environment
```bash
# Verify virtual environment has all dependencies
source venv/bin/activate
pip list | grep mcp
```

Should show `mcp` package installed.

#### D. Restart Cursor Completely
1. Quit Cursor entirely (⌘+Q)
2. Wait 10 seconds
3. Restart Cursor
4. Check MCP server status

### 2. Permission Issues

**Symptoms:**
- "Permission denied" errors
- Scripts not executable

**Solutions:**
```bash
chmod +x src/xcode_mcp_server.py
chmod +x install.sh
```

### 3. Python Environment Issues

**Symptoms:**
- `externally-managed-environment` errors
- Missing packages

**Solutions:**
```bash
# Use the virtual environment
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Xcode Integration Issues

**Symptoms:**
- "No recent projects found"
- "DerivedData not found"

**Solutions:**

#### A. Verify DerivedData Location
```bash
ls ~/Library/Developer/Xcode/DerivedData
```

#### B. Build a Project in Xcode
1. Open any iOS project in Xcode
2. Build it (⌘+B)
3. This creates logs that the MCP server can read

### 5. Console Monitoring Issues

**Symptoms:**
- No console logs appearing
- Console monitor errors

**Solutions:**

The console monitor requires macOS system permissions. If it's not working:
1. The basic build error detection will still work
2. Console logs are optional functionality

## Testing Your Installation

### 1. Basic Test
```bash
cd /path/to/your/xcode-errors-mcp  # Replace with your actual path
source venv/bin/activate
python examples/test_parser.py
```

Should show:
- ✅ DerivedData path exists
- ✅ Recent projects found
- ✅ Parser working

### 2. MCP Server Test
```bash
source venv/bin/activate
python src/xcode_mcp_server.py
```

Should start without errors and wait for input.

### 3. Full Integration Test
1. Configure Cursor with the MCP server
2. Restart Cursor
3. Check server status (should show green indicator)
4. Try using a tool in Cursor chat:
   ```
   Use the list_recent_projects tool to show my Xcode projects
   ```

## Debug Information

### Check MCP Logs in Cursor
1. Open Cursor
2. Go to View → Output
3. Select "MCP Logs" from dropdown
4. Look for error messages

### Server Logs
The server prints diagnostic information to stdout/stderr. Check the Cursor output panel for any error messages.

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `No such file or directory` | Wrong path in config | Update paths in `cursor_config.json` to match your installation directory |
| `Permission denied` | Script not executable | Run `chmod +x src/xcode_mcp_server.py` |
| `Module not found` | Missing dependencies | Run `pip install -r requirements.txt` |
| `DerivedData not found` | No Xcode projects built | Build a project in Xcode |

## Getting Help

If you're still having issues:

1. Check the error logs in Cursor's Output panel
2. Run the test scripts to isolate the problem
3. Verify all file paths are correct
4. Make sure virtual environment is activated
5. Try restarting both Cursor and your computer

## Success Indicators

When everything is working correctly:
- ✅ Green indicator in Cursor MCP settings
- ✅ Tools visible in MCP server list
- ✅ Can use tools in Cursor chat
- ✅ Build errors appear automatically when building in Xcode
