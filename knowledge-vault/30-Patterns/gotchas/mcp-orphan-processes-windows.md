---
created: 2025-12-21
category: mcp
tags:
- mcp
- windows
- gotcha
- process-management
---

# MCP Orphan Processes on Windows

## Summary

Claude Code spawns MCP servers as child processes but doesn't properly terminate them when sessions end on Windows. This causes process accumulation.

## Symptoms

- Multiple instances of same MCP server running
- Node processes accumulate over sessions
- Folders locked by orphaned processes
- Memory usage increases over time

## Root Cause

When Claude Code exits on Windows:
1. Parent process (claude CLI) terminates
2. Child processes (MCP servers spawned via `npx -y`) continue running
3. These become orphaned processes
4. Next session spawns NEW MCPs, leaving old ones running

## Solution

Added `cleanup_mcp_processes.py` to SessionEnd hook:
- Detects duplicate MCP server processes
- Keeps one instance of each type
- Terminates orphaned duplicates

**Location**: `.claude-plugins/claude-family-core/scripts/cleanup_mcp_processes.py`

## Manual Cleanup

Run to see orphans:
```bash
python cleanup_mcp_processes.py --dry-run
```

Run to kill orphans:
```bash
python cleanup_mcp_processes.py
```

Kill all MCPs (aggressive):
```bash
python cleanup_mcp_processes.py --aggressive
```

## Related

- Hook added to: `.claude/hooks.json` (SessionEnd)
- Affects: All projects using MCP servers on Windows

---

**Created**: 2025-12-21
**Issue**: Claude Code doesn't terminate child processes on Windows
