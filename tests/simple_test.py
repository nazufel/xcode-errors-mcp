#!/usr/bin/env python3
"""
Simple test to verify MCP server tools are defined.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from xcode_mcp_server import XcodeMCPServer

def test_tools():
    """Test that tools are properly defined."""
    print("🧪 Testing MCP Server Tool Definitions")
    print("=" * 50)
    
    server = XcodeMCPServer()
    
    # Check if the server has the list_tools handler
    if hasattr(server.server, '_tool_handlers'):
        print("✅ Tool handlers found")
        print(f"Number of tool handlers: {len(server.server._tool_handlers)}")
        for name in server.server._tool_handlers.keys():
            print(f"  • {name}")
    else:
        print("❌ No tool handlers found")
    
    # Try to get capabilities
    try:
        capabilities = server.server.get_capabilities()
        print(f"\n✅ Server capabilities: {capabilities}")
    except Exception as e:
        print(f"❌ Error getting capabilities: {e}")
    
    print("\n🔧 Testing individual components...")
    
    # Test parser
    try:
        projects = server.parser.find_recent_projects(3)
        print(f"✅ Parser working - found {len(projects)} projects")
    except Exception as e:
        print(f"❌ Parser error: {e}")
    
    # Test console monitor
    try:
        logs = server.console_monitor.get_recent_logs(5)
        print(f"✅ Console monitor working - {len(logs)} logs")
    except Exception as e:
        print(f"❌ Console monitor error: {e}")

if __name__ == "__main__":
    test_tools()
