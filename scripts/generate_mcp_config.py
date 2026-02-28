#!/usr/bin/env python3
"""
Generate MCP Config - Database-Driven .mcp.json Generator

Generates .mcp.json from database using a 3-layer merge chain:
    Layer 1: config_templates (global server configs like postgres, project-tools)
    Layer 2: project_type_configs.default_mcp_servers (which globals each project type gets)
    Layer 3: workspaces.startup_config.mcp_configs (project-specific overrides/additions)

Architecture:
    Database (Source of Truth)
        config_templates (mcp-postgres, mcp-project-tools, mcp-sequential-thinking)
            ↓ filtered by
        project_type_configs.default_mcp_servers (e.g. ['postgres', 'project-tools'])
            ↓ merged with
        workspaces.startup_config.mcp_configs (e.g. mui, playwright, bpmn-engine)
            ↓ resolved
        npx → direct node.exe paths (resolve_server_command)
            ↓
        {project}/.mcp.json (single output, all servers)

    Falls back to reading existing .mcp.json if DB unavailable.

Features:
    - 3-layer merge: templates + type defaults + workspace overrides
    - Resolves npx packages to direct node paths (eliminates cmd.exe shim overhead)
    - Falls back to cmd /c npx wrapper if package not globally installed
    - Graceful degradation: works without DB (reads existing .mcp.json)
    - Logs all operations to ~/.claude/hooks.log

Called by:
    - Launch-Claude-Code-Console.bat (before generate_project_settings.py)
    - Manual: python scripts/generate_mcp_config.py [project_name|project_path]

Author: Claude Family
Date: 2026-01-26
Updated: 2026-03-01 (restored DB-first with 3-layer merge)
"""

import json
import os
import sys
import logging
import platform
from pathlib import Path
from typing import Dict, Optional
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

# Database support (optional - graceful degradation if unavailable)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config import get_db_connection, detect_psycopg
    _psycopg_mod, PSYCOPG_VERSION, _, _ = detect_psycopg()
    DB_AVAILABLE = _psycopg_mod is not None
except ImportError:
    DB_AVAILABLE = False
    PSYCOPG_VERSION = 0


def get_mcp_configs_from_db(project_name: str) -> Optional[Dict]:
    """Resolve full MCP config from DB using 3-layer merge.

    Layer 1: config_templates (global server configs)
    Layer 2: project_type_configs.default_mcp_servers (which globals to include)
    Layer 3: workspaces.startup_config.mcp_configs (project-specific overrides)

    Args:
        project_name: Name of the project in claude.workspaces

    Returns:
        Dict with 'mcp_configs' and 'enabled_servers' keys, or None if DB unavailable
    """
    if not DB_AVAILABLE:
        logger.info("Database not available, skipping DB lookup")
        return None

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.warning("Could not connect to database")
            return None

        cur = conn.cursor()

        # Step 1: Get workspace info (project_type, startup_config)
        cur.execute(
            "SELECT project_type, startup_config FROM claude.workspaces WHERE project_name = %s",
            (project_name,)
        )
        row = cur.fetchone()
        if not row:
            logger.warning(f"No workspace found for project '{project_name}'")
            return None

        project_type = row['project_type']
        startup_config = row['startup_config'] or {}

        # Step 2: Get default_mcp_servers for this project type
        cur.execute(
            "SELECT default_mcp_servers FROM claude.project_type_configs WHERE project_type = %s",
            (project_type,)
        )
        type_row = cur.fetchone()
        default_servers = type_row['default_mcp_servers'] if type_row else []
        if not default_servers:
            default_servers = []

        # Step 3: Resolve each default server name to its config_template
        merged_configs = {}
        for server_name in default_servers:
            template_name = f'mcp-{server_name}'
            cur.execute(
                "SELECT content FROM claude.config_templates WHERE template_name = %s",
                (template_name,)
            )
            tmpl_row = cur.fetchone()
            if tmpl_row and tmpl_row['content']:
                merged_configs[server_name] = dict(tmpl_row['content'])
                logger.info(f"Layer 1+2: Added '{server_name}' from template '{template_name}'")
            else:
                logger.warning(f"No config_template found for '{template_name}'")

        # Step 4: Overlay workspace-specific mcp_configs (Layer 3)
        workspace_mcp = startup_config.get('mcp_configs', {})
        if workspace_mcp:
            for server_name, server_config in workspace_mcp.items():
                merged_configs[server_name] = dict(server_config)
                logger.info(f"Layer 3: Added/overrode '{server_name}' from workspace config")

        # Step 5: Apply enabledMcpjsonServers filter if set
        enabled_servers = startup_config.get('enabledMcpjsonServers', [])

        # Step 5: Apply enabledMcpjsonServers filter to workspace servers only
        # Template defaults are always included; the filter only restricts workspace-specific servers
        enabled_filter = startup_config.get('enabledMcpjsonServers', [])
        if enabled_filter and workspace_mcp:
            for ws_name in list(merged_configs.keys()):
                if ws_name in workspace_mcp and ws_name not in enabled_filter:
                    del merged_configs[ws_name]
                    logger.info(f"Filtered out workspace server '{ws_name}' (not in enabledMcpjsonServers)")

        if not merged_configs:
            logger.info(f"No MCP configs resolved for project '{project_name}'")
            return None

        logger.info(
            f"DB merge complete for '{project_name}': "
            f"{len(default_servers)} defaults + {len(workspace_mcp)} workspace = "
            f"{len(merged_configs)} total servers"
        )

        return {
            'mcp_configs': merged_configs,
            'enabled_servers': [],  # Filtering already done in merge chain
        }

    except Exception as e:
        logger.error(f"Failed to get MCP configs from DB: {e}", exc_info=True)
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_mcp_configs_from_file(project_path: str) -> Optional[Dict]:
    """Read MCP configs from an existing .mcp.json file (fallback).

    Args:
        project_path: Path to the project directory

    Returns:
        Dict with 'mcp_configs' and 'enabled_servers' keys, or None if file missing
    """
    mcp_file = Path(project_path) / ".mcp.json"
    if not mcp_file.exists():
        logger.info(f"No .mcp.json found at {mcp_file}")
        return None

    try:
        with open(mcp_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        mcp_servers = data.get('mcpServers', {})
        if not mcp_servers:
            logger.info(f"No mcpServers in {mcp_file}")
            return None

        return {
            'mcp_configs': mcp_servers,
            'enabled_servers': []  # All servers enabled when reading from file
        }
    except Exception as e:
        logger.error(f"Failed to read .mcp.json: {e}")
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

    # Strip @version suffix for lookup (e.g., @mui/mcp@latest -> @mui/mcp)
    lookup_name = package_name.split('@latest')[0]
    # Handle scoped packages: @scope/pkg@version
    if lookup_name.startswith('@') and '@' in lookup_name[1:]:
        # e.g., @playwright/mcp@0.1.0 -> @playwright/mcp
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
        logger.info(f"Resolved {server_name}: npx {package_name} -> node {entry_point}")
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
        logger.info(f"Fallback wrapper for {server_name}: npx -> cmd /c npx (not globally installed)")
        return result

    return server_config


def generate_mcp_json(project_name: str, project_path: str) -> Optional[Dict]:
    """Generate .mcp.json from database with file fallback.

    Tries DB first (3-layer merge), falls back to existing .mcp.json file
    if DB is unavailable. Resolves npx commands to direct node paths.

    Args:
        project_name: Name of the project (for DB lookup and logging)
        project_path: Path to the project directory

    Returns:
        Dict ready to be written as .mcp.json, or None if no config found
    """
    logger.info(f"Generating MCP config for project: {project_name}")

    # Try DB first (3-layer merge)
    config_data = get_mcp_configs_from_db(project_name)
    source = "database"

    # Fall back to file if DB unavailable
    if not config_data:
        config_data = get_mcp_configs_from_file(project_path)
        source = "file"

    if not config_data:
        logger.warning(f"No MCP config found for project '{project_name}' (tried DB + file)")
        return None

    mcp_configs = config_data.get('mcp_configs', {})
    enabled_servers = config_data.get('enabled_servers', [])

    if not mcp_configs:
        logger.info(f"Project '{project_name}' has no MCP servers defined")
        return None

    # Build resolved mcpServers object
    mcp_servers = {}

    for server_name, server_config in mcp_configs.items():
        # Apply enabledMcpjsonServers filter (only when from DB with explicit filter)
        if enabled_servers and server_name not in enabled_servers:
            # Only filter workspace-specific servers, not template defaults
            # Template defaults (from default_mcp_servers) are always included
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
        return None

    result = {"mcpServers": mcp_servers}

    logger.info(
        f"Generated MCP config from {source} with servers: {list(mcp_servers.keys())}"
    )
    return result


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
        arg: Either a project directory path or a project name (uses cwd as path)

    Returns:
        Tuple of (project_name, project_path)
    """
    # Check if arg is a path to an existing directory
    if os.path.isdir(arg):
        project_path = os.path.abspath(arg)
        project_name = os.path.basename(project_path)
        return project_name, project_path

    # Treat as project name - use current working directory as path
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
        print("[SKIP] No MCP config found (no DB config and no existing .mcp.json)")
        return 0  # Not an error - project may not need MCP

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
