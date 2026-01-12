#!/usr/bin/env python3
"""
Unified Component Deployment System

Deploys all configuration components from database to file system:
- CLAUDE.md files (from profiles)
- Skills (from skills table)
- Instructions (from instructions table)
- Rules (from rules table)
- Commands (from shared_commands table)
- Standards (from coding_standards table)

Follows ADR-006: Database is source of truth, files are generated.

Usage:
    python scripts/deploy_components.py [project_name] [--import] [--dry-run]

    project_name: Deploy for specific project (default: current directory)
    --import: Import files to database instead of deploying
    --dry-run: Show what would be done without making changes
    --force: Deploy even if hashes match
    --component-type: Only deploy specific type (claude_md, skill, etc.)

Author: Claude Family
Date: 2026-01-12
"""

import json
import os
import sys
import logging
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import psycopg (v3) or psycopg2
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_VERSION = 3
except ImportError:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG_VERSION = 2

# Constants
GLOBAL_CLAUDE_DIR = Path.home() / ".claude"

# Database connection - try pgpass file first, then env var, then default
def _get_pg_config():
    """Read PostgreSQL config from pgpass file or Windows AppData."""
    # Try Unix-style pgpass
    pgpass_locations = [
        Path.home() / ".pgpass",
        Path.home() / "AppData" / "Roaming" / "postgresql" / "pgpass.conf"
    ]

    for pgpass_path in pgpass_locations:
        if pgpass_path.exists():
            try:
                content = pgpass_path.read_text()
                for line in content.strip().split('\n'):
                    if 'ai_company_foundation' in line:
                        parts = line.split(':')
                        if len(parts) >= 5:
                            return {
                                'host': parts[0],
                                'port': parts[1] or '5432',
                                'database': parts[2],
                                'user': parts[3],
                                'password': parts[4]
                            }
            except Exception:
                pass

    # Default config matching other scripts in this project
    return {
        'host': 'localhost',
        'port': '5432',
        'database': 'ai_company_foundation',
        'user': 'postgres',
        'password': '05OX79HNFCjQwhotDjVx'  # Standard dev password
    }

_PG_CONFIG = _get_pg_config()
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}:{_PG_CONFIG['port']}/{_PG_CONFIG['database']}"
)


def get_db_connection():
    """Get database connection."""
    if PSYCOPG_VERSION == 3:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    else:
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = RealDictCursor
        return conn


def calculate_hash(content: str) -> str:
    """Calculate SHA256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def get_project_info(conn, project_name: str) -> Optional[Dict]:
    """Get project information from workspaces table."""
    cur = conn.cursor()
    cur.execute("""
        SELECT project_id, project_name, project_path, project_type
        FROM claude.workspaces
        WHERE project_name = %s AND is_active = true
    """, (project_name,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_deployable_components(conn, project_name: str, component_type: str = None) -> List[Dict]:
    """Get all deployable components for a project with scope inheritance."""
    cur = conn.cursor()

    # Get project info
    project = get_project_info(conn, project_name)
    if not project:
        logger.warning(f"Project {project_name} not found in workspaces")
        return []

    project_id = project['project_id']
    project_type = project['project_type']

    query = """
        SELECT
            component_type,
            component_id,
            component_name,
            scope,
            scope_ref,
            content,
            applies_to,
            sub_type,
            version,
            is_active,
            updated_at
        FROM claude.deployable_components
        WHERE is_active = true
          AND (
              scope = 'global'
              OR (scope = 'project_type' AND scope_ref = %s)
              OR (scope = 'project' AND (scope_ref = %s OR scope_ref = %s))
          )
    """
    params = [project_type, project_name, str(project_id) if project_id else '']

    if component_type:
        query += " AND component_type = %s"
        params.append(component_type)

    query += " ORDER BY component_type, component_name"

    cur.execute(query, params)
    return [dict(row) for row in cur.fetchall()]


def get_target_path(component: Dict, project_path: str) -> Path:
    """Calculate deployment target path based on component type and scope."""
    comp_type = component['component_type']
    name = component['component_name']
    scope = component['scope']
    sub_type = component.get('sub_type')

    project_path = Path(project_path) if project_path else None

    # Global components go to ~/.claude/
    if scope == 'global':
        if comp_type == 'instruction':
            return GLOBAL_CLAUDE_DIR / "instructions" / f"{name}.instructions.md"
        elif comp_type == 'standard':
            category = sub_type or 'misc'
            return GLOBAL_CLAUDE_DIR / "standards" / category / f"{name}.md"
        elif comp_type == 'command':
            return GLOBAL_CLAUDE_DIR / "commands" / f"{name}.md"
        elif comp_type == 'skill':
            # Global skills don't have a standard file location
            # They're typically in project directories
            return None

    # Project-scoped components go to project/.claude/
    if project_path:
        if comp_type == 'claude_md':
            return project_path / "CLAUDE.md"
        elif comp_type == 'skill':
            return project_path / ".claude" / "skills" / name / "skill.md"
        elif comp_type == 'rule':
            return project_path / ".claude" / "rules" / f"{name}.md"
        elif comp_type == 'command':
            return project_path / ".claude" / "commands" / f"{name}.md"
        elif comp_type == 'instruction':
            return project_path / ".claude" / "instructions" / f"{name}.instructions.md"

    return None


def get_deployment_tracking(conn, component_type: str, component_id: str) -> Optional[Dict]:
    """Get deployment tracking record for a component."""
    cur = conn.cursor()
    cur.execute("""
        SELECT tracking_id, content_hash, file_hash, last_deployed_at, status
        FROM claude.deployment_tracking
        WHERE component_type = %s AND component_id = %s
    """, (component_type, component_id))
    row = cur.fetchone()
    return dict(row) if row else None


def update_deployment_tracking(conn, component: Dict, target_path: Path, content_hash: str, status: str = 'deployed'):
    """Update or create deployment tracking record."""
    cur = conn.cursor()

    # Check if tracking exists
    cur.execute("""
        SELECT tracking_id FROM claude.deployment_tracking
        WHERE component_type = %s AND component_id = %s
    """, (component['component_type'], str(component['component_id'])))

    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE claude.deployment_tracking
            SET target_path = %s,
                content_hash = %s,
                file_hash = %s,
                last_deployed_at = NOW(),
                status = %s,
                deployed_by = 'deploy_components.py',
                updated_at = NOW()
            WHERE component_type = %s AND component_id = %s
        """, (
            str(target_path),
            content_hash,
            content_hash,  # file_hash = content_hash after deploy
            status,
            component['component_type'],
            str(component['component_id'])
        ))
    else:
        cur.execute("""
            INSERT INTO claude.deployment_tracking (
                component_type, component_id, component_name,
                target_path, scope, scope_ref,
                content_hash, file_hash, last_deployed_at,
                status, deployed_by, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, 'deploy_components.py', NOW(), NOW()
            )
        """, (
            component['component_type'],
            str(component['component_id']),
            component['component_name'],
            str(target_path),
            component['scope'],
            component.get('scope_ref'),
            content_hash,
            content_hash,
            status
        ))

    conn.commit()


def deploy_component(component: Dict, target_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """Deploy a single component to file system."""
    content = component['content']

    if not content:
        return False, "No content to deploy"

    if dry_run:
        return True, f"Would deploy to {target_path}"

    # Create parent directories
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    try:
        target_path.write_text(content, encoding='utf-8')
        return True, f"Deployed to {target_path}"
    except Exception as e:
        return False, f"Failed to deploy: {e}"


def check_sync_status(component: Dict, target_path: Path, tracking: Optional[Dict]) -> str:
    """Check sync status between database and file."""
    content = component['content']
    content_hash = calculate_hash(content) if content else None

    if not target_path or not target_path.exists():
        return 'file_missing'

    try:
        file_content = target_path.read_text(encoding='utf-8')
        file_hash = calculate_hash(file_content)
    except Exception:
        return 'file_error'

    if content_hash == file_hash:
        return 'in_sync'

    # Check if local file changed vs last deployment
    if tracking and tracking.get('file_hash'):
        if file_hash != tracking['file_hash']:
            return 'local_change'

    return 'db_change'


def deploy_for_project(project_name: str, component_type: str = None,
                       dry_run: bool = False, force: bool = False) -> Dict:
    """Deploy all components for a project."""
    results = {
        'project': project_name,
        'deployed': [],
        'skipped': [],
        'errors': [],
        'conflicts': []
    }

    conn = get_db_connection()
    try:
        project = get_project_info(conn, project_name)
        if not project:
            results['errors'].append(f"Project {project_name} not found")
            return results

        project_path = project['project_path']
        components = get_deployable_components(conn, project_name, component_type)

        logger.info(f"Found {len(components)} components for {project_name}")

        for component in components:
            comp_type = component['component_type']
            comp_name = component['component_name']

            target_path = get_target_path(component, project_path)
            if not target_path:
                results['skipped'].append({
                    'type': comp_type,
                    'name': comp_name,
                    'reason': 'No target path'
                })
                continue

            tracking = get_deployment_tracking(conn, comp_type, str(component['component_id']))
            status = check_sync_status(component, target_path, tracking)

            if status == 'local_change' and not force:
                results['conflicts'].append({
                    'type': comp_type,
                    'name': comp_name,
                    'path': str(target_path),
                    'status': status
                })
                continue

            if status == 'in_sync' and not force:
                results['skipped'].append({
                    'type': comp_type,
                    'name': comp_name,
                    'reason': 'Already in sync'
                })
                continue

            # Deploy
            success, message = deploy_component(component, target_path, dry_run)

            if success:
                content_hash = calculate_hash(component['content']) if component['content'] else None
                if not dry_run and content_hash:
                    update_deployment_tracking(conn, component, target_path, content_hash)

                results['deployed'].append({
                    'type': comp_type,
                    'name': comp_name,
                    'path': str(target_path),
                    'message': message
                })
            else:
                results['errors'].append({
                    'type': comp_type,
                    'name': comp_name,
                    'error': message
                })

        return results

    finally:
        conn.close()


def import_commands_from_files(dry_run: bool = False) -> Dict:
    """Import command files to shared_commands table."""
    results = {
        'imported': [],
        'skipped': [],
        'errors': []
    }

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Import global commands
        global_commands_dir = GLOBAL_CLAUDE_DIR / "commands"
        if global_commands_dir.exists():
            for cmd_file in global_commands_dir.glob("*.md"):
                name = cmd_file.stem
                content = cmd_file.read_text(encoding='utf-8')

                # Extract description from first non-empty line after title
                lines = content.split('\n')
                description = None
                for line in lines[1:]:  # Skip title
                    line = line.strip()
                    if line and not line.startswith('#'):
                        description = line[:200]  # First 200 chars
                        break

                if dry_run:
                    results['imported'].append({
                        'name': name,
                        'scope': 'global',
                        'path': str(cmd_file)
                    })
                    continue

                # Check if exists
                cur.execute("""
                    SELECT command_id FROM claude.shared_commands
                    WHERE command_name = %s AND scope = 'global'
                """, (name,))

                if cur.fetchone():
                    # Update
                    cur.execute("""
                        UPDATE claude.shared_commands
                        SET content = %s, description = %s, filename = %s, updated_at = NOW()
                        WHERE command_name = %s AND scope = 'global'
                    """, (content, description, cmd_file.name, name))
                else:
                    # Insert
                    cur.execute("""
                        INSERT INTO claude.shared_commands
                        (command_name, filename, description, content, is_core, scope, version, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, true, 'global', 1, NOW(), NOW())
                    """, (name, cmd_file.name, description, content))

                results['imported'].append({
                    'name': name,
                    'scope': 'global',
                    'path': str(cmd_file)
                })

        # Import project commands from all workspaces
        cur.execute("""
            SELECT project_id, project_name, project_path
            FROM claude.workspaces
            WHERE is_active = true AND project_path IS NOT NULL
        """)

        for workspace in cur.fetchall():
            workspace = dict(workspace)
            project_path = Path(workspace['project_path'])
            commands_dir = project_path / ".claude" / "commands"

            if not commands_dir.exists():
                continue

            for cmd_file in commands_dir.glob("*.md"):
                name = cmd_file.stem
                content = cmd_file.read_text(encoding='utf-8')

                # Extract description
                lines = content.split('\n')
                description = None
                for line in lines[1:]:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        description = line[:200]
                        break

                project_id = workspace['project_id']

                if dry_run:
                    results['imported'].append({
                        'name': name,
                        'scope': 'project',
                        'project': workspace['project_name'],
                        'path': str(cmd_file)
                    })
                    continue

                # Check if exists
                cur.execute("""
                    SELECT command_id FROM claude.shared_commands
                    WHERE command_name = %s AND scope = 'project' AND scope_ref = %s
                """, (name, str(project_id) if project_id else workspace['project_name']))

                if cur.fetchone():
                    # Update
                    cur.execute("""
                        UPDATE claude.shared_commands
                        SET content = %s, description = %s, filename = %s, updated_at = NOW()
                        WHERE command_name = %s AND scope = 'project' AND scope_ref = %s
                    """, (content, description, cmd_file.name, name,
                          str(project_id) if project_id else workspace['project_name']))
                else:
                    # Insert
                    cur.execute("""
                        INSERT INTO claude.shared_commands
                        (command_name, filename, description, content, is_core, scope, scope_ref, version, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, false, 'project', %s, 1, NOW(), NOW())
                    """, (name, cmd_file.name, description, content,
                          str(project_id) if project_id else workspace['project_name']))

                results['imported'].append({
                    'name': name,
                    'scope': 'project',
                    'project': workspace['project_name'],
                    'path': str(cmd_file)
                })

        if not dry_run:
            conn.commit()

        return results

    except Exception as e:
        results['errors'].append(str(e))
        return results
    finally:
        conn.close()


def print_results(results: Dict, title: str):
    """Print deployment results in a formatted way."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")

    if results.get('deployed'):
        print(f"\n[OK] DEPLOYED ({len(results['deployed'])})")
        for item in results['deployed']:
            print(f"   {item.get('type', 'command'):12} | {item.get('name', item.get('name'))}")

    if results.get('imported'):
        print(f"\n[OK] IMPORTED ({len(results['imported'])})")
        for item in results['imported']:
            scope = item.get('scope', 'unknown')
            project = f" ({item.get('project')})" if item.get('project') else ""
            print(f"   {scope:12} | {item['name']}{project}")

    if results.get('skipped'):
        print(f"\n[--] SKIPPED ({len(results['skipped'])})")
        for item in results['skipped']:
            print(f"   {item.get('type', 'unknown'):12} | {item['name']}: {item.get('reason', 'unknown')}")

    if results.get('conflicts'):
        print(f"\n[!!] CONFLICTS ({len(results['conflicts'])})")
        for item in results['conflicts']:
            print(f"   {item['type']:12} | {item['name']}: local file modified")
            print(f"                  Path: {item['path']}")

    if results.get('errors'):
        print(f"\n[XX] ERRORS ({len(results['errors'])})")
        for item in results['errors']:
            if isinstance(item, dict):
                print(f"   {item.get('type', 'error'):12} | {item.get('name', 'unknown')}: {item.get('error')}")
            else:
                print(f"   {item}")

    print(f"\n{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description='Deploy configuration components from database to files')
    parser.add_argument('project_name', nargs='?', help='Project name (default: current directory)')
    parser.add_argument('--import', dest='do_import', action='store_true',
                        help='Import files to database instead of deploying')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--force', action='store_true', help='Deploy even if hashes match')
    parser.add_argument('--component-type', choices=['claude_md', 'skill', 'instruction', 'rule', 'command', 'standard'],
                        help='Only deploy specific component type')

    args = parser.parse_args()

    # Determine project name
    project_name = args.project_name
    if not project_name:
        project_name = Path.cwd().name

    if args.do_import:
        # Import mode
        print(f"\n>>> Importing commands to database...")
        if args.dry_run:
            print("   (DRY RUN - no changes will be made)\n")

        results = import_commands_from_files(dry_run=args.dry_run)
        print_results(results, "IMPORT RESULTS")
    else:
        # Deploy mode
        print(f"\n>>> Deploying components for project: {project_name}")
        if args.dry_run:
            print("   (DRY RUN - no changes will be made)")
        if args.force:
            print("   (FORCE - ignoring hash matches)")
        print()

        results = deploy_for_project(
            project_name,
            component_type=args.component_type,
            dry_run=args.dry_run,
            force=args.force
        )
        print_results(results, f"DEPLOYMENT RESULTS - {project_name}")


if __name__ == '__main__':
    main()
