#!/usr/bin/env python3
"""
Cleanup orphaned MCP server processes from crashed Claude Code sessions.

When Claude Code crashes or is killed, its child MCP server processes
keep running as orphans. This script detects and kills them.

Detection logic:
  1. Find all python/node processes matching known MCP server patterns
  2. Group by command line (identical processes = duplicates)
  3. For each group with >1 process, keep the newest PID, kill older ones
  4. Kill processes from removed MCP servers (memory, filesystem)

Usage:
  python scripts/utilities/cleanup_orphaned_mcps.py          # Dry run (show what would be killed)
  python scripts/utilities/cleanup_orphaned_mcps.py --kill    # Actually kill orphans
  python scripts/utilities/cleanup_orphaned_mcps.py --all     # Kill ALL MCP processes (nuclear option)

Safety:
  - Default is dry-run (no --kill = just report)
  - Never kills claude-code CLI process itself
  - Groups by normalized command line to find true duplicates
  - Keeps the highest PID (newest) in each duplicate group
"""

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict


# MCP server patterns to look for
MCP_PATTERNS = [
    # Python MCP servers
    r"server\.py$",
    r"server_v2\.py$",
    r"mcp-server-fetch",
    r"mcp-server-postgres",
    # Node MCP servers
    r"server-sequential-thinking",
    r"server-memory",
    r"server-filesystem",
    r"@mui[\\/]mcp",
    r"@playwright[\\/]mcp",
    r"@anthropic-ai[\\/]mcp",
]

# Removed MCP servers - always kill these
REMOVED_SERVERS = [
    "server-memory",
    "server-filesystem",
]

# Never kill these
PROTECTED_PATTERNS = [
    r"claude-code[\\/]cli\.js",
    r"cleanup_orphaned_mcps\.py",
]


def get_processes():
    """Get all python.exe and node.exe processes with command lines."""
    processes = []
    try:
        result = subprocess.run(
            ["wmic", "process", "where",
             "name='python.exe' or name='node.exe'",
             "get", "ProcessId,CommandLine,CreationDate"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")
        # Skip header
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            # WMIC format: CommandLine followed by CreationDate and PID at the end
            # Parse PID from the end (last number)
            parts = line.rsplit(None, 2)
            if len(parts) >= 2:
                try:
                    pid = int(parts[-1])
                    # CreationDate is second from end (like 20260221...)
                    creation = parts[-2] if len(parts) >= 3 else ""
                    cmdline = line[:line.rfind(parts[-2])].strip() if len(parts) >= 3 else line[:line.rfind(str(pid))].strip()
                    processes.append({
                        "pid": pid,
                        "cmdline": cmdline,
                        "creation": creation,
                    })
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        print(f"Error getting processes: {e}", file=sys.stderr)
    return processes


def is_mcp_server(cmdline):
    """Check if a command line matches a known MCP server pattern."""
    for pattern in MCP_PATTERNS:
        if re.search(pattern, cmdline, re.IGNORECASE):
            return True
    return False


def is_removed_server(cmdline):
    """Check if process is from a removed MCP server."""
    for pattern in REMOVED_SERVERS:
        if pattern in cmdline.lower():
            return True
    return False


def is_protected(cmdline):
    """Check if process is protected from killing."""
    for pattern in PROTECTED_PATTERNS:
        if re.search(pattern, cmdline, re.IGNORECASE):
            return True
    return False


def normalize_cmdline(cmdline):
    """Normalize command line for grouping (remove path variations)."""
    # Normalize path separators
    normalized = cmdline.replace("\\", "/").lower()
    # Remove quotes
    normalized = normalized.replace('"', '').replace("'", '')
    # Collapse whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def main():
    parser = argparse.ArgumentParser(description="Cleanup orphaned MCP server processes")
    parser.add_argument("--kill", action="store_true", help="Actually kill orphans (default: dry run)")
    parser.add_argument("--all", action="store_true", help="Kill ALL MCP processes (nuclear option)")
    args = parser.parse_args()

    processes = get_processes()
    mcp_processes = [p for p in processes if is_mcp_server(p["cmdline"]) and not is_protected(p["cmdline"])]

    if not mcp_processes:
        print("No MCP server processes found.")
        return

    print(f"Found {len(mcp_processes)} MCP server processes:\n")

    # Group by normalized command line
    groups = defaultdict(list)
    for proc in mcp_processes:
        key = normalize_cmdline(proc["cmdline"])
        groups[key].append(proc)

    to_kill = []
    to_keep = []

    for key, procs in sorted(groups.items()):
        # Sort by PID descending (highest PID = newest)
        procs.sort(key=lambda p: p["pid"], reverse=True)

        if args.all:
            # Kill everything
            to_kill.extend(procs)
            continue

        # Check for removed servers - kill all instances
        if is_removed_server(procs[0]["cmdline"]):
            print(f"  REMOVED SERVER (kill all):")
            for p in procs:
                print(f"    PID {p['pid']}: {p['cmdline'][:100]}")
                to_kill.append(p)
            print()
            continue

        if len(procs) == 1:
            # Single instance - keep it
            to_keep.append(procs[0])
            print(f"  OK (single): PID {procs[0]['pid']}: {procs[0]['cmdline'][:100]}")
        else:
            # Duplicates - keep newest, kill rest
            print(f"  DUPLICATES ({len(procs)} instances):")
            to_keep.append(procs[0])
            print(f"    KEEP PID {procs[0]['pid']}: {procs[0]['cmdline'][:100]}")
            for p in procs[1:]:
                print(f"    KILL PID {p['pid']}: {p['cmdline'][:100]}")
                to_kill.append(p)
        print()

    print(f"\nSummary: {len(to_keep)} to keep, {len(to_kill)} to kill")

    if not to_kill:
        print("Nothing to clean up!")
        return

    if not args.kill:
        print("\nDry run - use --kill to actually terminate these processes.")
        return

    # Kill orphans
    killed = 0
    failed = 0
    for proc in to_kill:
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(proc["pid"])],
                capture_output=True, timeout=5
            )
            print(f"  Killed PID {proc['pid']}")
            killed += 1
        except Exception as e:
            print(f"  Failed to kill PID {proc['pid']}: {e}")
            failed += 1

    print(f"\nDone: {killed} killed, {failed} failed")


if __name__ == "__main__":
    main()
