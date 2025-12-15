#!/bin/bash

# Xcode Errors MCP Server Installation Script

set -e

echo "🚀 Installing Xcode Errors MCP Server..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This MCP server requires macOS to access Xcode."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Make scripts executable
chmod +x src/xcode_mcp_server.py
chmod +x examples/test_parser.py

echo "✅ Installation completed!"
echo ""
echo "🧪 To test the installation, run:"
echo "   source venv/bin/activate"
echo "   python examples/test_parser.py"
echo ""
echo "📋 To configure Cursor, add this to your MCP settings:"
echo "   Copy the contents of cursor_config.json to your Cursor MCP configuration"
echo ""
echo "🔧 Usage:"
echo "   1. Build a project in Xcode to generate some logs"
echo "   2. Run the test script to verify everything works"
echo "   3. Configure Cursor to use the MCP server"
echo "   4. Use the tools in Cursor to get live Xcode diagnostics!"
echo ""
echo "Available MCP tools:"
echo "   • get_build_errors - Get current build errors and warnings"
echo "   • get_console_logs - Get recent console output"
echo "   • list_recent_projects - List recently built projects"
echo "   • analyze_project - Analyze a project for issues"
echo "   • read_project_file - Read project files"
echo "   • watch_builds - Monitor for new builds"
