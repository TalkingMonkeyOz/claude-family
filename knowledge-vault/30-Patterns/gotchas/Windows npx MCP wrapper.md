---
projects:
- claude-family
- ATO-Infrastructure
tags:
- gotcha
- windows
- mcp
- npx
synced: false
---

# Windows npx MCP Wrapper Gotcha

On Windows, MCP servers using `npx` must be wrapped with `cmd /c`.

---

## The Problem

When configuring an MCP server in `.mcp.json` on Windows:

```json
{
  "mcpServers": {
    "azure": {
      "command": "npx",
      "args": ["-y", "@azure/mcp-server"]
    }
  }
}
```

Claude Code shows a warning:
> [Warning] Windows requires 'cmd /c' wrapper to execute npx

---

## The Fix

Wrap npx with `cmd /c`:

```json
{
  "mcpServers": {
    "azure": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@azure/mcp-server"]
    }
  }
}
```

---

## Automatic Fix

The SessionStart hook now **automatically fixes** this issue.

When a session starts, `fix_windows_npx_commands()` in `session_startup_hook.py`:
1. Checks if running on Windows
2. Reads `.mcp.json` in project directory
3. Finds any servers with `"command": "npx"`
4. Automatically converts to `cmd /c npx` wrapper
5. Saves the updated config

You'll see this message if it fixes anything:
```
[AUTO-FIX] Fixed 1 MCP server(s) with Windows npx wrapper
```

---

## Why This Happens

Windows doesn't have a native shell that can directly execute npm/npx commands like Unix shells can. The `cmd /c` wrapper tells Windows to:
1. Open a command interpreter (`cmd`)
2. Execute the command (`/c`)
3. Exit when done

---

## Related

- [[Add MCP Server SOP]] - When adding new MCP servers
- [[MCP Registry]] - List of all MCP servers

---

**Version**: 1.0
**Created**: 2026-01-03
**Updated**: 2026-01-03
**Location**: knowledge-vault/30-Patterns/gotchas/Windows npx MCP wrapper.md
