"""
Xcode log parser for extracting build errors, warnings, and diagnostic information.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, NamedTuple
from datetime import datetime
import glob

class XcodeDiagnostic(NamedTuple):
    """Represents a single Xcode diagnostic (error, warning, or note)."""
    severity: str  # 'error', 'warning', 'note'
    message: str
    file_path: Optional[str]
    line_number: Optional[int]
    column_number: Optional[int]
    category: Optional[str]
    code: Optional[str]
    timestamp: datetime

class XcodeBuildResult(NamedTuple):
    """Represents the result of an Xcode build."""
    project_name: str
    scheme: str
    target: str
    configuration: str
    success: bool
    diagnostics: List[XcodeDiagnostic]
    build_time: datetime
    duration: Optional[float]

class XcodeLogParser:
    """Parses Xcode build logs and extracts diagnostic information."""
    
    def __init__(self):
        self.derived_data_path = self._get_derived_data_path()
        
        # Regex patterns for parsing Xcode logs
        self.error_patterns = [
            # Swift compiler errors with file:line:column format
            r"^(.+?):(\d+):(\d+): error: (.+)$",
            # SwiftUI specific errors
            r"^(.+?):(\d+):(\d+): error: \[SwiftUI\] (.+)$",
            # Swift scope and syntax errors
            r"^(.+?):(\d+):(\d+): error: Cannot find '(.+?)' in scope$",
            r"^(.+?):(\d+):(\d+): error: Use of unresolved identifier '(.+?)'$",
            r"^(.+?):(\d+):(\d+): error: Expected '(.+?)'$",
            r"^(.+?):(\d+):(\d+): error: Missing argument for parameter '(.+?)'$",
            r"^(.+?):(\d+):(\d+): error: Generic parameter '(.+?)' could not be inferred$",
            r"^(.+?):(\d+):(\d+): error: Incorrect argument label in call$",
            r"^(.+?):(\d+):(\d+): error: Cannot convert value of type '(.+?)' to expected argument type '(.+?)'$",
            # Generic error pattern
            r"^error: (.+)$",
            # Build error pattern
            r"^\*\* BUILD FAILED \*\*$",
        ]
        
        self.warning_patterns = [
            # Swift compiler warnings
            r"^(.+?):(\d+):(\d+): warning: (.+)$",
            # SwiftUI warnings
            r"^(.+?):(\d+):(\d+): warning: \[SwiftUI\] (.+)$",
            # Generic warning pattern
            r"^warning: (.+)$",
        ]
        
        self.note_patterns = [
            # Compiler notes
            r"^(.+?):(\d+):(\d+): note: (.+)$",
            # Generic note pattern
            r"^note: (.+)$",
        ]
    
    def _get_derived_data_path(self) -> Path:
        """Get the path to Xcode's DerivedData directory."""
        home = Path.home()
        derived_data = home / "Library" / "Developer" / "Xcode" / "DerivedData"
        return derived_data
    
    def find_recent_projects(self, limit: int = 10) -> List[str]:
        """Find recently built Xcode projects."""
        if not self.derived_data_path.exists():
            return []
        
        projects = []
        for project_dir in self.derived_data_path.iterdir():
            if project_dir.is_dir() and not project_dir.name.startswith('.'):
                # Get modification time
                mod_time = project_dir.stat().st_mtime
                projects.append((project_dir.name, mod_time))
        
        # Sort by modification time (most recent first)
        projects.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in projects[:limit]]
    
    def get_latest_build_log(self, project_name: Optional[str] = None) -> Optional[Path]:
        """Get the path to the most recent build log."""
        if project_name:
            project_path = self.derived_data_path / project_name
        else:
            # Find the most recently modified project
            recent_projects = self.find_recent_projects(1)
            if not recent_projects:
                return None
            project_path = self.derived_data_path / recent_projects[0]
        
        if not project_path.exists():
            return None
        
        # Look for build logs in Logs/Build directory
        logs_path = project_path / "Logs" / "Build"
        if not logs_path.exists():
            return None
        
        # Find the most recent .xcactivitylog file
        log_files = list(logs_path.glob("*.xcactivitylog"))
        if not log_files:
            return None
        
        # Return the most recently modified log file
        return max(log_files, key=lambda f: f.stat().st_mtime)
    
    def parse_build_log(self, log_path: Path) -> Optional[XcodeBuildResult]:
        """Parse an Xcode build log file."""
        if not log_path.exists():
            return None
        
        try:
            # Handle binary .xcactivitylog files properly
            if log_path.suffix == '.xcactivitylog':
                content = self._extract_text_from_xcactivitylog(log_path)
            else:
                # Try to read as text for other log formats
                try:
                    content = log_path.read_text(encoding='utf-8', errors='ignore')
                except UnicodeDecodeError:
                    # If it's binary, try to extract readable text
                    with open(log_path, 'rb') as f:
                        raw_content = f.read()
                        content = raw_content.decode('utf-8', errors='ignore')
            
            return self._parse_log_content(content, log_path)
            
        except Exception as e:
            print(f"Error parsing log file {log_path}: {e}")
            return None
    
    def _extract_text_from_xcactivitylog(self, log_path: Path) -> str:
        """Extract text content from binary .xcactivitylog files."""
        try:
            # Try using xcrun to convert the log to text
            result = subprocess.run(
                ['xcrun', 'xcactivitylog', '--log', str(log_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"xcrun xcactivitylog failed: {result.stderr}")
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"xcrun not available or failed: {e}")
        
        # Fallback: try to extract readable text from binary
        try:
            with open(log_path, 'rb') as f:
                raw_content = f.read()
                # Look for readable text patterns in the binary data
                content = raw_content.decode('utf-8', errors='ignore')
                # Filter out most binary noise, keep lines that look like build output
                lines = content.split('\n')
                filtered_lines = []
                for line in lines:
                    line = line.strip()
                    if (line and 
                        (':' in line or 'error:' in line.lower() or 'warning:' in line.lower() or 
                         'note:' in line.lower() or 'BUILD' in line.upper())):
                        filtered_lines.append(line)
                return '\n'.join(filtered_lines)
        except Exception as e:
            print(f"Fallback text extraction failed: {e}")
            return ""
    
    def _parse_log_content(self, content: str, log_path: Path) -> XcodeBuildResult:
        """Parse the content of a build log."""
        lines = content.split('\n')
        diagnostics = []
        
        project_name = "Unknown"
        scheme = "Unknown"
        target = "Unknown" 
        configuration = "Unknown"
        success = True
        build_time = datetime.fromtimestamp(log_path.stat().st_mtime)
        
        # Extract project info from log path or content
        if "DerivedData" in str(log_path):
            parts = str(log_path).split("/")
            for i, part in enumerate(parts):
                if part == "DerivedData" and i + 1 < len(parts):
                    project_name = parts[i + 1].split("-")[0]
                    break
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check for build failure
            if "BUILD FAILED" in line or "** BUILD FAILED **" in line:
                success = False
            
            # Parse diagnostics
            diagnostic = self._parse_diagnostic_line(line)
            if diagnostic:
                diagnostics.append(diagnostic)
        
        return XcodeBuildResult(
            project_name=project_name,
            scheme=scheme,
            target=target,
            configuration=configuration,
            success=success,
            diagnostics=diagnostics,
            build_time=build_time,
            duration=None
        )
    
    def _parse_diagnostic_line(self, line: str) -> Optional[XcodeDiagnostic]:
        """Parse a single line for diagnostic information."""
        # Try error patterns
        for pattern in self.error_patterns:
            match = re.match(pattern, line)
            if match:
                if len(match.groups()) >= 4:
                    # Full diagnostic with file, line, column
                    return XcodeDiagnostic(
                        severity='error',
                        message=match.group(4),
                        file_path=match.group(1),
                        line_number=int(match.group(2)),
                        column_number=int(match.group(3)),
                        category=None,
                        code=None,
                        timestamp=datetime.now()
                    )
                else:
                    # Generic error
                    return XcodeDiagnostic(
                        severity='error',
                        message=match.group(1),
                        file_path=None,
                        line_number=None,
                        column_number=None,
                        category=None,
                        code=None,
                        timestamp=datetime.now()
                    )
        
        # Try warning patterns
        for pattern in self.warning_patterns:
            match = re.match(pattern, line)
            if match:
                if len(match.groups()) >= 4:
                    return XcodeDiagnostic(
                        severity='warning',
                        message=match.group(4),
                        file_path=match.group(1),
                        line_number=int(match.group(2)),
                        column_number=int(match.group(3)),
                        category=None,
                        code=None,
                        timestamp=datetime.now()
                    )
                else:
                    return XcodeDiagnostic(
                        severity='warning',
                        message=match.group(1),
                        file_path=None,
                        line_number=None,
                        column_number=None,
                        category=None,
                        code=None,
                        timestamp=datetime.now()
                    )
        
        # Try note patterns
        for pattern in self.note_patterns:
            match = re.match(pattern, line)
            if match:
                if len(match.groups()) >= 4:
                    return XcodeDiagnostic(
                        severity='note',
                        message=match.group(4),
                        file_path=match.group(1),
                        line_number=int(match.group(2)),
                        column_number=int(match.group(3)),
                        category=None,
                        code=None,
                        timestamp=datetime.now()
                    )
                else:
                    return XcodeDiagnostic(
                        severity='note',
                        message=match.group(1),
                        file_path=None,
                        line_number=None,
                        column_number=None,
                        category=None,
                        code=None,
                        timestamp=datetime.now()
                    )
        
        return None
    
    def get_current_diagnostics(self, project_name: Optional[str] = None) -> List[XcodeDiagnostic]:
        """Get current diagnostics for the most recent build."""
        # First try to get live editor errors from Xcode console
        print("Debug: Attempting to get live editor errors...")
        live_editor_errors = self._get_live_editor_errors(project_name)
        if live_editor_errors:
            print(f"Debug: Found {len(live_editor_errors)} live editor errors")
            return live_editor_errors
        
        # Then try to get live build errors from xcodebuild
        print("Debug: Attempting live build diagnostics...")
        live_diagnostics = self._get_live_build_diagnostics(project_name)
        if live_diagnostics:
            print(f"Debug: Found {len(live_diagnostics)} live diagnostics")
            return live_diagnostics
        
        print("Debug: No live diagnostics found, trying log files...")
        # Fallback to parsing log files
        log_path = self.get_latest_build_log(project_name)
        if not log_path:
            print("Debug: No log files found")
            return []
        
        print(f"Debug: Found log file: {log_path}")
        result = self.parse_build_log(log_path)
        if not result:
            print("Debug: Could not parse log file")
            return []
        
        print(f"Debug: Parsed {len(result.diagnostics)} diagnostics from log file")
        return result.diagnostics
    
    def _get_live_editor_errors(self, project_name: Optional[str] = None) -> List[XcodeDiagnostic]:
        """Get live editor errors by monitoring Xcode's console output."""
        try:
            # Use log command to get recent Xcode diagnostics
            cmd = [
                'log', 'show', 
                '--predicate', 'process == "Xcode" OR process == "SourceKitService" OR process == "swift"',
                '--last', '5m',  # Last 5 minutes
                '--style', 'compact'
            ]
            
            print(f"Debug: Running log command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Debug: log command failed with return code {result.returncode}")
                print(f"Debug: stderr: {result.stderr}")
                return []
            
            print(f"Debug: Log output length: {len(result.stdout)}")
            
            # Parse the log output for error patterns
            diagnostics = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Look for error patterns in the log output
                diagnostic = self._parse_diagnostic_line(line)
                if diagnostic:
                    diagnostics.append(diagnostic)
            
            print(f"Debug: Found {len(diagnostics)} diagnostics in log output")
            return diagnostics
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"Live editor errors failed: {e}")
            return []
    
    def _get_live_build_diagnostics(self, project_name: Optional[str] = None) -> List[XcodeDiagnostic]:
        """Get live build diagnostics by running xcodebuild with live error checking."""
        try:
            # Find the most recent project if not specified
            if not project_name:
                recent_projects = self.find_recent_projects(1)
                if not recent_projects:
                    print("Debug: No recent projects found")
                    return []
                project_name = recent_projects[0]
                print(f"Debug: Using most recent project: {project_name}")
            
            # Look for .xcodeproj or .xcworkspace files in common locations
            project_path = self._find_project_file(project_name)
            if not project_path:
                print(f"Debug: Could not find project file for '{project_name}'")
                return []
            
            print(f"Debug: Found project file: {project_path}")
            
            # Run xcodebuild to get current build status
            cmd = ['xcodebuild', '-project', str(project_path), '-list']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Debug: xcodebuild -list failed with return code {result.returncode}")
                print(f"Debug: stderr: {result.stderr}")
                return []
            
            # Get available schemes
            schemes = self._extract_schemes_from_list(result.stdout)
            if not schemes:
                print("Debug: No schemes found")
                return []
            
            print(f"Debug: Found schemes: {schemes}")
            
            # Try to build with the first scheme to get current errors
            scheme = schemes[0]
            # Use -dry-run first to get syntax errors without full compilation
            build_cmd = [
                'xcodebuild', 
                '-project', str(project_path),
                '-scheme', scheme,
                '-configuration', 'Debug',
                '-dry-run'  # This will show syntax errors without full build
            ]
            
            print(f"Debug: Running dry-run command: {' '.join(build_cmd)}")
            
            build_result = subprocess.run(
                build_cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            print(f"Debug: Dry-run completed with return code: {build_result.returncode}")
            print(f"Debug: stdout length: {len(build_result.stdout)}")
            print(f"Debug: stderr length: {len(build_result.stderr)}")
            
            # Parse build output for diagnostics
            diagnostics = self._parse_build_output(build_result.stdout, build_result.stderr)
            print(f"Debug: Parsed {len(diagnostics)} diagnostics from dry-run output")
            
            # If dry-run didn't find errors, try a full build
            if not diagnostics:
                print("Debug: No errors from dry-run, trying full build...")
                build_cmd = [
                    'xcodebuild', 
                    '-project', str(project_path),
                    '-scheme', scheme,
                    '-configuration', 'Debug',
                    'build'
                ]
                
                build_result = subprocess.run(
                    build_cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=60
                )
                
                print(f"Debug: Full build completed with return code: {build_result.returncode}")
                diagnostics = self._parse_build_output(build_result.stdout, build_result.stderr)
                print(f"Debug: Parsed {len(diagnostics)} diagnostics from full build output")
            
            return diagnostics
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"Live build diagnostics failed: {e}")
            return []
    
    def _find_project_file(self, project_name: str) -> Optional[Path]:
        """Find the .xcodeproj or .xcworkspace file for a project using Spotlight."""
        try:
            # Search for .xcworkspace first
            command = [
                'mdfind',
                f"kMDItemKind == 'Xcode Workspace' && kMDItemDisplayName == '{project_name}.xcworkspace'"
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                # Take the first result
                workspace_path = result.stdout.strip().split('\n')[0]
                return Path(workspace_path)
            
            # If not found, search for .xcodeproj
            command = [
                'mdfind',
                f"kMDItemKind == 'Xcode Project' && kMDItemDisplayName == '{project_name}.xcodeproj'"
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                # Take the first result
                project_path = result.stdout.strip().split('\n')[0]
                return Path(project_path)

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"Error finding project using mdfind: {e}")
            # Fallback to the old method if mdfind fails
            return self._find_project_file_fallback(project_name)
        
        # Fallback if mdfind doesn't find anything
        return self._find_project_file_fallback(project_name)

    def _find_project_file_fallback(self, project_name: str) -> Optional[Path]:
        """Fallback method to find project files in common locations."""
        # Common locations to search
        search_paths = [
            Path.home() / "Desktop",
            Path.home() / "Documents", 
            Path.home() / "Developer",
            Path("/Users") / "Shared" / "Developer",
            Path.cwd()  # Current working directory
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            # Look for .xcodeproj files
            for proj_file in search_path.rglob(f"{project_name}.xcodeproj"):
                return proj_file
                
            # Look for .xcworkspace files
            for workspace_file in search_path.rglob(f"{project_name}.xcworkspace"):
                return workspace_file
        
        return None
    
    def _extract_schemes_from_list(self, list_output: str) -> List[str]:
        """Extract scheme names from xcodebuild -list output."""
        schemes = []
        in_schemes_section = False
        
        for line in list_output.split('\n'):
            line = line.strip()
            if 'Schemes:' in line:
                in_schemes_section = True
                continue
            elif in_schemes_section:
                if line and not line.startswith('Info:') and not line.startswith('Build'):
                    schemes.append(line)
                elif line.startswith('Info:') or line.startswith('Build'):
                    break
        
        return schemes
    
    def _parse_build_output(self, stdout: str, stderr: str) -> List[XcodeDiagnostic]:
        """Parse xcodebuild output for diagnostics."""
        diagnostics = []
        all_output = stdout + '\n' + stderr
        
        for line in all_output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            diagnostic = self._parse_diagnostic_line(line)
            if diagnostic:
                diagnostics.append(diagnostic)
        
        return diagnostics
    
    def watch_for_new_builds(self, callback):
        """Watch for new build logs and call callback when found."""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class BuildLogHandler(FileSystemEventHandler):
            def __init__(self, parser, callback):
                self.parser = parser
                self.callback = callback
            
            def on_created(self, event):
                if event.is_directory:
                    return
                
                if event.src_path.endswith('.xcactivitylog'):
                    # New build log created
                    log_path = Path(event.src_path)
                    result = self.parser.parse_build_log(log_path)
                    if result:
                        self.callback(result)
        
        observer = Observer()
        handler = BuildLogHandler(self, callback)
        
        # Watch all project directories for new logs
        for project_name in self.find_recent_projects():
            logs_path = self.derived_data_path / project_name / "Logs" / "Build"
            if logs_path.exists():
                observer.schedule(handler, str(logs_path), recursive=False)
        
        observer.start()
        return observer


def main():
    """Test the Xcode parser."""
    parser = XcodeLogParser()
    
    print("Recent Xcode projects:")
    projects = parser.find_recent_projects(5)
    for i, project in enumerate(projects):
        print(f"  {i+1}. {project}")
    
    print(f"\nDerivedData path: {parser.derived_data_path}")
    
    # Get diagnostics for the most recent project
    diagnostics = parser.get_current_diagnostics()
    print(f"\nFound {len(diagnostics)} diagnostics:")
    
    for diag in diagnostics:
        location = ""
        if diag.file_path and diag.line_number:
            location = f" at {diag.file_path}:{diag.line_number}"
            if diag.column_number:
                location += f":{diag.column_number}"
        
        print(f"  [{diag.severity.upper()}]{location}: {diag.message}")


if __name__ == "__main__":
    main()
