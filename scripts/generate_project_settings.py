#!/usr/bin/env python3
"""
Generate Project Settings - Database-Driven Configuration Generator

Reads configuration from PostgreSQL database and generates .claude/settings.local.json

Architecture:
    Database (Source of Truth)
        ↓
    generate_project_settings.py
        ↓
    .claude/settings.local.json (Generated, do not edit manually)

Merge Priority (last wins):
    1. Base template (hooks-base from config_templates)
    2. Project type defaults (from project_type_configs)
    3. Project-specific overrides (from workspaces.startup_config)

Called by:
    - session_startup_hook.py on every SessionStart (self-healing)
    - Manual: python scripts/generate_project_settings.py [project_name]

Author: Claude Family
Date: 2025-12-27
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional
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

# Try to import psycopg for database access
DB_AVAILABLE = False
try:
    import psycopg
    from psycopg.rows import dict_row
    DB_AVAILABLE = True
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        DB_AVAILABLE = True
        PSYCOPG_VERSION = 2
    except ImportError:
        DB_AVAILABLE = False

# Default connection string - DO NOT hardcode credentials!
DEFAULT_CONN_STR = None

# Try to load from ai-workspace secure config
try:
    import sys as _sys
    _sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
    from config import POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
except ImportError:
    pass


def get_db_connection():
    """Get PostgreSQL connection from environment or default."""
    conn_str = os.environ.get('DATABASE_URL', DEFAULT_CONN_STR)

    if not conn_str:
        return None

    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(conn_str, row_factory=dict_row)
        else:
            return psycopg.connect(conn_str, cursor_factory=RealDictCursor)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


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
                'enabledMcpjsonServers': data.get('default_mcp_servers', []),
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

        logger.info(f"Successfully generated settings for {project_name}")
        logger.info(f"  - Hook types: {list(final_config.get('hooks', {}).keys())}")
        logger.info(f"  - MCP servers: {final_config.get('enabledMcpjsonServers', [])}")

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
    """Write settings to .claude/settings.local.json"""
    try:
        claude_dir = Path(project_path) / ".claude"
        claude_dir.mkdir(exist_ok=True)

        settings_file = claude_dir / "settings.local.json"

        # Write with nice formatting
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        logger.info(f"Settings written to {settings_file}")
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


def main():
    """CLI entry point."""
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        project_path = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    else:
        # Auto-detect from cwd
        project_path = os.getcwd()
        project_name = os.path.basename(project_path)

    print(f"Generating settings for: {project_name}")
    print(f"Project path: {project_path}")

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
