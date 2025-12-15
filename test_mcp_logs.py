#!/usr/bin/env python3
"""
Test script to verify MCP server console log functionality.
"""

import asyncio
import json
import sys
from io import StringIO
from unittest.mock import patch

# Import the MCP server
from src.xcode_mcp_server import XcodeMCPServer

async def test_console_logs():
    """Test the get_console_logs tool."""
    print("Testing MCP server console log functionality...")
    
    # Create the server
    server = XcodeMCPServer()
    
    # Wait a moment for logs to accumulate
    print("Waiting 3 seconds for logs to accumulate...")
    await asyncio.sleep(3)
    
    # Test get_console_logs
    try:
        result = await server._get_console_logs({
            "count": 10,
            "level": "all"
        })
        
        print(f"get_console_logs returned {len(result)} results:")
        for i, content in enumerate(result):
            print(f"Result {i+1}:")
            print(f"  Type: {content.type}")
            lines = content.text.split('\n')
            for j, line in enumerate(lines[:5]):  # Show first 5 lines
                print(f"  {line}")
            if len(lines) > 5:
                print(f"  ... and {len(lines) - 5} more lines")
            print()
    
    except Exception as e:
        print(f"Error testing get_console_logs: {e}")
    
    # Test with filter
    try:
        result = await server._get_console_logs({
            "count": 5,
            "level": "error",
            "filter_text": "error"
        })
        
        print("get_console_logs with error filter:")
        for content in result:
            print(f"  {content.text}")
    
    except Exception as e:
        print(f"Error testing filtered logs: {e}")

if __name__ == "__main__":
    asyncio.run(test_console_logs())

