# Python REPL MCP Installation & Investigation

**Date:** 2025-11-16
**Status:** Partially Complete

---

## ✅ Completed: python-repl MCP Installed

**Package installed successfully:**
```bash
C:/venvs/mcp/Scripts/pip install mcp-python
# Result: mcp-python-0.1.4 installed
```

**Executable location:**
```
C:/venvs/mcp/Scripts/mcp-python.exe
```

---

## ⏳ Pending: Add to MCP Configuration

**To complete installation, add to your `.mcp.json`:**

```json
{
  "mcpServers": {
    "python-repl": {
      "command": "C:/venvs/mcp/Scripts/mcp-python.exe",
      "type": "stdio"
    }
  }
}
```

**Where to add it:**
- Your MCP config location depends on isolated workspace setup
- Check `.mcp.json` in current working directory OR
- Check `~/.claude/.mcp.json` for global config
- You may need to add "python-repl" to `.claude/settings.local.json` `enabledMcpjsonServers` array

---

## 🔍 Investigation: Missing MCP Tools

### Issue
Two MCPs show as "Connected" in `claude mcp list` but don't expose tools in `/context`:
- **postgres** - Connected but no tools visible
- **orchestrator** - Connected but no tools visible

### Findings

**1. postgres MCP:**
- **Command:** `C:\venvs\mcp\Scripts\postgres-mcp.exe --access-mode=unrestricted`
- **Problem:** Missing database URL argument!
- **Fix Needed:** Add database connection string

**Expected format:**
```json
{
  "mcpServers": {
    "postgres": {
      "command": "C:/venvs/mcp/Scripts/postgres-mcp.exe",
      "args": [
        "--access-mode=unrestricted",
        "postgresql://user:password@localhost:5432/ai_company_foundation"
      ],
      "type": "stdio"
    }
  }
}
```

**Without a database URL, postgres MCP connects but has no database to query, so it exposes no tools.**

**2. orchestrator MCP:**
- **Command:** `C:\venvs\mcp\Scripts\python.exe C:\Projects\claude-family\mcp-servers\orchestrator\server.py`
- **Status:** Connected
- **Likely Reason:** Custom agent orchestrator designed to spawn sub-agents, not expose direct tools
- **Assessment:** This is probably intentional - orchestrator manages agents, not tools

---

## 📝 Recommended Actions

### High Priority
1. **Add python-repl to MCP config** (complete installation)
2. **Fix postgres MCP** - Add database URL so tools become available

### Low Priority
3. **Verify orchestrator** - Confirm it's working as designed (agent spawning, not tool exposure)

---

## 🎯 Benefits of python-repl MCP

Once configured, you'll be able to:
- Execute Python code snippets in a persistent REPL session
- Test database queries before adding to code
- Prototype Flet UI components interactively
- Debug SQL template generation logic
- Quick Python calculations and data transformations

**Perfect for Mission Control development!**

---

## Next Steps

1. Locate your active `.mcp.json` file
2. Add python-repl configuration
3. Restart Claude Code session
4. Verify with `/context` command - should see `mcp__python-repl__*` tools
5. Fix postgres MCP database URL if you need SQL tools exposed

---

**Created:** 2025-11-16
**By:** claude-code-unified
**Project:** claude-family (infrastructure)
