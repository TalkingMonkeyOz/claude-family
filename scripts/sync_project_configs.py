#!/usr/bin/env python3
"""
Unified Project Configuration Sync Script

Distributes slash commands, hooks, and validation scripts from claude-family
infrastructure repo to all active projects. Ensures consistent governance
across all Claude Family projects.

Usage:
    python scripts/sync_project_configs.py [--dry-run] [--commands-only] [--hooks-only]

Requirements:
    - workspaces.json must exist (run sync_workspaces.py first)
    - Source files in .claude/commands/, .claude/hooks.json
    - Target projects in workspaces.json

Author: Claude Family
Created: 2025-12-07
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
import argparse
import sys

# Configuration
WORKSPACE_FILE = Path("workspaces.json")
SOURCE_COMMANDS_DIR = Path(".claude/commands")
SOURCE_HOOKS_FILE = Path(".claude/hooks.json")
SOURCE_PLUGINS_DIR = Path(".claude-plugins/claude-family-core")
SYNC_LOG_FILE = Path("logs/project_config_sync.log")

# Commands to distribute universally
UNIVERSAL_COMMANDS = [
    "session-start.md",
    "session-end.md",
    "session-commit.md",
    "session-resume.md",
    "inbox-check.md",
    "broadcast.md",
    "team-status.md",
    "feedback-check.md",
]

# Validation scripts to distribute
VALIDATION_SCRIPTS = [
    "scripts/session_startup_hook.py",
    "scripts/session_end_hook.py",
    "scripts/validate_db_write.py",
    "scripts/validate_phase.py",
    "scripts/check_doc_updates.py",
]


class ConfigSyncer:
    def __init__(self, dry_run=False, commands_only=False, hooks_only=False):
        self.dry_run = dry_run
        self.commands_only = commands_only
        self.hooks_only = hooks_only
        self.stats = {
            'commands_synced': 0,
            'hooks_synced': 0,
            'scripts_synced': 0,
            'projects_updated': 0,
            'skipped': 0,
            'errors': 0,
        }
        self.log_entries = []
        self.issues = []

    def log(self, message, level="INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_entries.append(log_entry)
        print(log_entry)

    def load_workspaces(self):
        """Load workspace configuration"""
        if not WORKSPACE_FILE.exists():
            self.log("ERROR: workspaces.json not found. Run sync_workspaces.py first.", "ERROR")
            sys.exit(1)

        with open(WORKSPACE_FILE, 'r') as f:
            data = json.load(f)
            return data.get('workspaces', {})

    def sync_commands(self, project_path: Path, project_name: str):
        """Sync slash commands to a project"""
        target_dir = project_path / ".claude" / "commands"

        if not self.dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        synced = 0
        for command in UNIVERSAL_COMMANDS:
            source_file = SOURCE_COMMANDS_DIR / command
            target_file = target_dir / command

            if not source_file.exists():
                self.log(f"    WARN: Source not found: {command}", "WARN")
                continue

            try:
                if not self.dry_run:
                    shutil.copy2(source_file, target_file)
                synced += 1
                self.stats['commands_synced'] += 1
            except Exception as e:
                self.log(f"    ERROR copying {command}: {e}", "ERROR")
                self.stats['errors'] += 1
                self.issues.append(f"{project_name}: Failed to copy {command}")

        if synced > 0:
            self.log(f"    Commands: {synced} synced", "INFO")
        return synced

    def sync_hooks(self, project_path: Path, project_name: str):
        """Sync hooks.json to a project (merge, don't overwrite)"""
        target_file = project_path / ".claude" / "hooks.json"

        if not SOURCE_HOOKS_FILE.exists():
            self.log("    WARN: Source hooks.json not found", "WARN")
            return 0

        try:
            # Load source hooks
            with open(SOURCE_HOOKS_FILE, 'r') as f:
                source_hooks = json.load(f)

            # Check if target exists
            if target_file.exists():
                with open(target_file, 'r') as f:
                    target_hooks = json.load(f)

                # Merge: source takes precedence for matching keys
                merged = {**target_hooks, **source_hooks}

                if merged == target_hooks:
                    self.log(f"    Hooks: Already up to date", "INFO")
                    return 0
            else:
                merged = source_hooks

            if not self.dry_run:
                target_file.parent.mkdir(parents=True, exist_ok=True)
                with open(target_file, 'w') as f:
                    json.dump(merged, f, indent=2)

            self.stats['hooks_synced'] += 1
            self.log(f"    Hooks: Updated", "INFO")
            return 1

        except json.JSONDecodeError as e:
            self.log(f"    ERROR: Invalid JSON in hooks: {e}", "ERROR")
            self.stats['errors'] += 1
            self.issues.append(f"{project_name}: Invalid hooks.json")
            return 0
        except Exception as e:
            self.log(f"    ERROR syncing hooks: {e}", "ERROR")
            self.stats['errors'] += 1
            return 0

    def sync_validation_scripts(self, project_path: Path, project_name: str):
        """Sync validation scripts to project's plugin directory"""
        target_dir = project_path / ".claude-plugins" / "claude-family-core"

        if not self.dry_run:
            (target_dir / "scripts").mkdir(parents=True, exist_ok=True)

        synced = 0
        for script in VALIDATION_SCRIPTS:
            source_file = SOURCE_PLUGINS_DIR / script
            target_file = target_dir / script

            if not source_file.exists():
                continue

            try:
                if not self.dry_run:
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, target_file)
                synced += 1
                self.stats['scripts_synced'] += 1
            except Exception as e:
                self.log(f"    ERROR copying {script}: {e}", "ERROR")
                self.stats['errors'] += 1

        if synced > 0:
            self.log(f"    Scripts: {synced} synced", "INFO")
        return synced

    def validate_project_settings(self, project_path: Path, project_name: str):
        """Validate settings.local.json has correct paths"""
        settings_file = project_path / ".claude" / "settings.local.json"

        if not settings_file.exists():
            self.issues.append(f"{project_name}: Missing settings.local.json")
            return

        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)

            # Check for path case issues
            settings_str = json.dumps(settings)
            if project_name in settings_str:
                # Path should match exactly
                pass
            elif project_name.lower() in settings_str.lower():
                self.issues.append(f"{project_name}: Path case mismatch in settings.local.json")

        except json.JSONDecodeError:
            self.issues.append(f"{project_name}: Invalid JSON in settings.local.json")
        except Exception as e:
            self.issues.append(f"{project_name}: Error reading settings: {e}")

    def sync_to_project(self, project_name: str, project_info: dict):
        """Sync all configs to a single project"""
        project_path = Path(project_info['path'])

        # Skip source repo
        if project_name == "claude-family":
            self.log(f"  Skipping {project_name} (source repository)", "INFO")
            self.stats['skipped'] += 1
            return

        if not project_path.exists():
            self.log(f"  Skipping {project_name} (path not found: {project_path})", "WARN")
            self.stats['skipped'] += 1
            return

        self.log(f"  {project_name}:", "INFO")

        updated = False

        if not self.hooks_only:
            if self.sync_commands(project_path, project_name) > 0:
                updated = True

        if not self.commands_only:
            if self.sync_hooks(project_path, project_name) > 0:
                updated = True
            if self.sync_validation_scripts(project_path, project_name) > 0:
                updated = True

        # Always validate
        self.validate_project_settings(project_path, project_name)

        if updated:
            self.stats['projects_updated'] += 1

    def sync_all(self):
        """Sync to all projects"""
        self.log("=" * 70, "INFO")
        self.log("PROJECT CONFIGURATION SYNC", "INFO")
        self.log("=" * 70, "INFO")

        if self.dry_run:
            self.log("DRY RUN MODE - No files will be modified", "INFO")

        mode = "all configs"
        if self.commands_only:
            mode = "commands only"
        elif self.hooks_only:
            mode = "hooks only"
        self.log(f"Mode: {mode}", "INFO")
        self.log("", "INFO")

        workspaces = self.load_workspaces()
        self.log(f"Found {len(workspaces)} projects", "INFO")
        self.log("", "INFO")

        for project_name, project_info in workspaces.items():
            self.sync_to_project(project_name, project_info)
            self.log("", "INFO")

        # Summary
        self.log("=" * 70, "INFO")
        self.log("SYNC COMPLETE", "INFO")
        self.log("=" * 70, "INFO")
        self.log(f"Projects updated: {self.stats['projects_updated']}", "INFO")
        self.log(f"Commands synced:  {self.stats['commands_synced']}", "INFO")
        self.log(f"Hooks synced:     {self.stats['hooks_synced']}", "INFO")
        self.log(f"Scripts synced:   {self.stats['scripts_synced']}", "INFO")
        self.log(f"Skipped:          {self.stats['skipped']}", "INFO")
        self.log(f"Errors:           {self.stats['errors']}", "INFO")

        if self.issues:
            self.log("", "INFO")
            self.log("ISSUES FOUND:", "WARN")
            for issue in self.issues:
                self.log(f"  - {issue}", "WARN")

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
        description="Sync project configurations (commands, hooks, scripts) to all projects"
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be synced without making changes')
    parser.add_argument('--commands-only', action='store_true',
                        help='Only sync slash commands')
    parser.add_argument('--hooks-only', action='store_true',
                        help='Only sync hooks and validation scripts')

    args = parser.parse_args()

    if args.commands_only and args.hooks_only:
        print("ERROR: Cannot specify both --commands-only and --hooks-only")
        sys.exit(1)

    syncer = ConfigSyncer(
        dry_run=args.dry_run,
        commands_only=args.commands_only,
        hooks_only=args.hooks_only
    )
    success = syncer.sync_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
