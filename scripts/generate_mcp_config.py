#!/usr/bin/env python3
"""
Generate MCP Config - Database-Driven .mcp.json Generator

Reads MCP server configuration from PostgreSQL database and generates .mcp.json
with automatic resolution of npx packages to direct node paths.

Architecture:
    Database (Source of Truth: workspaces.startup_config.mcp_configs)
        ↓
    generate_mcp_config.py (resolves npx → direct node paths)
        ↓
    .mcp.json (Generated, self-healing)

Features:
    - Resolves npx packages to direct node paths (eliminates cmd.exe shim overhead)
    - Falls back to cmd /c npx wrapper if package not globally installed
    - Preserves env vars and other config
    - Logs all operations to ~/.claude/hooks.log

Called by:
    - Desktop shortcut → start-claude.bat
    - Manual: python scripts/generate_mcp_config.py [project_name|project_path]

Author: Claude Family
Date: 2026-01-26
"""

import json
import os
import sys
import logging
import platform
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple
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
logger = logging.getLogger('mcp_config_generator')

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

# Default connection string - load from secure config
DEFAULT_CONN_STR = None

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


def get_mcp_configs(conn, project_name: str) -> Optional[Dict]:
    """Get MCP configs from workspaces.startup_config.mcp_configs."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                startup_config->'mcp_configs' as mcp_configs,
                startup_config->'enabledMcpjsonServers' as enabled_servers
            FROM claude.workspaces
            WHERE project_name = %s
        """, (project_name,))

        row = cur.fetchone()
        if row:
            data = dict(row) if PSYCOPG_VERSION == 3 else dict(row)
            return {
                'mcp_configs': data.get('mcp_configs') or {},
                'enabled_servers': data.get('enabled_servers') or []
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get MCP configs: {e}")
        return None


def _find_global_npm_entry_point(package_name: str) -> Optional[str]:
    """Find the entry point of a globally installed npm package.

    Checks the global npm node_modules directory for the package and resolves
    its main/bin entry point.

    Args:
        package_name: npm package name (e.g., '@mui/mcp', 'ag-mcp')

    Returns:
        Absolute path to the entry point .js file, or None if not found
    """
    # Get global npm prefix
    npm_prefix = os.environ.get('APPDATA', '')
    if not npm_prefix:
        return None

    global_modules = Path(npm_prefix) / "npm" / "node_modules"
    pkg_dir = global_modules / package_name.replace('/', os.sep)

    if not pkg_dir.exists():
        return None

    # Read package.json to find entry point
    pkg_json = pkg_dir / "package.json"
    if not pkg_json.exists():
        return None

    try:
        with open(pkg_json, 'r', encoding='utf-8') as f:
            pkg_data = json.load(f)

        # Check bin first (for CLI tools), then main
        bin_entry = pkg_data.get('bin', {})
        if isinstance(bin_entry, str):
            entry = bin_entry
        elif isinstance(bin_entry, dict):
            # Use first bin entry
            entry = next(iter(bin_entry.values()), None)
        else:
            entry = None

        if not entry:
            entry = pkg_data.get('main')

        if entry:
            full_path = pkg_dir / entry
            if full_path.exists():
                return str(full_path.resolve())

    except Exception as e:
        logger.debug(f"Failed to read package.json for {package_name}: {e}")

    return None


def _get_node_path() -> str:
    """Get the path to the node executable."""
    if platform.system() == 'Windows':
        # Check common locations
        for candidate in [
            Path(os.environ.get('ProgramFiles', '')) / "nodejs" / "node.exe",
            Path(os.environ.get('LOCALAPPDATA', '')) / "fnm_multishells" / "node.exe",
        ]:
            if candidate.exists():
                return str(candidate)
    return "node"  # Fall back to PATH lookup


def resolve_server_command(server_name: str, server_config: Dict) -> Dict:
    """Resolve npx commands to direct node paths where possible.

    For npx-based MCP servers, checks if the npm package is globally installed.
    If so, replaces the npx command with a direct node invocation, eliminating
    the cmd.exe shim overhead (2 extra processes per server on Windows).

    Falls back to cmd /c npx wrapper if the package is not globally installed.

    Args:
        server_name: Name of the MCP server (for logging)
        server_config: Server configuration dict

    Returns:
        Modified server config with resolved command
    """
    command = server_config.get('command', '')
    args = server_config.get('args', [])

    # Normalize: if already cmd-wrapped npx, extract the package info
    is_cmd_wrapped_npx = (command == 'cmd' and len(args) >= 3
                          and args[0] == '/c' and args[1] == 'npx')
    is_raw_npx = command == 'npx'

    if not is_raw_npx and not is_cmd_wrapped_npx:
        return server_config

    # Extract package name and extra args from the npx args
    if is_cmd_wrapped_npx:
        npx_args = args[2:]  # Skip /c, npx
    else:
        npx_args = list(args)

    # Filter out -y flag and find the package name
    extra_args = []
    package_name = None
    for arg in npx_args:
        if arg == '-y':
            continue
        elif package_name is None and not arg.startswith('-'):
            package_name = arg
        else:
            extra_args.append(arg)

    if not package_name:
        logger.warning(f"Could not determine package name for {server_name}")
        return server_config

    # Strip @version suffix for lookup (e.g., @mui/mcp@latest → @mui/mcp)
    lookup_name = package_name.split('@latest')[0]
    # Handle scoped packages: @scope/pkg@version
    if lookup_name.startswith('@') and '@' in lookup_name[1:]:
        # e.g., @playwright/mcp@0.1.0 → @playwright/mcp
        parts = lookup_name[1:].split('@', 1)
        lookup_name = '@' + parts[0]

    # Try to resolve to a globally installed package
    entry_point = _find_global_npm_entry_point(lookup_name)

    if entry_point:
        node_path = _get_node_path()
        result = {
            'type': server_config.get('type', 'stdio'),
            'command': node_path,
            'args': [entry_point] + extra_args
        }
        if 'env' in server_config:
            result['env'] = server_config['env']
        logger.info(f"Resolved {server_name}: npx {package_name} → node {entry_point}")
        return result

    # Fallback: wrap with cmd /c npx on Windows
    if platform.system() == 'Windows' and is_raw_npx:
        has_dash_y = '-y' in args
        result = {
            'type': server_config.get('type', 'stdio'),
            'command': 'cmd',
            'args': ['/c', 'npx'] + (['-y'] if not has_dash_y else []) + args
        }
        if 'env' in server_config:
            result['env'] = server_config['env']
        logger.info(f"Fallback wrapper for {server_name}: npx → cmd /c npx (not globally installed)")
        return result

    return server_config


def generate_mcp_json(project_name: str, project_path: str) -> Optional[Dict]:
    """Generate .mcp.json content from database configs.

    Args:
        project_name: Name of the project in workspaces table
        project_path: Path to the project directory

    Returns:
        Dict ready to be written as .mcp.json, or None if failed
    """
    if not DB_AVAILABLE:
        logger.error("Database not available - cannot generate MCP config")
        return None

    conn = get_db_connection()
    if not conn:
        logger.error("Failed to connect to database")
        return None

    try:
        logger.info(f"Generating MCP config for project: {project_name}")

        # Get MCP configs from database
        config_data = get_mcp_configs(conn, project_name)
        if not config_data:
            logger.warning(f"No MCP configs found for project '{project_name}'")
            conn.close()
            return None

        mcp_configs = config_data.get('mcp_configs', {})
        enabled_servers = config_data.get('enabled_servers', [])

        if not mcp_configs:
            logger.info(f"Project '{project_name}' has no MCP configs defined")
            conn.close()
            return None

        # Build mcpServers object
        mcp_servers = {}

        for server_name, server_config in mcp_configs.items():
            # Only include enabled servers if enabledMcpjsonServers is specified
            if enabled_servers and server_name not in enabled_servers:
                logger.info(f"Skipping disabled server: {server_name}")
                continue

            # Resolve npx to direct node paths where possible
            processed_config = resolve_server_command(server_name, deepcopy(server_config))

            # Ensure type is set
            if 'type' not in processed_config:
                processed_config['type'] = 'stdio'

            mcp_servers[server_name] = processed_config

        if not mcp_servers:
            logger.info(f"No enabled MCP servers for project '{project_name}'")
            conn.close()
            return None

        # Build final structure
        result = {
            "_comment": f"Generated from database - DO NOT EDIT MANUALLY",
            "_generated": True,
            "_project": project_name,
            "mcpServers": mcp_servers
        }

        logger.info(f"Generated MCP config with servers: {list(mcp_servers.keys())}")
        conn.close()
        return result

    except Exception as e:
        logger.error(f"Failed to generate MCP config: {e}", exc_info=True)
        try:
            conn.close()
        except:
            pass
        return None


def write_mcp_json(project_path: str, mcp_config: Dict) -> bool:
    """Write .mcp.json to project root.

    Args:
        project_path: Path to project directory
        mcp_config: MCP configuration dict

    Returns:
        True if successful, False otherwise
    """
    try:
        mcp_file = Path(project_path) / ".mcp.json"

        with open(mcp_file, 'w', encoding='utf-8') as f:
            json.dump(mcp_config, f, indent=2, ensure_ascii=False)

        servers = list(mcp_config.get('mcpServers', {}).keys())
        logger.info(f"MCP config written to {mcp_file}")
        logger.info(f"  - Servers: {servers}")

        return True

    except Exception as e:
        logger.error(f"Failed to write .mcp.json: {e}", exc_info=True)
        return False


def resolve_project(arg: str) -> tuple[str, str]:
    """Resolve argument to project name and path.

    Args:
        arg: Either a project name or a path

    Returns:
        Tuple of (project_name, project_path)
    """
    # Check if arg is a path
    if os.path.isdir(arg):
        project_path = os.path.abspath(arg)
        project_name = os.path.basename(project_path)
        return project_name, project_path

    # Check if arg looks like a project name - query database for path
    if not DB_AVAILABLE:
        # Assume it's a project name, use cwd
        return arg, os.getcwd()

    conn = get_db_connection()
    if not conn:
        return arg, os.getcwd()

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT project_path FROM claude.workspaces
            WHERE project_name = %s
        """, (arg,))

        row = cur.fetchone()
        if row:
            data = dict(row) if PSYCOPG_VERSION == 3 else dict(row)
            project_path = data.get('project_path', os.getcwd())
            conn.close()
            return arg, project_path

        conn.close()
        return arg, os.getcwd()

    except Exception as e:
        logger.error(f"Failed to resolve project: {e}")
        try:
            conn.close()
        except:
            pass
        return arg, os.getcwd()


def main():
    """CLI entry point."""
    # Parse arguments
    if len(sys.argv) >= 2:
        arg = sys.argv[1]
        project_name, project_path = resolve_project(arg)
    else:
        # Auto-detect from cwd
        project_path = os.getcwd()
        project_name = os.path.basename(project_path)

    print(f"Generating MCP config for: {project_name}")
    print(f"Project path: {project_path}")

    # Generate MCP config
    mcp_config = generate_mcp_json(project_name, project_path)

    if not mcp_config:
        print("[SKIP] No MCP config to generate (no mcp_configs in database)")
        return 0  # Not an error - project just doesn't have MCP configs

    # Write .mcp.json
    if write_mcp_json(project_path, mcp_config):
        servers = list(mcp_config.get('mcpServers', {}).keys())
        print(f"[OK] MCP config generated: {servers}")
        print(f"  File: {project_path}/.mcp.json")
        return 0
    else:
        print("[FAIL] Failed to write .mcp.json")
        print(f"  Check logs: {LOG_FILE}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
