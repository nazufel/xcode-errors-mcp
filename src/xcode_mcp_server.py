#!/usr/bin/env python3
"""
Xcode Errors MCP Server

An MCP server that provides real-time access to Xcode build errors, warnings,
and debug output for integration with Cursor and other AI coding assistants.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime, timedelta

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    LoggingLevel
)
import mcp.types as types

from xcode_parser import XcodeLogParser, XcodeDiagnostic, XcodeBuildResult
from console_monitor import XcodeConsoleMonitor, ConsoleLog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xcode-mcp-server")

class XcodeMCPServer:
    """MCP Server for Xcode integration."""
    
    def __init__(self):
        self.server = Server("xcode-errors-mcp")
        self.parser = XcodeLogParser()
        self.console_monitor = XcodeConsoleMonitor()
        self.current_project = None
        self.recent_diagnostics = []
        self.recent_console_logs = []
        
        # Setup MCP server handlers
        self._setup_handlers()
        
        # Start console monitoring with build focus
        self.console_monitor.add_callback(self._on_console_log)
        self.console_monitor.start_build_monitoring()
    
    def _setup_handlers(self):
        """Setup MCP server request handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="get_build_errors",
                    description="Get current build errors and warnings from Xcode",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Optional project name to filter results"
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["error", "warning", "note", "all"],
                                "description": "Filter by diagnostic severity",
                                "default": "all"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_console_logs",
                    description="Get recent console output and debug logs from Xcode",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "count": {
                                "type": "integer",
                                "description": "Number of recent logs to retrieve",
                                "default": 50
                            },
                            "level": {
                                "type": "string",
                                "enum": ["debug", "info", "warning", "error", "fault", "all"],
                                "description": "Filter by log level",
                                "default": "all"
                            },
                            "filter_text": {
                                "type": "string",
                                "description": "Optional text to filter log messages"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_connected_devices",
                    description="Get list of connected iOS devices",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="save_device_logs",
                    description="Save current device logs to a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path where to save the logs"
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of recent logs to save",
                                "default": 1000
                            },
                            "filter_text": {
                                "type": "string",
                                "description": "Optional text to filter log messages"
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="list_recent_projects",
                    description="List recently built Xcode projects",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of projects to return",
                                "default": 10
                            }
                        }
                    }
                ),
                Tool(
                    name="analyze_project",
                    description="Analyze an Xcode project for common issues and patterns",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Name of the project to analyze"
                            }
                        },
                        "required": ["project_name"]
                    }
                ),
                Tool(
                    name="read_project_file",
                    description="Read a file from the current Xcode project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to read (relative to project root)"
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="watch_builds",
                    description="Start watching for new Xcode builds and errors",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Optional project name to watch"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_live_build_errors",
                    description="Get live build errors from console monitoring",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "since_minutes": {
                                "type": "integer",
                                "description": "Number of minutes to look back for errors",
                                "default": 10
                            }
                        }
                    }
                ),
                Tool(
                    name="get_device_logs",
                    description="Get logs from a specific connected iOS device or simulator",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_udid": {
                                "type": "string",
                                "description": "UDID of the device to get logs from"
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of recent logs to retrieve",
                                "default": 100
                            },
                            "since_minutes": {
                                "type": "integer",
                                "description": "Number of minutes to look back for logs",
                                "default": 10
                            }
                        },
                        "required": ["device_udid"]
                    }
                ),
                Tool(
                    name="get_device_debug_logs",
                    description="Get debug logs from a specific device, optionally filtered by app bundle ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_udid": {
                                "type": "string",
                                "description": "UDID of the device to get debug logs from"
                            },
                            "app_bundle_id": {
                                "type": "string",
                                "description": "Optional app bundle ID to filter logs"
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of recent logs to retrieve",
                                "default": 100
                            }
                        },
                        "required": ["device_udid"]
                    }
                ),
                Tool(
                    name="start_device_monitoring",
                    description="Start monitoring logs from a specific device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_udid": {
                                "type": "string",
                                "description": "UDID of the device to monitor"
                            },
                            "app_bundle_id": {
                                "type": "string",
                                "description": "Optional app bundle ID to filter logs"
                            }
                        },
                        "required": ["device_udid"]
                    }
                ),
                Tool(
                    name="get_device_debug_logs_from_xcode",
                    description="Get debug logs from connected devices that are being debugged through Xcode",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_name": {
                                "type": "string",
                                "description": "Optional device name to filter logs (e.g., 'iPad', 'iPhone')"
                            },
                            "app_bundle_id": {
                                "type": "string",
                                "description": "Optional app bundle ID to filter logs"
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of recent logs to retrieve",
                                "default": 100
                            }
                        }
                    }
                ),
                Tool(
                    name="start_device_debug_monitoring",
                    description="Start monitoring debug logs from connected devices through Xcode",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_name": {
                                "type": "string",
                                "description": "Optional device name to filter logs (e.g., 'iPad', 'iPhone')"
                            },
                            "app_bundle_id": {
                                "type": "string",
                                "description": "Optional app bundle ID to filter logs"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            
            if name == "get_build_errors":
                return await self._get_build_errors(arguments)
            elif name == "get_console_logs":
                return await self._get_console_logs(arguments)
            elif name == "get_connected_devices":
                return await self._get_connected_devices(arguments)
            elif name == "save_device_logs":
                return await self._save_device_logs(arguments)
            elif name == "list_recent_projects":
                return await self._list_recent_projects(arguments)
            elif name == "analyze_project":
                return await self._analyze_project(arguments)
            elif name == "read_project_file":
                return await self._read_project_file(arguments)
            elif name == "watch_builds":
                return await self._watch_builds(arguments)
            elif name == "get_live_build_errors":
                return await self._get_live_build_errors(arguments)
            elif name == "get_device_logs":
                return await self._get_device_logs(arguments)
            elif name == "get_device_debug_logs":
                return await self._get_device_debug_logs(arguments)
            elif name == "start_device_monitoring":
                return await self._start_device_monitoring(arguments)
            elif name == "get_device_debug_logs_from_xcode":
                return await self._get_device_debug_logs_from_xcode(arguments)
            elif name == "start_device_debug_monitoring":
                return await self._start_device_debug_monitoring(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def _get_build_errors(self, args: dict[str, Any]) -> list[TextContent]:
        """Get current build errors and warnings."""
        project_name = args.get("project_name")
        severity = args.get("severity", "all")
        
        try:
            # Debug: Check what projects are available
            recent_projects = self.parser.find_recent_projects(5)
            debug_info = f"Debug: Found {len(recent_projects)} recent projects: {recent_projects}\n"
            
            # Debug: Check if we can find the project file
            if project_name:
                project_path = self.parser._find_project_file(project_name)
                debug_info += f"Debug: Looking for project '{project_name}', found: {project_path}\n"
            else:
                debug_info += f"Debug: No project name specified, using most recent\n"
            
            diagnostics = self.parser.get_current_diagnostics(project_name)
            debug_info += f"Debug: Found {len(diagnostics)} diagnostics\n"
            
            # Filter by severity
            if severity != "all":
                diagnostics = [d for d in diagnostics if d.severity == severity]
            
            if not diagnostics:
                return [TextContent(
                    type="text",
                    text=f"{debug_info}\nNo build errors or warnings found. ✅"
                )]
            
            # Format diagnostics
            result = []
            result.append(f"Found {len(diagnostics)} diagnostic(s):\n")
            
            for i, diag in enumerate(diagnostics, 1):
                location = ""
                if diag.file_path and diag.line_number:
                    location = f" at {diag.file_path}:{diag.line_number}"
                    if diag.column_number:
                        location += f":{diag.column_number}"
                
                severity_icon = {
                    'error': '❌',
                    'warning': '⚠️',
                    'note': 'ℹ️'
                }.get(diag.severity, '•')
                
                result.append(f"{i}. {severity_icon} [{diag.severity.upper()}]{location}")
                result.append(f"   {diag.message}\n")
            
            return [TextContent(
                type="text",
                text="\n".join(result)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting build diagnostics: {str(e)}"
            )]
    
    async def _get_console_logs(self, args: dict[str, Any]) -> list[TextContent]:
        """Get recent console logs."""
        count = args.get("count", 50)
        level = args.get("level", "all")
        filter_text = args.get("filter_text")
        
        try:
            logs = self.console_monitor.get_recent_logs(count)
            
            # Filter by level
            if level != "all":
                logs = [log for log in logs if log.level == level]
            
            # Filter by text
            if filter_text:
                logs = [log for log in logs if filter_text.lower() in log.message.lower()]
            
            if not logs:
                return [TextContent(
                    type="text",
                    text="No console logs found matching criteria."
                )]
            
            # Format logs
            result = []
            result.append(f"Recent console logs ({len(logs)} entries):\n")
            
            for log in logs:
                timestamp = log.timestamp.strftime("%H:%M:%S.%f")[:-3]
                level_icon = {
                    'debug': '🔍',
                    'info': 'ℹ️',
                    'warning': '⚠️',
                    'error': '❌',
                    'fault': '💥'
                }.get(log.level, '•')
                
                result.append(f"[{timestamp}] {level_icon} {log.process}: {log.message}")
            
            return [TextContent(
                type="text",
                text="\n".join(result)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting console logs: {str(e)}"
            )]
    
    async def _get_connected_devices(self, args: dict[str, Any]) -> list[TextContent]:
        """Get list of connected iOS devices."""
        try:
            devices = self.console_monitor.get_connected_devices()
            
            if not devices:
                return [TextContent(
                    type="text",
                    text="No connected iOS devices found. Make sure your device is connected via USB and trusted."
                )]
            
            result = ["Connected iOS Devices:\n"]
            for i, device in enumerate(devices, 1):
                device_type = device.get('type', 'unknown')
                device_name = device.get('name', 'Unknown Device')
                state = device.get('state', 'Unknown')
                
                result.append(f"{i}. {device_name}")
                result.append(f"   Type: {device_type}")
                result.append(f"   State: {state}")
                
                if device.get('udid'):
                    result.append(f"   UDID: {device['udid']}")
                if device.get('product_id'):
                    result.append(f"   Product ID: {device['product_id']}")
                if device.get('runtime'):
                    result.append(f"   Runtime: {device['runtime']}")
                
                result.append("")
            
            return [TextContent(
                type="text",
                text="\n".join(result)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting connected devices: {str(e)}"
            )]
    
    async def _save_device_logs(self, args: dict[str, Any]) -> list[TextContent]:
        """Save current device logs to a file."""
        file_path = args.get("file_path")
        count = args.get("count", 1000)
        filter_text = args.get("filter_text")
        
        if not file_path:
            return [TextContent(
                type="text",
                text="Error: file_path is required"
            )]
        
        try:
            # Get recent logs
            logs = self.console_monitor.get_recent_logs(count)
            
            # Filter by text if provided
            if filter_text:
                logs = [log for log in logs if filter_text.lower() in log.message.lower()]
            
            if not logs:
                return [TextContent(
                    type="text",
                    text="No logs found matching criteria."
                )]
            
            # Save logs to file
            success = self.console_monitor.save_logs_to_file(logs, file_path)
            
            if success:
                return [TextContent(
                    type="text",
                    text=f"Successfully saved {len(logs)} logs to {file_path}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to save logs to {file_path}"
                )]
                
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error saving device logs: {str(e)}"
            )]
    
    async def _list_recent_projects(self, args: dict[str, Any]) -> list[TextContent]:
        """List recently built projects."""
        limit = args.get("limit", 10)
        
        try:
            projects = self.parser.find_recent_projects(limit)
            
            if not projects:
                return [TextContent(
                    type="text",
                    text="No recent Xcode projects found in DerivedData."
                )]
            
            result = ["Recent Xcode projects:\n"]
            for i, project in enumerate(projects, 1):
                result.append(f"{i}. {project}")
            
            return [TextContent(
                type="text",
                text="\n".join(result)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error listing projects: {str(e)}"
            )]
    
    async def _analyze_project(self, args: dict[str, Any]) -> list[TextContent]:
        """Analyze a project for common issues."""
        project_name = args.get("project_name")
        
        if not project_name:
            return [TextContent(
                type="text",
                text="Project name is required for analysis."
            )]
        
        try:
            # Get the latest build log
            log_path = self.parser.get_latest_build_log(project_name)
            if not log_path:
                return [TextContent(
                    type="text",
                    text=f"No build logs found for project: {project_name}"
                )]
            
            # Parse the build result
            build_result = self.parser.parse_build_log(log_path)
            if not build_result:
                return [TextContent(
                    type="text",
                    text=f"Could not parse build log for project: {project_name}"
                )]
            
            # Analyze diagnostics
            errors = [d for d in build_result.diagnostics if d.severity == 'error']
            warnings = [d for d in build_result.diagnostics if d.severity == 'warning']
            notes = [d for d in build_result.diagnostics if d.severity == 'note']
            
            # Common issue patterns
            swiftui_errors = [d for d in errors if 'SwiftUI' in d.message]
            compiler_errors = [d for d in errors if 'error:' in d.message and 'SwiftUI' not in d.message]
            
            result = []
            result.append(f"📊 Analysis for project: {project_name}")
            result.append(f"Build Status: {'✅ Success' if build_result.success else '❌ Failed'}")
            result.append(f"Build Time: {build_result.build_time.strftime('%Y-%m-%d %H:%M:%S')}")
            result.append("")
            
            result.append("📈 Diagnostic Summary:")
            result.append(f"  • Errors: {len(errors)}")
            result.append(f"  • Warnings: {len(warnings)}")
            result.append(f"  • Notes: {len(notes)}")
            result.append("")
            
            if swiftui_errors:
                result.append("🔍 SwiftUI Issues:")
                for error in swiftui_errors[:5]:  # Show first 5
                    location = f" ({Path(error.file_path).name}:{error.line_number})" if error.file_path else ""
                    result.append(f"  • {error.message}{location}")
                if len(swiftui_errors) > 5:
                    result.append(f"  ... and {len(swiftui_errors) - 5} more")
                result.append("")
            
            if compiler_errors:
                result.append("⚙️ Compiler Issues:")
                for error in compiler_errors[:5]:  # Show first 5
                    location = f" ({Path(error.file_path).name}:{error.line_number})" if error.file_path else ""
                    result.append(f"  • {error.message}{location}")
                if len(compiler_errors) > 5:
                    result.append(f"  ... and {len(compiler_errors) - 5} more")
            
            return [TextContent(
                type="text",
                text="\n".join(result)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error analyzing project: {str(e)}"
            )]
    
    async def _read_project_file(self, args: dict[str, Any]) -> list[TextContent]:
        """Read a file from the project."""
        file_path = args.get("file_path")
        
        if not file_path:
            return [TextContent(
                type="text",
                text="File path is required."
            )]
        
        try:
            # For now, assume files are relative to current directory
            # In a full implementation, you'd determine the project root
            path = Path(file_path)
            
            if not path.exists():
                return [TextContent(
                    type="text",
                    text=f"File not found: {file_path}"
                )]
            
            if path.is_dir():
                return [TextContent(
                    type="text",
                    text=f"Path is a directory: {file_path}"
                )]
            
            content = path.read_text(encoding='utf-8')
            
            return [TextContent(
                type="text",
                text=f"File: {file_path}\n\n{content}"
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error reading file: {str(e)}"
            )]
    
    async def _watch_builds(self, args: dict[str, Any]) -> list[TextContent]:
        """Start watching for new builds."""
        project_name = args.get("project_name")
        
        try:
            # Start watching for new build logs
            def on_new_build(build_result: XcodeBuildResult):
                logger.info(f"New build detected for {build_result.project_name}")
                self.recent_diagnostics = build_result.diagnostics
            
            observer = self.parser.watch_for_new_builds(on_new_build)
            
            return [TextContent(
                type="text",
                text=f"Started watching for new builds{f' for project: {project_name}' if project_name else ''}. "
                     "Build errors and warnings will be automatically detected."
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error starting build watcher: {str(e)}"
            )]
    
    async def _get_live_build_errors(self, args: dict[str, Any]) -> list[TextContent]:
        """Get live build errors from console monitoring."""
        since_minutes = args.get("since_minutes", 10)
        
        try:
            build_errors = self.console_monitor.get_build_errors(since_minutes)
            
            if not build_errors:
                return [TextContent(
                    type="text",
                    text=f"No build errors found in the last {since_minutes} minutes. ✅"
                )]
            
            # Format build errors
            result = []
            result.append(f"Found {len(build_errors)} build error(s) in the last {since_minutes} minutes:\n")
            
            for i, log in enumerate(build_errors, 1):
                timestamp = log.timestamp.strftime("%H:%M:%S")
                level_icon = {
                    'debug': '🔍',
                    'info': 'ℹ️',
                    'warning': '⚠️',
                    'error': '❌',
                    'fault': '💥'
                }.get(log.level, '•')
                
                result.append(f"{i}. [{timestamp}] {level_icon} {log.process}: {log.message}")
                if log.subsystem:
                    result.append(f"   Subsystem: {log.subsystem}")
                result.append("")
            
            return [TextContent(
                type="text",
                text="\n".join(result)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting live build errors: {str(e)}"
            )]
    
    async def _get_device_logs(self, args: dict[str, Any]) -> list[TextContent]:
        """Get logs from a specific device."""
        device_udid = args.get("device_udid")
        count = args.get("count", 100)
        since_minutes = args.get("since_minutes", 10)
        
        if not device_udid:
            return [TextContent(
                type="text",
                text="Error: device_udid is required"
            )]
        
        try:
            logs = self.console_monitor.get_device_logs(device_udid, count, since_minutes)
            
            if not logs:
                return [TextContent(
                    type="text",
                    text=f"No logs found for device {device_udid} in the last {since_minutes} minutes."
                )]
            
            # Format logs
            result = []
            result.append(f"Device logs for {device_udid} ({len(logs)} entries):\n")
            
            for log in logs:
                timestamp = log.timestamp.strftime("%H:%M:%S.%f")[:-3]
                level_icon = {
                    'debug': '🔍',
                    'info': 'ℹ️',
                    'warning': '⚠️',
                    'error': '❌',
                    'fault': '💥'
                }.get(log.level, '•')
                
                result.append(f"[{timestamp}] {level_icon} {log.process}: {log.message}")
                if log.subsystem:
                    result.append(f"  Subsystem: {log.subsystem}")
                result.append("")
            
            return [TextContent(
                type="text",
                text="\n".join(result)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting device logs: {str(e)}"
            )]
    
    async def _get_device_debug_logs(self, args: dict[str, Any]) -> list[TextContent]:
        """Get debug logs from a specific device."""
        device_udid = args.get("device_udid")
        app_bundle_id = args.get("app_bundle_id")
        count = args.get("count", 100)
        
        if not device_udid:
            return [TextContent(
                type="text",
                text="Error: device_udid is required"
            )]
        
        try:
            logs = self.console_monitor.get_device_debug_logs(device_udid, app_bundle_id, count)
            
            if not logs:
                filter_info = f" for app {app_bundle_id}" if app_bundle_id else ""
                return [TextContent(
                    type="text",
                    text=f"No debug logs found for device {device_udid}{filter_info}."
                )]
            
            # Format logs
            result = []
            filter_info = f" (filtered for {app_bundle_id})" if app_bundle_id else ""
            result.append(f"Debug logs for device {device_udid}{filter_info} ({len(logs)} entries):\n")
            
            for log in logs:
                timestamp = log.timestamp.strftime("%H:%M:%S.%f")[:-3]
                level_icon = {
                    'debug': '🔍',
                    'info': 'ℹ️',
                    'warning': '⚠️',
                    'error': '❌',
                    'fault': '💥'
                }.get(log.level, '•')
                
                result.append(f"[{timestamp}] {level_icon} {log.process}: {log.message}")
                if log.subsystem:
                    result.append(f"  Subsystem: {log.subsystem}")
                if log.category:
                    result.append(f"  Category: {log.category}")
                result.append("")
            
            return [TextContent(
                type="text",
                text="\n".join(result)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting device debug logs: {str(e)}"
            )]
    
    async def _start_device_monitoring(self, args: dict[str, Any]) -> list[TextContent]:
        """Start monitoring logs from a specific device."""
        device_udid = args.get("device_udid")
        app_bundle_id = args.get("app_bundle_id")
        
        if not device_udid:
            return [TextContent(
                type="text",
                text="Error: device_udid is required"
            )]
        
        try:
            # Stop any existing monitoring
            self.console_monitor.stop_monitoring()
            
            # Start device-specific monitoring
            self.console_monitor.start_device_monitoring(device_udid, app_bundle_id)
            
            filter_info = f" for app {app_bundle_id}" if app_bundle_id else ""
            return [TextContent(
                type="text",
                text=f"Started monitoring device {device_udid}{filter_info}. Debug logs will be captured in real-time."
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error starting device monitoring: {str(e)}"
            )]
    
    async def _get_device_debug_logs_from_xcode(self, args: dict[str, Any]) -> list[TextContent]:
        """Get debug logs from connected devices through Xcode."""
        device_name = args.get("device_name")
        app_bundle_id = args.get("app_bundle_id")
        count = args.get("count", 100)
        
        try:
            logs = self.console_monitor.get_device_debug_logs_from_xcode(device_name, app_bundle_id, count)
            
            if not logs:
                filter_info = []
                if device_name:
                    filter_info.append(f"device: {device_name}")
                if app_bundle_id:
                    filter_info.append(f"app: {app_bundle_id}")
                filter_text = f" ({', '.join(filter_info)})" if filter_info else ""
                return [TextContent(
                    type="text",
                    text=f"No debug logs found from connected devices through Xcode{filter_text}."
                )]
            
            # Format logs
            result = []
            filter_info = []
            if device_name:
                filter_info.append(f"device: {device_name}")
            if app_bundle_id:
                filter_info.append(f"app: {app_bundle_id}")
            filter_text = f" ({', '.join(filter_info)})" if filter_info else ""
            result.append(f"Debug logs from connected devices through Xcode{filter_text} ({len(logs)} entries):\n")
            
            for log in logs:
                timestamp = log.timestamp.strftime("%H:%M:%S.%f")[:-3]
                level_icon = {
                    'debug': '🔍',
                    'info': 'ℹ️',
                    'warning': '⚠️',
                    'error': '❌',
                    'fault': '💥'
                }.get(log.level, '•')
                
                result.append(f"[{timestamp}] {level_icon} {log.process}: {log.message}")
                if log.subsystem:
                    result.append(f"  Subsystem: {log.subsystem}")
                if log.category:
                    result.append(f"  Category: {log.category}")
                result.append("")
            
            return [TextContent(
                type="text",
                text="\n".join(result)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting device debug logs from Xcode: {str(e)}"
            )]
    
    async def _start_device_debug_monitoring(self, args: dict[str, Any]) -> list[TextContent]:
        """Start monitoring debug logs from connected devices through Xcode."""
        device_name = args.get("device_name")
        app_bundle_id = args.get("app_bundle_id")
        
        try:
            # Stop any existing monitoring
            self.console_monitor.stop_monitoring()
            
            # Start device debug monitoring
            self.console_monitor.start_device_debug_monitoring(device_name, app_bundle_id)
            
            filter_info = []
            if device_name:
                filter_info.append(f"device: {device_name}")
            if app_bundle_id:
                filter_info.append(f"app: {app_bundle_id}")
            filter_text = f" ({', '.join(filter_info)})" if filter_info else ""
            
            return [TextContent(
                type="text",
                text=f"Started monitoring debug logs from connected devices through Xcode{filter_text}. Debug logs will be captured in real-time."
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error starting device debug monitoring: {str(e)}"
            )]
    
    def _on_console_log(self, log: ConsoleLog):
        """Handle new console logs."""
        self.recent_console_logs.append(log)
        # Keep only recent logs (last 1000)
        if len(self.recent_console_logs) > 1000:
            self.recent_console_logs = self.recent_console_logs[-1000:]
    
    async def run(self):
        """Run the MCP server."""
        # Use stdin/stdout for MCP communication
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as streams:
            await self.server.run(
                streams[0], 
                streams[1],
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    server = XcodeMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
