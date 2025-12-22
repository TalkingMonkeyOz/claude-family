#!/usr/bin/env python3
"""
Deploy Project Configs - Database-driven config deployment

This script is called by CFM (or batch file) BEFORE launching Claude Code.
It queries the database for config templates assigned to a project and
generates/updates the necessary files.

This replaces the older file-based sync_project_configs.py with a
database-driven approach for centralized config management.

Usage:
    python deploy_project_configs.py <project_name_or_path>
    python deploy_project_configs.py claude-family
    python deploy_project_configs.py "C:/Projects/nimbus-user-loader"
    python deploy_project_configs.py --all
    python deploy_project_configs.py --all --dry-run

Author: Claude Family
Date: 2025-12-21
"""

import sys
import os
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from copy import deepcopy

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("Error: psycopg3 not installed. Run: pip install psycopg[binary]")
    sys.exit(1)


# Database connection - reads from environment or uses default
DB_CONNECTION = os.environ.get(
    "DATABASE_URI",
    "postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation"
)


def get_connection():
    """Get database connection."""
    return psycopg.connect(DB_CONNECTION, row_factory=dict_row)


def find_project(identifier: str) -> Optional[Dict]:
    """Find project by name or path."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Try by name first
            cur.execute("""
                SELECT project_id, project_name, metadata->>'project_path' as project_path
                FROM claude.projects
                WHERE project_name ILIKE %s
                  AND (is_archived = false OR is_archived IS NULL)
            """, (identifier,))
            result = cur.fetchone()

            if result:
                return dict(result)

            # Try by path (partial match)
            cur.execute("""
                SELECT project_id, project_name, metadata->>'project_path' as project_path
                FROM claude.projects
                WHERE metadata->>'project_path' ILIKE %s
                  AND (is_archived = false OR is_archived IS NULL)
            """, (f"%{identifier}%",))
            result = cur.fetchone()

            if result:
                return dict(result)

    return None


def get_all_active_projects() -> List[Dict]:
    """Get all active projects."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT project_id, project_name, metadata->>'project_path' as project_path
                FROM claude.projects
                WHERE (is_archived = false OR is_archived IS NULL)
                  AND metadata->>'project_path' IS NOT NULL
                ORDER BY project_name
            """)
            return [dict(row) for row in cur.fetchall()]


def get_project_templates(project_id: str) -> List[Dict]:
    """Get all config templates assigned to a project."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    ct.template_id,
                    ct.template_name,
                    ct.config_type,
                    ct.content,
                    ct.file_path,
                    ct.is_base,
                    ct.extends_template_id,
                    ct.version,
                    pca.override_content,
                    pca.deployed_version
                FROM claude.project_config_assignments pca
                JOIN claude.config_templates ct ON ct.template_id = pca.template_id
                WHERE pca.project_id = %s
                  AND pca.is_active = true
                ORDER BY ct.is_base DESC, ct.template_id
            """, (project_id,))
            return [dict(row) for row in cur.fetchall()]


def deep_merge(base: Dict, extension: Dict) -> Dict:
    """Deep merge two dictionaries. Extension values override base."""
    result = deepcopy(base)

    for key, value in extension.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # For lists in hooks, we need smart merging by matcher
            result[key] = merge_hook_lists(result[key], value)
        else:
            result[key] = deepcopy(value)

    return result


def merge_hook_lists(base_list: List, extension_list: List) -> List:
    """Merge hook lists, combining hooks with same matcher."""
    result = deepcopy(base_list)

    # Build index of existing matchers
    matcher_index = {}
    for i, item in enumerate(result):
        if isinstance(item, dict) and 'matcher' in item:
            matcher_index[item['matcher']] = i

    for ext_item in extension_list:
        if isinstance(ext_item, dict) and 'matcher' in ext_item:
            matcher = ext_item['matcher']
            if matcher in matcher_index:
                # Merge hooks into existing matcher group
                idx = matcher_index[matcher]
                if 'hooks' in result[idx] and 'hooks' in ext_item:
                    result[idx]['hooks'].extend(ext_item['hooks'])
            else:
                # Add new matcher group
                result.append(deepcopy(ext_item))
                matcher_index[matcher] = len(result) - 1
        else:
            # Non-matcher item, just append
            result.append(deepcopy(ext_item))

    return result


def merge_hooks_content(templates: List[Dict]) -> Dict:
    """Merge multiple hooks templates into a single hooks.json content."""
    result = {"hooks": {}}

    for template in templates:
        content = template['content']
        if isinstance(content, str):
            content = json.loads(content)

        # Apply project-specific overrides if present
        if template.get('override_content'):
            override = template['override_content']
            if isinstance(override, str):
                override = json.loads(override)
            content = deep_merge(content, override)

        # Merge into result
        result = deep_merge(result, content)

    return result


def compute_hash(content: str) -> str:
    """Compute hash of content for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def log_deployment(project_id: str, config_type: str, file_path: str,
                   action: str, template_id: Optional[int] = None,
                   version: Optional[int] = None, details: Optional[str] = None):
    """Log deployment action to database."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO claude.config_deployment_log
                        (project_id, config_type, file_path, action, template_id, version_deployed, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (project_id, config_type, file_path, action, template_id, version, details))
                conn.commit()
    except Exception as e:
        print(f"  Warning: Could not log deployment: {e}")


def update_deployment_status(project_id: str, template_id: int, version: int, content_hash: str):
    """Update deployment status in project_config_assignments."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE claude.project_config_assignments
                    SET deployed_at = NOW(),
                        deployed_version = %s,
                        deployment_hash = %s
                    WHERE project_id = %s AND template_id = %s
                """, (version, content_hash, project_id, template_id))
                conn.commit()
    except Exception as e:
        print(f"  Warning: Could not update deployment status: {e}")


def deploy_hooks(project: Dict, templates: List[Dict], dry_run: bool = False) -> bool:
    """Deploy hooks.json for a project."""
    project_path = project['project_path']
    project_id = str(project['project_id'])

    # Filter to hooks templates only
    hooks_templates = [t for t in templates if t['config_type'] == 'hooks']

    if not hooks_templates:
        print(f"  No hooks templates assigned")
        return True

    # Merge all hooks templates
    merged_content = merge_hooks_content(hooks_templates)
    content_json = json.dumps(merged_content, indent=2)
    content_hash = compute_hash(content_json)

    # Determine file path
    target_path = Path(project_path) / ".claude" / "hooks.json"

    # Check if file exists and compare
    action = "created"
    if target_path.exists():
        try:
            existing_content = target_path.read_text(encoding='utf-8')
            existing_hash = compute_hash(existing_content)

            if existing_hash == content_hash:
                print(f"  hooks.json: No changes (up to date)")
                if not dry_run:
                    log_deployment(project_id, 'hooks', str(target_path), 'skipped',
                                 details="Content unchanged")
                return True
            action = "updated"
        except Exception as e:
            print(f"  hooks.json: Will replace (read error: {e})")
            action = "replaced"

    template_names = ', '.join(t['template_name'] for t in hooks_templates)

    if dry_run:
        print(f"  hooks.json: Would be {action}")
        print(f"    Templates: {template_names}")
        return True

    # Create directory if needed
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    target_path.write_text(content_json, encoding='utf-8')
    print(f"  hooks.json: {action.upper()} ({template_names})")

    # Log and update status
    for template in hooks_templates:
        log_deployment(project_id, 'hooks', str(target_path), action,
                      template['template_id'], template['version'])
        update_deployment_status(project_id, template['template_id'],
                                template['version'], content_hash)

    return True


def deploy_to_project(project: Dict, dry_run: bool = False) -> bool:
    """Deploy all configs to a project."""
    project_name = project['project_name']
    project_path = project['project_path']
    project_id = str(project['project_id'])

    print(f"\n  {project_name}")
    print(f"  Path: {project_path}")

    # Verify path exists
    if not project_path or not Path(project_path).exists():
        print(f"  ERROR: Project path does not exist")
        return False

    # Get templates
    templates = get_project_templates(project_id)

    if not templates:
        print(f"  No templates assigned")
        return True

    # Deploy hooks
    success = deploy_hooks(project, templates, dry_run)

    # TODO: Add deploy for commands, settings, etc.

    return success


def deploy_single_project(identifier: str, dry_run: bool = False) -> bool:
    """Deploy configs to a single project."""
    print("="*60)
    print(f"DEPLOY PROJECT CONFIGS")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("="*60)

    project = find_project(identifier)
    if not project:
        print(f"ERROR: Project not found: {identifier}")
        return False

    return deploy_to_project(project, dry_run)


def deploy_all_projects(dry_run: bool = False) -> bool:
    """Deploy configs to all active projects."""
    print("="*60)
    print("DEPLOY ALL PROJECT CONFIGS")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("="*60)

    projects = get_all_active_projects()
    print(f"Found {len(projects)} active projects")

    all_success = True
    for project in projects:
        try:
            success = deploy_to_project(project, dry_run)
            if not success:
                all_success = False
        except Exception as e:
            print(f"  ERROR: {e}")
            all_success = False

    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE")
    print("="*60)

    return all_success


def main():
    parser = argparse.ArgumentParser(
        description='Deploy project configs from database to project directories'
    )
    parser.add_argument('project', nargs='?',
                        help='Project name or path (omit for --all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making changes')
    parser.add_argument('--all', action='store_true',
                        help='Deploy to all active projects')

    args = parser.parse_args()

    if args.all:
        success = deploy_all_projects(args.dry_run)
    elif args.project:
        success = deploy_single_project(args.project, args.dry_run)
    else:
        parser.print_help()
        print("\nError: Specify a project or use --all")
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
