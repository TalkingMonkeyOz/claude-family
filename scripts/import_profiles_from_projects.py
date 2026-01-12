#!/usr/bin/env python3
"""
Import Claude profiles from project files into database.

Reads CLAUDE.md and settings.local.json from each project
and creates/updates profiles in claude.profiles table.

Usage:
    python import_profiles_from_projects.py [--dry-run] [--project PROJECT_NAME]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

import psycopg2
from psycopg2.extras import Json

# Add scripts directory to path for config import
sys.path.insert(0, str(Path(__file__).parent))
from config import POSTGRES_CONFIG


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**POSTGRES_CONFIG)


def get_active_projects(conn, project_name: Optional[str] = None):
    """Get active projects with paths from database."""
    cursor = conn.cursor()
    if project_name:
        cursor.execute("""
            SELECT id, project_name, project_path, project_type
            FROM claude.workspaces
            WHERE is_active = true AND project_path IS NOT NULL
              AND project_name = %s
            ORDER BY project_name
        """, (project_name,))
    else:
        cursor.execute("""
            SELECT id, project_name, project_path, project_type
            FROM claude.workspaces
            WHERE is_active = true AND project_path IS NOT NULL
            ORDER BY project_name
        """)
    return cursor.fetchall()


def read_file_content(file_path: Path) -> Optional[str]:
    """Read file content or return None if file doesn't exist."""
    if not file_path.exists():
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


def parse_settings_json(content: str) -> dict:
    """Parse settings.local.json content into config dict."""
    try:
        settings = json.loads(content)
        config = {}

        # Extract MCPs
        if 'mcpServers' in settings:
            config['mcps'] = list(settings['mcpServers'].keys())

        # Extract hooks
        if 'hooks' in settings:
            config['hooks'] = settings['hooks']

        # Extract permissions
        if 'permissions' in settings:
            allowed_tools = []
            for key, value in settings.get('permissions', {}).items():
                if value is True:
                    allowed_tools.append(key)
            if allowed_tools:
                config['allowed_tools'] = allowed_tools

        return config
    except json.JSONDecodeError:
        return {}


def get_existing_profile(conn, project_name: str) -> Optional[dict]:
    """Get existing profile for a project."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT profile_id, name, config, current_version
        FROM claude.profiles
        WHERE name = %s
    """, (project_name,))
    row = cursor.fetchone()
    if row:
        return {
            'profile_id': row[0],
            'name': row[1],
            'config': row[2],
            'current_version': row[3]
        }
    return None


def create_profile(conn, project_name: str, workspace_id: int, config: dict, dry_run: bool) -> str:
    """Create a new profile."""
    profile_id = str(uuid.uuid4())

    if dry_run:
        print(f"  [DRY RUN] Would CREATE profile: {project_name}")
        return profile_id

    cursor = conn.cursor()

    # Insert profile
    cursor.execute("""
        INSERT INTO claude.profiles (profile_id, name, source_type, source_ref, config, current_version, is_active, is_favorite)
        VALUES (%s, %s, 'project', %s, %s, 1, true, false)
        RETURNING profile_id
    """, (profile_id, project_name, str(workspace_id), Json(config)))

    profile_id = cursor.fetchone()[0]

    # Create initial version
    cursor.execute("""
        INSERT INTO claude.profile_versions (version_id, profile_id, version, config, notes)
        VALUES (%s, %s, 1, %s, %s)
    """, (str(uuid.uuid4()), profile_id, Json(config), 'Initial import from project files'))

    conn.commit()
    return profile_id


def update_profile(conn, profile: dict, new_config: dict, dry_run: bool) -> int:
    """Update existing profile with new config."""
    new_version = profile['current_version'] + 1

    if dry_run:
        print(f"  [DRY RUN] Would UPDATE profile: {profile['name']} to version {new_version}")
        return new_version

    cursor = conn.cursor()

    # Update profile
    cursor.execute("""
        UPDATE claude.profiles
        SET config = %s, current_version = %s, updated_at = NOW()
        WHERE profile_id = %s
    """, (Json(new_config), new_version, profile['profile_id']))

    # Create version snapshot
    cursor.execute("""
        INSERT INTO claude.profile_versions (version_id, profile_id, version, config, notes)
        VALUES (%s, %s, %s, %s, %s)
    """, (str(uuid.uuid4()), profile['profile_id'], new_version, Json(new_config), 'Re-imported from project files'))

    conn.commit()
    return new_version


def import_project(conn, workspace_id: int, project_name: str, project_path: str,
                   project_type: str, dry_run: bool) -> dict:
    """
    Import a single project into profiles.

    Returns dict with status info.
    """
    result = {
        'project_name': project_name,
        'status': 'skipped',
        'details': ''
    }

    project_path = Path(project_path)
    if not project_path.exists():
        result['details'] = f'Project path does not exist: {project_path}'
        return result

    # Read CLAUDE.md
    claude_md_path = project_path / 'CLAUDE.md'
    claude_md_content = read_file_content(claude_md_path)

    if not claude_md_content:
        result['details'] = 'No CLAUDE.md file found'
        return result

    # Read settings.local.json
    settings_path = project_path / '.claude' / 'settings.local.json'
    settings_content = read_file_content(settings_path)
    settings_config = parse_settings_json(settings_content) if settings_content else {}

    # Build config
    config = {
        'behavior': claude_md_content,
        'description': f'{project_name} project configuration',
        **settings_config
    }

    # Check for existing profile
    existing = get_existing_profile(conn, project_name)

    if existing:
        # Check if content actually changed
        old_behavior = existing['config'].get('behavior', '') if existing['config'] else ''
        if old_behavior == claude_md_content:
            result['status'] = 'unchanged'
            result['details'] = f'Content unchanged (v{existing["current_version"]})'
            return result

        # Update existing profile
        new_version = update_profile(conn, existing, config, dry_run)
        result['status'] = 'updated'
        result['details'] = f'Updated to version {new_version}'
    else:
        # Create new profile
        profile_id = create_profile(conn, project_name, workspace_id, config, dry_run)
        result['status'] = 'created'
        result['details'] = f'Created profile {profile_id[:8]}...'

    return result


def main():
    parser = argparse.ArgumentParser(description='Import profiles from project files')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--project',
        type=str,
        help='Import only a specific project by name'
    )
    args = parser.parse_args()

    print("Import Profiles from Projects")
    print("=" * 60)
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
    print()

    # Connect to database
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)

    # Get projects
    projects = get_active_projects(conn, args.project)
    print(f"Found {len(projects)} project(s) to process")
    print()

    # Stats
    stats = {'created': 0, 'updated': 0, 'unchanged': 0, 'skipped': 0}

    for workspace_id, project_name, project_path, project_type in projects:
        print(f"Processing: {project_name}")

        result = import_project(
            conn, workspace_id, project_name, project_path,
            project_type, args.dry_run
        )

        stats[result['status']] += 1
        print(f"  {result['status'].upper()}: {result['details']}")
        print()

    # Summary
    print("Summary")
    print("-" * 40)
    print(f"Created: {stats['created']}")
    print(f"Updated: {stats['updated']}")
    print(f"Unchanged: {stats['unchanged']}")
    print(f"Skipped: {stats['skipped']}")

    if args.dry_run:
        print("\nThis was a dry run. Run without --dry-run to apply changes.")

    conn.close()


if __name__ == '__main__':
    main()
