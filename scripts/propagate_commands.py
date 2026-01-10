#!/usr/bin/env python3
"""
Propagate updated command files from claude-family to all active projects.

This script reads command files from claude-family/.claude/commands/ and copies
them to all active projects registered in the database.

Usage:
    python scripts/propagate_commands.py [--dry-run] [--command session-end]
"""

import argparse
import os
import shutil
from pathlib import Path
import psycopg2
from urllib.parse import urlparse

def load_env_file():
    """Load .env file from current directory or script directory."""
    env_paths = [
        Path.cwd() / '.env',
        Path(__file__).parent.parent / '.env',
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
            return True
    return False

def get_db_connection():
    """Get database connection from environment."""
    load_env_file()
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # Default connection for local development
        db_url = "postgresql://postgres:postgres@localhost:5432/ai_company_foundation"

    parsed = urlparse(db_url)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],  # Remove leading /
        user=parsed.username,
        password=parsed.password
    )

def get_active_projects(conn):
    """Get all active projects with their paths."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT project_name, project_path
            FROM claude.workspaces
            WHERE is_active = true
              AND project_path IS NOT NULL
              AND project_path != ''
            ORDER BY project_name
        """)
        return cur.fetchall()

def propagate_command(source_dir: Path, projects: list, command_name: str, dry_run: bool = False):
    """Propagate a command file to all projects."""
    source_file = source_dir / f"{command_name}.md"

    if not source_file.exists():
        print(f"ERROR: Source file {source_file} does not exist")
        return

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Propagating {command_name}.md to {len(projects)} projects:\n")

    updated = 0
    skipped = 0
    errors = 0

    for project_name, project_path in projects:
        # Skip claude-family (source)
        if project_name == 'claude-family':
            print(f"  SKIP: {project_name} (source)")
            skipped += 1
            continue

        # Check if project path exists
        project_dir = Path(project_path)
        if not project_dir.exists():
            print(f"  SKIP: {project_name} - path not found: {project_path}")
            skipped += 1
            continue

        # Target directory
        target_dir = project_dir / ".claude" / "commands"
        target_file = target_dir / f"{command_name}.md"

        try:
            if not dry_run:
                # Create directory if needed
                target_dir.mkdir(parents=True, exist_ok=True)
                # Copy file
                shutil.copy2(source_file, target_file)

            print(f"  OK: {project_name}")
            updated += 1
        except Exception as e:
            print(f"  ERROR: {project_name} - {e}")
            errors += 1

    print(f"\nSummary: {updated} updated, {skipped} skipped, {errors} errors")

def main():
    parser = argparse.ArgumentParser(description='Propagate command files to all projects')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--command', default='session-end', help='Command file to propagate (without .md extension)')
    parser.add_argument('--all', action='store_true', help='Propagate all command files')
    args = parser.parse_args()

    # Source directory
    source_dir = Path(__file__).parent.parent / ".claude" / "commands"

    if not source_dir.exists():
        print(f"ERROR: Source directory {source_dir} does not exist")
        return 1

    try:
        conn = get_db_connection()
        projects = get_active_projects(conn)
        print(f"Found {len(projects)} active projects in database")

        if args.all:
            # Propagate all .md files
            for cmd_file in source_dir.glob("*.md"):
                propagate_command(source_dir, projects, cmd_file.stem, args.dry_run)
        else:
            propagate_command(source_dir, projects, args.command, args.dry_run)

        conn.close()
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
