#!/usr/bin/env python3
"""
Test script to verify MCP server tools are properly defined.
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from xcode_mcp_server import XcodeMCPServer

async def test_mcp_server():
    """Test that the MCP server has tools properly defined."""
    print("🧪 Testing MCP Server Tools")
    print("=" * 40)
    
    server = XcodeMCPServer()
    
    # Get the tools list
    tools = await server.server._handle_request("tools/list", {})
    
    if "tools" in tools:
        print(f"✅ Found {len(tools['tools'])} tools:")
        for tool in tools["tools"]:
            print(f"  • {tool['name']}: {tool['description']}")
        print()
        
        # Test a simple tool call
        try:
            result = await server.server._handle_request("tools/call", {
                "name": "list_recent_projects",
                "arguments": {"limit": 3}
            })
            print("✅ Tool call test successful!")
            print("Sample output:", result.get("content", [{}])[0].get("text", "")[:100] + "...")
            
        except Exception as e:
            print(f"❌ Tool call test failed: {e}")
    else:
        print("❌ No tools found!")
        print("Response:", tools)

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
