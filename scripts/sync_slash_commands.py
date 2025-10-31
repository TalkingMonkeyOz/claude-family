#!/usr/bin/env python3
"""
Sync Slash Commands - Claude Family Infrastructure

Distributes updated slash commands from claude-family to all other project workspaces.
This ensures all Claude instances use the latest command versions.

Usage:
    python sync_slash_commands.py [--dry-run]

Options:
    --dry-run    Show what would be copied without actually copying
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Source: Master command files in claude-family
SOURCE_DIR = Path(r"C:\Projects\claude-family\.claude\commands")

# Targets: All other project workspaces
TARGET_WORKSPACES = [
    Path(r"C:\Projects\claude-pm\.claude\commands"),
    Path(r"C:\Projects\nimbus-user-loader\.claude\commands"),
    Path(r"C:\Projects\ATO-tax-agent\.claude\commands"),
]

def get_file_info(file_path):
    """Get file modification time and size for comparison."""
    if not file_path.exists():
        return None
    stat = file_path.stat()
    return {
        'mtime': datetime.fromtimestamp(stat.st_mtime),
        'size': stat.st_size
    }

def sync_commands(dry_run=False):
    """Sync all command files from source to target workspaces."""

    print("=" * 80)
    print("SLASH COMMAND SYNC - Claude Family Infrastructure")
    print("=" * 80)
    print()

    if dry_run:
        print("[DRY RUN] No files will be modified")
        print()

    # Check source directory exists
    if not SOURCE_DIR.exists():
        print(f"[ERROR] Source directory not found: {SOURCE_DIR}")
        return 1

    # Get all .md files in source
    source_files = list(SOURCE_DIR.glob("*.md"))

    if not source_files:
        print(f"[ERROR] No .md files found in {SOURCE_DIR}")
        return 1

    print(f"Source: {SOURCE_DIR}")
    print(f"Commands found: {len(source_files)}")
    for f in source_files:
        info = get_file_info(f)
        print(f"   - {f.name} ({info['size']} bytes, modified {info['mtime'].strftime('%Y-%m-%d %H:%M')})")
    print()

    # Sync to each target workspace
    total_copied = 0
    total_skipped = 0
    total_errors = 0

    for target_dir in TARGET_WORKSPACES:
        print(f"Target: {target_dir}")

        # Create target directory if it doesn't exist
        if not target_dir.exists():
            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                print(f"   [CREATED] Directory")
            else:
                print(f"   [DRY RUN] Would create directory")

        # Copy each source file
        for source_file in source_files:
            target_file = target_dir / source_file.name
            source_info = get_file_info(source_file)
            target_info = get_file_info(target_file)

            # Determine if copy is needed
            needs_copy = False
            reason = ""

            if target_info is None:
                needs_copy = True
                reason = "new file"
            elif source_info['size'] != target_info['size']:
                needs_copy = True
                reason = f"size changed ({target_info['size']} -> {source_info['size']} bytes)"
            elif source_info['mtime'] > target_info['mtime']:
                needs_copy = True
                reason = f"newer version ({target_info['mtime'].strftime('%Y-%m-%d %H:%M')} -> {source_info['mtime'].strftime('%Y-%m-%d %H:%M')})"
            else:
                reason = "up to date"

            if needs_copy:
                if not dry_run:
                    try:
                        shutil.copy2(source_file, target_file)
                        print(f"   [COPIED] {source_file.name} ({reason})")
                        total_copied += 1
                    except Exception as e:
                        print(f"   [ERROR] Copying {source_file.name}: {e}")
                        total_errors += 1
                else:
                    print(f"   [DRY RUN] Would copy: {source_file.name} ({reason})")
                    total_copied += 1
            else:
                print(f"   [SKIPPED] {source_file.name} ({reason})")
                total_skipped += 1

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Copied:  {total_copied} file(s)")
    print(f"Skipped: {total_skipped} file(s)")
    if total_errors > 0:
        print(f"Errors:  {total_errors} file(s)")
    print()

    if dry_run:
        print("[DRY RUN] This was a dry run. Run without --dry-run to actually sync files.")
    else:
        print("Sync complete! All workspaces now have the latest commands.")

    return 0 if total_errors == 0 else 1

if __name__ == "__main__":
    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv

    # Run sync
    exit_code = sync_commands(dry_run=dry_run)
    sys.exit(exit_code)
