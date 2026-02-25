#!/usr/bin/env python3
"""
Backup Claude configuration files from all projects.

Creates timestamped backups of:
- CLAUDE.md files
- .claude/settings.local.json files

Usage:
    python backup_claude_configs.py [--output-dir PATH]
"""

import os
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, CLAUDE_FAMILY_ROOT


def get_active_projects(conn):
    """Get all active projects with paths from database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, project_name, project_path
        FROM claude.workspaces
        WHERE is_active = true AND project_path IS NOT NULL
        ORDER BY project_name
    """)
    return cursor.fetchall()


def backup_file(source_path: Path, backup_dir: Path, project_name: str) -> bool:
    """
    Backup a single file.

    Returns True if file was backed up, False if source doesn't exist.
    """
    if not source_path.exists():
        return False

    # Create project backup directory
    project_backup_dir = backup_dir / project_name
    project_backup_dir.mkdir(parents=True, exist_ok=True)

    # Preserve directory structure
    relative_path = source_path.name
    if '.claude' in str(source_path):
        relative_path = f".claude/{source_path.name}"
        (project_backup_dir / '.claude').mkdir(exist_ok=True)

    dest_path = project_backup_dir / relative_path
    shutil.copy2(source_path, dest_path)
    return True


def backup_project(project_path: str, project_name: str, backup_dir: Path, log_file) -> dict:
    """
    Backup configuration files for a single project.

    Returns dict with counts of backed up files.
    """
    results = {'claude_md': False, 'settings': False}
    project_path = Path(project_path)

    if not project_path.exists():
        log_file.write(f"  SKIP: Project path does not exist: {project_path}\n")
        return results

    # Backup CLAUDE.md
    claude_md = project_path / 'CLAUDE.md'
    if backup_file(claude_md, backup_dir, project_name):
        results['claude_md'] = True
        log_file.write(f"  OK: {claude_md}\n")
    else:
        log_file.write(f"  SKIP: No CLAUDE.md in {project_path}\n")

    # Backup settings.local.json
    settings_file = project_path / '.claude' / 'settings.local.json'
    if backup_file(settings_file, backup_dir, project_name):
        results['settings'] = True
        log_file.write(f"  OK: {settings_file}\n")
    else:
        log_file.write(f"  SKIP: No settings.local.json in {project_path}\n")

    return results


def main():
    parser = argparse.ArgumentParser(description='Backup Claude configuration files')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=CLAUDE_FAMILY_ROOT / 'backups',
        help='Directory to store backups (default: claude-family/backups)'
    )
    args = parser.parse_args()

    # Create timestamped backup directory
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_dir = args.output_dir / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create log file
    log_path = backup_dir / 'backup.log'

    print(f"Backup directory: {backup_dir}")
    print(f"Log file: {log_path}")
    print()

    # Connect to database
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)

    # Get projects
    projects = get_active_projects(conn)
    print(f"Found {len(projects)} active projects with paths")
    print()

    # Stats
    total_claude_md = 0
    total_settings = 0
    skipped = 0

    with open(log_path, 'w', encoding='utf-8') as log_file:
        log_file.write(f"Claude Config Backup - {timestamp}\n")
        log_file.write("=" * 60 + "\n\n")

        for workspace_id, project_name, project_path in projects:
            print(f"Backing up: {project_name}")
            log_file.write(f"Project: {project_name}\n")
            log_file.write(f"Path: {project_path}\n")

            results = backup_project(project_path, project_name, backup_dir, log_file)

            if results['claude_md']:
                total_claude_md += 1
            if results['settings']:
                total_settings += 1
            if not results['claude_md'] and not results['settings']:
                skipped += 1

            log_file.write("\n")

        # Summary
        summary = f"""
Summary
-------
Total projects: {len(projects)}
CLAUDE.md backed up: {total_claude_md}
settings.local.json backed up: {total_settings}
Projects skipped (no files): {skipped}
Backup location: {backup_dir}
"""
        log_file.write(summary)
        print(summary)

    conn.close()
    print(f"\nBackup complete. Check {log_path} for details.")


if __name__ == '__main__':
    main()
