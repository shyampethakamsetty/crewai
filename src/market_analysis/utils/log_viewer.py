import os
import glob
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import re

class LogAnalyzer:
    """Advanced log analyzer for CrewAI run logs."""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
    
    def list_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent log files with metadata."""
        if not self.log_dir.exists():
            print(f"Log directory '{self.log_dir}' does not exist.")
            return []
        
        log_files = list(self.log_dir.glob("crewai_run_*.log"))
        log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        print(f"Recent CrewAI run logs (showing up to {limit}):")
        print("-" * 80)
        
        log_info = []
        for i, log_file in enumerate(log_files[:limit]):
            stat = log_file.stat()
            timestamp = datetime.fromtimestamp(stat.st_mtime)
            size_mb = stat.st_size / (1024 * 1024)
            
            # Extract run info from filename
            run_info = self._extract_run_info(log_file)
            
            print(f"{i+1:2d}. {log_file.name}")
            print(f"     Created: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Size: {size_mb:.2f} MB")
            if run_info:
                print(f"     Duration: {run_info.get('duration', 'Unknown')}")
                print(f"     Status: {run_info.get('status', 'Unknown')}")
            print()
            
            log_info.append({
                'file': str(log_file),
                'name': log_file.name,
                'timestamp': timestamp,
                'size_mb': size_mb,
                'run_info': run_info
            })
        
        return log_info
    
    def _extract_run_info(self, log_file: Path) -> Dict[str, Any]:
        """Extract run information from log file."""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            info = {}
            
            # Check for start and end timestamps
            start_match = re.search(r'CREWAI RUN STARTED.*?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', content)
            end_match = re.search(r'CREWAI RUN COMPLETED', content)
            
            if start_match:
                start_time = datetime.fromisoformat(start_match.group(1))
                info['start_time'] = start_time
                
                if end_match:
                    # Find the timestamp near the end
                    end_time_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', content[-5000:])
                    if end_time_match:
                        end_time = datetime.fromisoformat(end_time_match.group(1))
                        duration = end_time - start_time
                        info['duration'] = str(duration).split('.')[0]  # Remove microseconds
                        info['status'] = 'Completed'
                    else:
                        info['status'] = 'In Progress'
                else:
                    info['status'] = 'Incomplete'
            
            # Count agent activities
            agent_activities = len(re.findall(r'AGENT \[.*?\]:', content))
            info['agent_activities'] = agent_activities
            
            # Count tool executions
            tool_executions = len(re.findall(r'TOOL \[.*?\] EXECUTED:', content))
            info['tool_executions'] = tool_executions
            
            # Check for errors
            errors = len(re.findall(r'ERROR', content))
            info['errors'] = errors
            
            return info
            
        except Exception:
            return {}
    
    def view_log_content(self, log_file: str, lines: int = 50, search_term: str = None):
        """View the content of a specific log file with optional search."""
        log_path = Path(log_file)
        if not log_path.exists():
            print(f"Log file '{log_file}' does not exist.")
            return
        
        print(f"Viewing log: {log_path.name}")
        print("=" * 80)
        
        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            
            if search_term:
                # Filter lines containing search term
                matching_lines = [(i+1, line) for i, line in enumerate(all_lines) 
                                if search_term.lower() in line.lower()]
                
                if matching_lines:
                    print(f"Found {len(matching_lines)} lines containing '{search_term}':")
                    print("-" * 40)
                    for line_num, line in matching_lines[-lines:]:
                        print(f"{line_num:4d}: {line.rstrip()}")
                else:
                    print(f"No lines found containing '{search_term}'")
            else:
                # Show last N lines
                start_line = max(0, len(all_lines) - lines)
                for i, line in enumerate(all_lines[start_line:], start_line + 1):
                    print(f"{i:4d}: {line.rstrip()}")
    
    def search_logs(self, search_term: str, limit: int = 10):
        """Search for a term across all log files."""
        if not self.log_dir.exists():
            print(f"Log directory '{self.log_dir}' does not exist.")
            return
        
        log_files = list(self.log_dir.glob("crewai_run_*.log"))
        log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        print(f"Searching for '{search_term}' in {len(log_files)} log files...")
        print("=" * 80)
        
        results = []
        for log_file in log_files:
            found_lines = []
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if search_term.lower() in line.lower():
                        found_lines.append((line_num, line.strip()))
            
            if found_lines:
                results.append((log_file, found_lines))
        
        # Display results
        for log_file, found_lines in results[:limit]:
            print(f"\n📄 {log_file.name}:")
            for line_num, line in found_lines[-5:]:  # Show last 5 matches per file
                print(f"  Line {line_num}: {line}")
    
    def analyze_log(self, log_file: str):
        """Perform detailed analysis of a log file."""
        log_path = Path(log_file)
        if not log_path.exists():
            print(f"Log file '{log_file}' does not exist.")
            return
        
        print(f"Analyzing log: {log_path.name}")
        print("=" * 80)
        
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Basic statistics
        lines = content.split('\n')
        total_lines = len(lines)
        
        # Extract information
        run_info = self._extract_run_info(log_path)
        
        print(f"Total lines: {total_lines}")
        print(f"File size: {log_path.stat().st_size / 1024:.1f} KB")
        
        if run_info:
            print(f"Run status: {run_info.get('status', 'Unknown')}")
            if 'duration' in run_info:
                print(f"Duration: {run_info['duration']}")
            print(f"Agent activities: {run_info.get('agent_activities', 0)}")
            print(f"Tool executions: {run_info.get('tool_executions', 0)}")
            print(f"Errors: {run_info.get('errors', 0)}")
        
        # Find key sections
        sections = {
            'Configuration': len(re.findall(r'CONFIGURATION:', content)),
            'Agent Activities': len(re.findall(r'AGENT \[.*?\]:', content)),
            'Tool Executions': len(re.findall(r'TOOL \[.*?\] EXECUTED:', content)),
            'Errors': len(re.findall(r'ERROR', content)),
            'Warnings': len(re.findall(r'WARNING', content)),
        }
        
        print("\nKey sections found:")
        for section, count in sections.items():
            print(f"  {section}: {count}")

def main():
    """Main function for log viewer CLI."""
    import sys
    
    analyzer = LogAnalyzer()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            analyzer.list_recent_logs(limit)
            
        elif command == "view" and len(sys.argv) > 2:
            log_file = sys.argv[2]
            lines = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            search_term = sys.argv[4] if len(sys.argv) > 4 else None
            analyzer.view_log_content(log_file, lines, search_term)
            
        elif command == "search" and len(sys.argv) > 2:
            search_term = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            analyzer.search_logs(search_term, limit)
            
        elif command == "analyze" and len(sys.argv) > 2:
            log_file = sys.argv[2]
            analyzer.analyze_log(log_file)
            
        else:
            print("Usage:")
            print("  python log_viewer.py list [limit]")
            print("  python log_viewer.py view <log_file> [lines] [search_term]")
            print("  python log_viewer.py search <term> [limit]")
            print("  python log_viewer.py analyze <log_file>")
    else:
        analyzer.list_recent_logs()

if __name__ == "__main__":
    main() 