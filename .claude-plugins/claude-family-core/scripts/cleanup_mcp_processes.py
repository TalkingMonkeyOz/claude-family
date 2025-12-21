#!/usr/bin/env python3
"""
MCP Process Cleanup Script

Terminates orphaned MCP server processes that weren't cleaned up when
Claude sessions ended. This is a workaround for Claude Code not properly
terminating its child processes on Windows.

Called by SessionEnd hook to prevent process accumulation.

Usage:
    python cleanup_mcp_processes.py [--dry-run]

Exit codes:
    0 = Success
    1 = Error
"""

import json
import subprocess
import sys
import os
import re

# MCP servers we manage (patterns to match in command line)
MCP_PATTERNS = [
    '@modelcontextprotocol/server-memory',
    '@modelcontextprotocol/server-sequential-thinking',
    '@modelcontextprotocol/server-filesystem',
    '@mui/mcp',
    'ollama-mcp',
    'postgres-mcp',
]

# Patterns for npx launchers
NPX_PATTERNS = [
    'npx-cli.js',
    'npx.cmd',
]

def get_node_processes():
    """Get all node processes with their command lines."""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-CimInstance Win32_Process -Filter "Name=\'node.exe\'" | '
             'Select-Object ProcessId, ParentProcessId, CommandLine | '
             'ConvertTo-Json'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)
        # Handle single result vs array
        if isinstance(data, dict):
            return [data]
        return data or []
    except Exception as e:
        print(f"Error getting processes: {e}", file=sys.stderr)
        return []

def is_mcp_process(cmd_line):
    """Check if a process is an MCP server."""
    if not cmd_line:
        return False

    for pattern in MCP_PATTERNS:
        if pattern in cmd_line:
            return True
    return False

def is_npx_launcher(cmd_line):
    """Check if a process is an npx launcher for MCP."""
    if not cmd_line:
        return False

    for pattern in NPX_PATTERNS:
        if pattern in cmd_line:
            # Check if it's launching an MCP
            for mcp in MCP_PATTERNS:
                if mcp in cmd_line:
                    return True
    return False

def is_claude_session(cmd_line):
    """Check if a process is a Claude Code CLI session."""
    if not cmd_line:
        return False
    return 'claude-code' in cmd_line or '@anthropic-ai\\claude-code' in cmd_line

def get_active_claude_pids(processes):
    """Get PIDs of currently running Claude sessions."""
    return [p['ProcessId'] for p in processes if is_claude_session(p.get('CommandLine', ''))]

def find_orphaned_mcps(processes, keep_one_per_type=True):
    """Find MCP processes that should be terminated."""
    orphans = []
    seen_types = {}

    claude_pids = get_active_claude_pids(processes)

    for proc in processes:
        cmd = proc.get('CommandLine', '')
        pid = proc.get('ProcessId')
        parent_pid = proc.get('ParentProcessId')

        if is_mcp_process(cmd) or is_npx_launcher(cmd):
            # Determine MCP type
            mcp_type = None
            for pattern in MCP_PATTERNS:
                if pattern in cmd:
                    mcp_type = pattern
                    break

            if keep_one_per_type:
                # Keep the first instance of each type, mark rest as orphans
                if mcp_type:
                    if mcp_type not in seen_types:
                        seen_types[mcp_type] = pid
                    else:
                        orphans.append({
                            'pid': pid,
                            'type': mcp_type,
                            'cmd': cmd[:100] + '...' if len(cmd) > 100 else cmd
                        })
            else:
                # Mark all as orphans (aggressive cleanup)
                orphans.append({
                    'pid': pid,
                    'type': mcp_type or 'unknown',
                    'cmd': cmd[:100] + '...' if len(cmd) > 100 else cmd
                })

    return orphans

def kill_process(pid):
    """Terminate a process by PID."""
    try:
        result = subprocess.run(
            ['taskkill', '/F', '/PID', str(pid)],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error killing PID {pid}: {e}", file=sys.stderr)
        return False

def main():
    dry_run = '--dry-run' in sys.argv
    aggressive = '--aggressive' in sys.argv  # Kill all, not just duplicates

    processes = get_node_processes()
    if not processes:
        result = {"decision": "allow", "message": "No node processes found"}
        print(json.dumps(result))
        return 0

    orphans = find_orphaned_mcps(processes, keep_one_per_type=not aggressive)

    if not orphans:
        result = {"decision": "allow", "message": "No orphaned MCP processes found"}
        print(json.dumps(result))
        return 0

    killed = []
    failed = []

    for orphan in orphans:
        if dry_run:
            killed.append(orphan)
        else:
            if kill_process(orphan['pid']):
                killed.append(orphan)
            else:
                failed.append(orphan)

    result = {
        "decision": "allow",
        "message": f"Cleaned up {len(killed)} orphaned MCP processes",
        "killed": [f"PID {o['pid']} ({o['type']})" for o in killed],
        "failed": [f"PID {o['pid']}" for o in failed] if failed else None,
        "dry_run": dry_run
    }

    # Remove None values
    result = {k: v for k, v in result.items() if v is not None}

    print(json.dumps(result, indent=2))
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
