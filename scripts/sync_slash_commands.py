#!/usr/bin/env python3
"""
Sync Slash Commands Distribution Script

Distributes slash commands from claude-family infrastructure repo to all active projects.
This ensures all Claude instances have access to the latest session workflow commands.

Usage:
    python scripts/sync_slash_commands.py [--dry-run]

Requirements:
    - workspaces.json must exist (run sync_workspaces.py first)
    - Source commands in .claude/commands/
    - Target projects must have .claude/commands/ directories

Author: Claude Family
Created: 2025-11-15
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
import argparse
import sys

# Configuration
WORKSPACE_FILE = Path("workspaces.json")
SOURCE_DIR = Path(".claude/commands")
SYNC_LOG_FILE = Path("logs/slash_command_sync.log")

# Commands to distribute (add new universal commands here)
UNIVERSAL_COMMANDS = [
    "session-start.md",
    "session-end.md", 
    "session-commit.md",
    # Add more universal commands here as they're created
]

class CommandSyncer:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.stats = {
            'synced': 0,
            'skipped': 0,
            'errors': 0,
            'projects': 0
        }
        self.log_entries = []
        
    def log(self, message, level="INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_entries.append(log_entry)
        # Use ASCII-safe output for Windows console
        print(log_entry.encode('ascii', 'replace').decode('ascii'))
    
    def load_workspaces(self):
        """Load workspace configuration"""
        if not WORKSPACE_FILE.exists():
            self.log("ERROR: workspaces.json not found. Run sync_workspaces.py first.", "ERROR")
            sys.exit(1)
            
        with open(WORKSPACE_FILE, 'r') as f:
            data = json.load(f)
            return data.get('workspaces', {})
    
    def sync_commands_to_project(self, project_name, project_info):
        """Sync commands to a single project"""
        project_path = Path(project_info['path'])
        target_dir = project_path / ".claude" / "commands"
        
        # Skip claude-family (source repo)
        if project_name == "claude-family":
            self.log(f"  Skipping {project_name} (source repository)", "INFO")
            self.stats['skipped'] += 1
            return
        
        # Create target directory if it doesn't exist
        if not self.dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.log(f"  [DRY-RUN] Would create {target_dir}", "INFO")
        
        # Copy each universal command
        commands_synced = 0
        for command in UNIVERSAL_COMMANDS:
            source_file = SOURCE_DIR / command
            target_file = target_dir / command
            
            if not source_file.exists():
                self.log(f"  WARNING: Source command not found: {command}", "WARN")
                continue
            
            try:
                if not self.dry_run:
                    shutil.copy2(source_file, target_file)
                    self.log(f"    ✓ Copied {command}", "INFO")
                else:
                    self.log(f"    [DRY-RUN] Would copy {command}", "INFO")
                
                commands_synced += 1
                self.stats['synced'] += 1
                
            except Exception as e:
                self.log(f"    ✗ Error copying {command}: {e}", "ERROR")
                self.stats['errors'] += 1
        
        if commands_synced > 0:
            self.stats['projects'] += 1
            self.log(f"  -> Synced {commands_synced} commands to {project_name}", "SUCCESS")
    
    def sync_all(self):
        """Sync commands to all projects"""
        self.log("=" * 80, "INFO")
        self.log("SLASH COMMAND SYNC STARTED", "INFO")
        self.log("=" * 80, "INFO")
        
        if self.dry_run:
            self.log("DRY RUN MODE - No files will be modified", "INFO")
        
        # Load workspaces
        workspaces = self.load_workspaces()
        self.log(f"Found {len(workspaces)} projects in workspaces.json", "INFO")
        self.log("", "INFO")
        
        # Verify source commands exist
        missing_commands = []
        for command in UNIVERSAL_COMMANDS:
            if not (SOURCE_DIR / command).exists():
                missing_commands.append(command)
        
        if missing_commands:
            self.log(f"WARNING: Missing source commands: {', '.join(missing_commands)}", "WARN")
            self.log("", "INFO")
        
        # Sync to each project
        for project_name, project_info in workspaces.items():
            self.log(f"Project: {project_name}", "INFO")
            self.sync_commands_to_project(project_name, project_info)
            self.log("", "INFO")
        
        # Summary
        self.log("=" * 80, "INFO")
        self.log("SYNC COMPLETE", "INFO")
        self.log("=" * 80, "INFO")
        self.log(f"Projects processed: {len(workspaces)}", "INFO")
        self.log(f"Projects updated: {self.stats['projects']}", "INFO")
        self.log(f"Commands synced: {self.stats['synced']}", "INFO")
        self.log(f"Commands skipped: {self.stats['skipped']}", "INFO")
        self.log(f"Errors: {self.stats['errors']}", "INFO")
        
        # Save log
        if not self.dry_run:
            self.save_log()
        
        return self.stats['errors'] == 0
    
    def save_log(self):
        """Save sync log to file"""
        SYNC_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(SYNC_LOG_FILE, 'a') as f:
            f.write('\n'.join(self.log_entries))
            f.write('\n\n')
        
        self.log(f"Log saved to: {SYNC_LOG_FILE}", "INFO")


def main():
    parser = argparse.ArgumentParser(
        description="Sync universal slash commands to all projects"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be synced without making changes'
    )
    
    args = parser.parse_args()
    
    syncer = CommandSyncer(dry_run=args.dry_run)
    success = syncer.sync_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
