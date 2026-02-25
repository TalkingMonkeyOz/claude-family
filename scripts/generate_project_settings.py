#!/usr/bin/env python3
"""
Generate Project Settings - Database-Driven Configuration Generator

Reads configuration from PostgreSQL database and generates .claude/settings.local.json
with ALL settings including hooks.

Architecture:
    Database (Source of Truth)
        ↓
    generate_project_settings.py
        ↓
    .claude/settings.local.json (Generated, contains hooks + MCP + skills + permissions)

Note: Claude Code reads hooks from settings files only:
    - ~/.claude/settings.json (global)
    - .claude/settings.json (project, shared)
    - .claude/settings.local.json (project, local)
A separate hooks.json file is NOT supported by Claude Code.

Merge Priority (last wins):
    1. Base template (hooks-base from config_templates)
    2. Project type defaults (from project_type_configs)
    3. Project-specific overrides (from workspaces.startup_config)

Change Detection (2026-01-11):
    Before generating settings, checks if CLAUDE.md has local changes.
    If changed, prompts user to:
    - [1] Accept changes → Import to database
    - [2] Discard changes → Restore from database
    - [3] Continue anyway → No sync

Called by:
    - Desktop shortcut → Launch-Claude-Code-Console.bat
    - session_startup_hook.py on every SessionStart (self-healing)
    - Manual: python scripts/generate_project_settings.py [project_name]

Author: Claude Family
Date: 2025-12-27
Updated: 2026-01-11 (added change detection)
"""

import json
import os
import sys
import logging
import hashlib
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from copy import deepcopy

# Setup logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('config_generator')

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg
_psycopg_mod, PSYCOPG_VERSION, _, _ = detect_psycopg()
DB_AVAILABLE = _psycopg_mod is not None


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries, with override taking precedence.

    For hooks specifically, we merge at the hook type level to allow
    adding new hooks without replacing entire sections.
    """
    result = deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge dictionaries
            result[key] = deep_merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # For arrays, append (don't replace)
            result[key] = result[key] + value
        else:
            # Override
            result[key] = value

    return result


def validate_hooks(hooks_config: Dict) -> Dict:
    """Validate and clean hook configuration, removing invalid hook types.

    Valid Claude Code hook types (as of 2025-12-29):
    - PreToolUse, PostToolUse, PostToolUseFailure
    - UserPromptSubmit, PermissionRequest
    - SessionStart, SessionEnd
    - Stop, SubagentStart, SubagentStop
    - PreCompact, Notification
    """
    VALID_HOOK_TYPES = {
        'PreToolUse', 'PostToolUse', 'PostToolUseFailure',
        'UserPromptSubmit', 'PermissionRequest',
        'SessionStart', 'SessionEnd',
        'Stop', 'SubagentStart', 'SubagentStop',
        'PreCompact', 'Notification'
    }

    if not hooks_config:
        return hooks_config

    invalid = set(hooks_config.keys()) - VALID_HOOK_TYPES
    if invalid:
        logger.warning(f"Removing invalid hook types: {invalid}")
        logger.warning("Note: PreCommit/PostCommit are NOT valid Claude Code hooks (use native Git hooks)")
        for key in invalid:
            del hooks_config[key]

    return hooks_config


def get_base_template(conn) -> Optional[Dict]:
    """Get the base hooks template from config_templates."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT content
            FROM claude.config_templates
            WHERE template_name = 'hooks-base'
        """)

        row = cur.fetchone()
        if row:
            return dict(row)['content'] if PSYCOPG_VERSION == 3 else row['content']
        return None
    except Exception as e:
        logger.error(f"Failed to get base template: {e}")
        return None


def get_project_type_defaults(conn, project_type: str) -> Optional[Dict]:
    """Get project type defaults from project_type_configs."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                default_mcp_servers,
                default_skills,
                default_instructions
            FROM claude.project_type_configs
            WHERE project_type = %s
        """, (project_type,))

        row = cur.fetchone()
        if row:
            data = dict(row) if PSYCOPG_VERSION == 3 else dict(row)
            return {
                'mcp_servers': data.get('default_mcp_servers', []),
                'skills': data.get('default_skills', []),
                'instructions': data.get('default_instructions', [])
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get project type defaults: {e}")
        return None


def get_project_info(conn, project_name: str) -> Optional[Dict]:
    """Get project info from workspaces."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT project_type, startup_config
            FROM claude.workspaces
            WHERE project_name = %s
        """, (project_name,))

        row = cur.fetchone()
        if row:
            return dict(row) if PSYCOPG_VERSION == 3 else dict(row)
        return None
    except Exception as e:
        logger.error(f"Failed to get project info: {e}")
        return None


def get_profile_for_project(conn, project_name: str) -> Optional[Dict]:
    """Get profile from claude.profiles for a project."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT profile_id, name, config, current_version
            FROM claude.profiles
            WHERE name = %s
        """, (project_name,))

        row = cur.fetchone()
        if row:
            data = dict(row) if PSYCOPG_VERSION == 3 else dict(row)
            return {
                'profile_id': data['profile_id'],
                'name': data['name'],
                'config': data['config'],
                'current_version': data['current_version']
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get profile: {e}")
        return None


def check_for_local_changes(project_path: str, profile: Dict) -> Tuple[bool, str]:
    """Compare CLAUDE.md file content vs database profile.

    Returns:
        (has_changes, changed_file) - True if file differs from database
    """
    claude_md_path = Path(project_path) / "CLAUDE.md"

    if not claude_md_path.exists():
        return False, ""

    try:
        with open(claude_md_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
    except Exception as e:
        logger.error(f"Failed to read CLAUDE.md: {e}")
        return False, ""

    # Get database content
    db_content = ""
    if profile and profile.get('config'):
        db_content = profile['config'].get('behavior', '')

    # Compare by hash for efficiency
    file_hash = hashlib.md5(file_content.encode('utf-8')).hexdigest()
    db_hash = hashlib.md5(db_content.encode('utf-8')).hexdigest()

    if file_hash != db_hash:
        logger.info(f"Local changes detected in CLAUDE.md (file hash: {file_hash[:8]}, db hash: {db_hash[:8]})")
        return True, "CLAUDE.md"

    return False, ""


def import_changes_to_database(conn, project_name: str, project_path: str, profile: Optional[Dict]) -> bool:
    """Import CLAUDE.md content to database profile."""
    claude_md_path = Path(project_path) / "CLAUDE.md"

    try:
        with open(claude_md_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
    except Exception as e:
        logger.error(f"Failed to read CLAUDE.md: {e}")
        return False

    try:
        cur = conn.cursor()

        if profile:
            # Update existing profile
            new_version = profile['current_version'] + 1
            new_config = profile['config'].copy() if profile['config'] else {}
            new_config['behavior'] = file_content

            cur.execute("""
                UPDATE claude.profiles
                SET config = %s, current_version = %s, updated_at = NOW()
                WHERE profile_id = %s
            """, (json.dumps(new_config), new_version, profile['profile_id']))

            # Create version snapshot
            cur.execute("""
                INSERT INTO claude.profile_versions (version_id, profile_id, version, config, notes)
                VALUES (%s, %s, %s, %s, %s)
            """, (str(uuid.uuid4()), profile['profile_id'], new_version, json.dumps(new_config),
                  'Imported local changes from CLAUDE.md'))

            conn.commit()
            logger.info(f"Updated profile {project_name} to version {new_version}")
            print(f"  Imported changes to database (version {new_version})")
        else:
            # Create new profile
            profile_id = str(uuid.uuid4())
            config = {
                'behavior': file_content,
                'description': f'{project_name} project configuration'
            }

            cur.execute("""
                INSERT INTO claude.profiles (profile_id, name, source_type, config, current_version, is_active, is_favorite)
                VALUES (%s, %s, 'project', %s, 1, true, false)
            """, (profile_id, project_name, json.dumps(config)))

            cur.execute("""
                INSERT INTO claude.profile_versions (version_id, profile_id, version, config, notes)
                VALUES (%s, %s, 1, %s, %s)
            """, (str(uuid.uuid4()), profile_id, json.dumps(config), 'Initial import from CLAUDE.md'))

            conn.commit()
            logger.info(f"Created new profile for {project_name}")
            print(f"  Created new profile in database")

        return True

    except Exception as e:
        logger.error(f"Failed to import to database: {e}")
        conn.rollback()
        return False


def restore_file_from_database(project_path: str, profile: Dict) -> bool:
    """Restore CLAUDE.md from database profile content."""
    if not profile or not profile.get('config'):
        logger.error("No profile content to restore")
        return False

    db_content = profile['config'].get('behavior', '')
    if not db_content:
        logger.error("Profile has no behavior content")
        return False

    claude_md_path = Path(project_path) / "CLAUDE.md"

    try:
        # Create backup first
        if claude_md_path.exists():
            backup_path = claude_md_path.with_suffix('.md.bak')
            import shutil
            shutil.copy2(claude_md_path, backup_path)
            logger.info(f"Created backup: {backup_path}")

        # Write database content
        with open(claude_md_path, 'w', encoding='utf-8') as f:
            f.write(db_content)

        logger.info(f"Restored CLAUDE.md from database (v{profile['current_version']})")
        print(f"  Restored CLAUDE.md from database (backup saved as .bak)")
        return True

    except Exception as e:
        logger.error(f"Failed to restore file: {e}")
        return False


def prompt_user_for_action(changed_file: str, interactive: bool = True) -> str:
    """Prompt user for action on detected changes.

    Returns: '1' (accept), '2' (discard), '3' (continue), or 'skip' if non-interactive
    """
    if not interactive:
        logger.info("Non-interactive mode, skipping change prompt")
        return 'skip'

    print(f"\n{'='*60}")
    print(f"  LOCAL CHANGES DETECTED: {changed_file}")
    print(f"{'='*60}")
    print()
    print("  The file has been modified outside the database.")
    print()
    print("  [1] Accept changes  (import to database)")
    print("  [2] Discard changes (restore from database)")
    print("  [3] Continue anyway (no sync)")
    print()

    try:
        choice = input("  Choice (1-3): ").strip()
        if choice in ('1', '2', '3'):
            return choice
        print("  Invalid choice, continuing without sync...")
        return '3'
    except (EOFError, KeyboardInterrupt):
        print("\n  Interrupted, continuing without sync...")
        return '3'


def get_current_settings(project_path: str) -> Dict:
    """Read current settings.local.json if it exists."""
    settings_file = Path(project_path) / ".claude" / "settings.local.json"

    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read existing settings: {e}")

    return {}


def generate_settings(project_name: str, project_path: Optional[str] = None) -> Optional[Dict]:
    """Generate settings for a project by merging database configs.

    Args:
        project_name: Name of the project
        project_path: Optional path to project (defaults to cwd)

    Returns:
        Dict with merged settings, or None if failed
    """
    if not DB_AVAILABLE:
        logger.error("Database not available - cannot generate settings")
        return None

    conn = get_db_connection()
    if not conn:
        logger.error("Failed to connect to database")
        return None

    try:
        logger.info(f"Generating settings for project: {project_name}")

        # 1. Get project info
        project_info = get_project_info(conn, project_name)
        if not project_info:
            logger.warning(f"Project '{project_name}' not found in workspaces table")
            conn.close()
            return None

        project_type = project_info.get('project_type', 'infrastructure')
        logger.info(f"Project type: {project_type}")

        # 2. Get base template (hooks-base)
        base_config = get_base_template(conn)
        if not base_config:
            logger.warning("No base template found, starting with empty config")
            base_config = {}

        # 3. Get project type defaults
        type_defaults = get_project_type_defaults(conn, project_type)
        if not type_defaults:
            logger.warning(f"No defaults found for project type '{project_type}'")
            type_defaults = {}

        # 4. Get project-specific overrides
        startup_config = project_info.get('startup_config')
        if startup_config is None:
            startup_config = {}

        # 5. Merge: base + type_defaults + overrides
        merged = deep_merge(base_config, type_defaults)
        final_config = deep_merge(merged, startup_config)

        # 6. Preserve current permissions if they exist
        if project_path:
            current = get_current_settings(project_path)
            if 'permissions' in current:
                final_config['permissions'] = current['permissions']

        # 7. Ensure permissions structure exists
        if 'permissions' not in final_config:
            final_config['permissions'] = {
                'allow': [],
                'deny': [],
                'ask': []
            }

        # 8. Validate and clean hooks configuration
        if 'hooks' in final_config:
            final_config['hooks'] = validate_hooks(final_config['hooks'])

        logger.info(f"Successfully generated settings for {project_name}")
        logger.info(f"  - Hook types: {list(final_config.get('hooks', {}).keys())}")
        logger.info(f"  - MCP servers: {final_config.get('mcp_servers', [])}")

        conn.close()
        return final_config

    except Exception as e:
        logger.error(f"Failed to generate settings: {e}", exc_info=True)
        try:
            conn.close()
        except:
            pass
        return None


def write_settings(project_path: str, settings: Dict) -> bool:
    """Write settings to .claude/settings.local.json

    Claude Code reads hooks from settings files, NOT from a separate hooks.json.
    Valid locations for hooks (per official docs):
      - ~/.claude/settings.json (global)
      - .claude/settings.json (project, shared)
      - .claude/settings.local.json (project, local)

    We write everything (including hooks) to settings.local.json.
    """
    try:
        claude_dir = Path(project_path) / ".claude"
        claude_dir.mkdir(exist_ok=True)

        # Write ALL settings (including hooks) to settings.local.json
        settings_file = claude_dir / "settings.local.json"
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        hook_types = list(settings.get('hooks', {}).keys())
        logger.info(f"Settings written to {settings_file}")
        logger.info(f"  - Hooks included: {hook_types}")

        # Clean up legacy hooks.json if it exists (no longer used)
        legacy_hooks_file = claude_dir / "hooks.json"
        if legacy_hooks_file.exists():
            legacy_hooks_file.unlink()
            logger.info(f"Removed legacy {legacy_hooks_file} (hooks now in settings.local.json)")

        return True

    except Exception as e:
        logger.error(f"Failed to write settings: {e}", exc_info=True)
        return False


def sync_project_config(project_name: str, project_path: Optional[str] = None) -> bool:
    """Main entry point: Generate and write settings for a project.

    Args:
        project_name: Name of the project
        project_path: Optional path to project (defaults to cwd)

    Returns:
        True if successful, False otherwise
    """
    if project_path is None:
        project_path = os.getcwd()

    logger.info(f"=== Config Sync Started: {project_name} ===")

    # Generate settings from database
    settings = generate_settings(project_name, project_path)
    if not settings:
        logger.error("Failed to generate settings")
        return False

    # Write to file
    if not write_settings(project_path, settings):
        logger.error("Failed to write settings")
        return False

    logger.info(f"=== Config Sync Complete: {project_name} ===")
    return True


def check_and_handle_local_changes(project_name: str, project_path: str, interactive: bool = True) -> bool:
    """Check for local changes and handle them based on user choice.

    Args:
        project_name: Name of the project
        project_path: Path to project directory
        interactive: If False, skip prompting (for automated/hook calls)

    Returns:
        True if we should continue with settings generation, False to abort
    """
    if not DB_AVAILABLE:
        return True  # Can't check without DB

    conn = get_db_connection()
    if not conn:
        return True  # Can't check without connection

    try:
        # Get profile from database
        profile = get_profile_for_project(conn, project_name)

        # Check for local changes
        has_changes, changed_file = check_for_local_changes(project_path, profile)

        if not has_changes:
            conn.close()
            return True  # No changes, continue normally

        # Get user choice
        choice = prompt_user_for_action(changed_file, interactive)

        if choice == '1':
            # Accept changes - import to database
            success = import_changes_to_database(conn, project_name, project_path, profile)
            conn.close()
            return True  # Continue with settings generation

        elif choice == '2':
            # Discard changes - restore from database
            if profile:
                restore_file_from_database(project_path, profile)
            else:
                print("  No profile in database to restore from")
            conn.close()
            return True  # Continue with settings generation

        else:
            # Continue anyway (choice 3 or skip)
            conn.close()
            return True

    except Exception as e:
        logger.error(f"Error during change detection: {e}")
        try:
            conn.close()
        except:
            pass
        return True  # Continue on error


def main():
    """CLI entry point."""
    # Parse arguments
    interactive = True
    project_name = None
    project_path = None

    args = sys.argv[1:]

    # Check for --no-interactive flag
    if '--no-interactive' in args:
        interactive = False
        args.remove('--no-interactive')

    # Check for --skip-change-detection flag (for hook calls)
    skip_change_detection = '--skip-change-detection' in args
    if skip_change_detection:
        args.remove('--skip-change-detection')

    if len(args) >= 1:
        project_name = args[0]
        project_path = args[1] if len(args) > 1 else os.getcwd()
    else:
        # Auto-detect from cwd
        project_path = os.getcwd()
        project_name = os.path.basename(project_path)

    print(f"Generating settings for: {project_name}")
    print(f"Project path: {project_path}")

    # Step 1: Check for local changes (unless skipped)
    if not skip_change_detection:
        if not check_and_handle_local_changes(project_name, project_path, interactive):
            print("[ABORT] Settings generation aborted")
            return 1

    # Step 2: Generate and write settings
    if sync_project_config(project_name, project_path):
        print("[OK] Settings generated successfully")
        print(f"  Check: {project_path}/.claude/settings.local.json")
        print(f"  Logs: {LOG_FILE}")
        return 0
    else:
        print("[FAIL] Failed to generate settings")
        print(f"  Check logs: {LOG_FILE}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
