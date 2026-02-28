#!/usr/bin/env python3
"""
Generate MCP Config - .mcp.json Resolver

Reads MCP server configuration from an existing .mcp.json file and resolves
npx packages to direct node paths for faster startup.

Architecture:
    .mcp.json (Source of Truth - edit directly or via DB workspaces.startup_config)
        ↓
    generate_mcp_config.py (resolves npx → direct node paths)
        ↓
    .mcp.json (Updated in-place with resolved paths)

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

# No database dependency - reads directly from .mcp.json files


def get_mcp_configs_from_file(project_path: str) -> Optional[Dict]:
    """Read MCP configs from an existing .mcp.json file.

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
    """Resolve npx commands in .mcp.json to direct node paths.

    Reads the existing .mcp.json in the project directory and resolves any
    npx-based server commands to direct node invocations for faster startup.

    Args:
        project_name: Name of the project (for logging)
        project_path: Path to the project directory

    Returns:
        Dict ready to be written as .mcp.json, or None if no .mcp.json found
    """
    logger.info(f"Resolving MCP config for project: {project_name}")

    # Read from existing .mcp.json file
    config_data = get_mcp_configs_from_file(project_path)
    if not config_data:
        logger.warning(f"No .mcp.json found for project '{project_name}'")
        return None

    mcp_configs = config_data.get('mcp_configs', {})
    enabled_servers = config_data.get('enabled_servers', [])

    if not mcp_configs:
        logger.info(f"Project '{project_name}' has no mcpServers defined")
        return None

    # Build resolved mcpServers object
    mcp_servers = {}

    for server_name, server_config in mcp_configs.items():
        # Only include enabled servers if a filter is specified
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
        return None

    # Preserve any top-level metadata from the original file, update mcpServers
    original_file = Path(project_path) / ".mcp.json"
    result = {}
    try:
        with open(original_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
    except Exception:
        pass

    result["mcpServers"] = mcp_servers

    logger.info(f"Resolved MCP config with servers: {list(mcp_servers.keys())}")
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
        print("[SKIP] No MCP config to resolve (no .mcp.json found in project directory)")
        return 0  # Not an error - project just doesn't have .mcp.json yet

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
