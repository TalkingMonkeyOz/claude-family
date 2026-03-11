---
title: MCP Windows npx Wrapper Pattern
created: 2026-01-02
updated: 2026-01-02
tags: [mcp, windows, npx, process-management, crash-fix]
category: patterns
status: active
severity: critical
---

# MCP Windows npx Wrapper Pattern

## Critical Issue ⚠️

**Problem**: Claude Code crashes when dev servers (Vite, webpack, etc.) are closed

**Symptom**: MCP servers (memory, filesystem, sequential-thinking) get killed, causing immediate Claude crash

**Impact**: Loss of context, interrupted work, todos/session state lost

## Root Cause

On Windows, when `npx` is called directly in MCP configuration, the spawned Node.js processes become child processes of the Claude Code session. When a dev server terminal is closed, Windows kills all child processes in the process group, including unrelated MCP servers.

**Broken Pattern**:
```json
{
  "memory": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-memory"]
  }
}
```

## Solution Pattern

Use `cmd /c` wrapper to isolate the process:

```json
{
  "memory": {
    "type": "stdio",
    "command": "cmd",
    "args": [
      "/c",
      "npx",
      "-y",
      "@modelcontextprotocol/server-memory"
    ]
  }
}
```

**Why This Works**:
- `cmd /c` creates a new command interpreter
- The Node.js process is a child of `cmd.exe`, not the parent Claude session
- Process isolation prevents cascade termination

## Affected MCP Servers

Any MCP server using `npx`:
- ✅ `@modelcontextprotocol/server-memory`
- ✅ `@modelcontextprotocol/server-filesystem`
- ✅ `@modelcontextprotocol/server-sequential-thinking`
- ✅ `@mui/mcp` (project-specific)
- ⚠️ Any custom npx-based MCP servers

## Fix Locations

### Global Config
File: `~/.claude/mcp.json`

Apply to all npx-based MCPs.

### Project-Specific Configs
File: `{project}/.mcp.json`

Check these projects:
- ✅ nimbus-mui (fixed 2026-01-02)
- ✅ claude-manager-mui (fixed 2026-01-02)
- ⚠️ Other React/Tauri projects

## History

- **Oct 2025**: Original fix applied (commit `fd95b69`)
- **Dec 2025**: Fix accidentally reverted during config cleanup
- **Jan 2026**: Issue rediscovered, fix reapplied permanently

## Prevention

When adding new MCP servers via npx:

1. **ALWAYS** use `cmd /c` wrapper on Windows
2. Test by starting/stopping dev servers - Claude should NOT crash
3. Document in vault if new npx MCP pattern discovered

## Validation

After applying fix:

```bash
# 1. Start Claude Code
# 2. Start a dev server (npm run dev, tauri:dev, etc.)
# 3. Close the dev server terminal
# 4. Claude should remain running ✅
```

## Alternative Solutions Considered

❌ **Using npx.cmd full path**: Inconsistent, not portable
❌ **Global npm install**: Defeats MCP's auto-update via npx
❌ **Custom shell scripts**: Adds complexity, maintenance burden
✅ **cmd /c wrapper**: Simple, portable, Windows-standard

## Related Issues

- [[Tauri Multiple Instances Port Isolation]] - Separate Tauri port conflict issue
- [[Add MCP Server SOP]] - MCP configuration best practices

## References

- Original Fix: Commit `fd95b69` (2025-10-11)
- MCP Specification: https://modelcontextprotocol.io/
- Windows Process Management: https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/cmd

## Keywords

mcp, windows, npx, crash, process-management, cmd, child-process, isolation, dev-server
