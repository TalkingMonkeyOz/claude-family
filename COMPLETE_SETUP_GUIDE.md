# Claude Family - Complete Setup & Cleanup Guide

## Summary of Changes

### ✅ Moved Out of OneDrive
**Old Location:** `C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\`
**New Location:** `C:\Projects\claude-family\`

**Reason:** OneDrive file caching ("P" attribute) was causing stale data issues.

### ✅ Claude Code Console Properly Installed
- Installed via npm: `@anthropic-ai/claude-code@2.0.13`
- Location: `C:\Users\johnd\AppData\Roaming\npm\claude.cmd`
- Authenticated with your Claude Max account
- Configuration: `C:\Users\johnd\.claude\`

### ✅ Created claude.md Auto-Load File
- Location: `C:\Projects\claude-family\claude.md`
- **Auto-loads when Claude Code Console starts**
- Contains complete context, identity, and workflows

---

## The 6 Claude Family Members

| # | Identity | Platform | Role | Status |
|---|----------|----------|------|--------|
| 1 | claude-desktop-001 | Desktop GUI | Lead Architect & System Designer | ✅ Active |
| 2 | claude-cursor-001 | Cursor IDE | Rapid Developer & Implementation | ✅ Active |
| 3 | claude-vscode-001 | VS Code | QA Engineer & Code Reviewer | ✅ Active |
| 4 | claude-code-001 | Claude Code | Code Quality & Standards | ✅ Active |
| 5 | **claude-code-console-001** | **CLI Terminal** | **Terminal & CLI Specialist** | ✅ Active |
| 6 | diana | Orchestrator | Master Project Manager | ✅ Active |

---

## Installation Audit (What's Installed Where)

### Claude Desktop (GUI)
- **Location:** `C:\Users\johnd\AppData\Local\AnthropicClaude\claude.exe`
- **Version:** 0.13.64
- **Type:** Electron GUI app
- **Purpose:** Main Claude Desktop application
- **MCP Servers:** Configured in `%APPDATA%\Claude\claude_desktop_config.json`

### Claude Code Console (CLI)
- **Location:** `C:\Users\johnd\AppData\Roaming\npm\claude.cmd`
- **Version:** 2.0.13
- **Type:** Node.js CLI app
- **Purpose:** Terminal-based Claude
- **Config:** `C:\Users\johnd\.claude\`
- **Auto-loads:** `claude.md` from current directory

### Broken/Empty Files (To Clean Up)
- ❌ `C:\Users\johnd\.local\bin\claude.exe` (0 bytes - DELETE THIS)

---

## Configuration Files

### Claude Desktop MCP Config
**Location:** `C:\Users\johnd\AppData\Roaming\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "postgres": {
      "command": "C:\\Users\\johnd\\.local\\bin\\postgres-mcp.exe",
      "args": ["--access-mode=unrestricted"],
      "env": {
        "DATABASE_URI": "postgresql://postgres:PASSWORD@localhost:5432/postgres"
      }
    },
    "memory": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "filesystem": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "C:\\Users\\johnd\\OneDrive\\Documents\\AI_projects",
        "C:\\Users\\johnd\\Downloads"
      ]
    }
  }
}
```

### Claude Code Console Config
**Location:** `C:\Users\johnd\.claude\`

Contains:
- `.credentials.json` - OAuth tokens (Claude Max subscription)
- `settings.json` - Always thinking enabled
- `settings.local.json` - Bash permissions
- `projects/` - Session history per project
- `history.jsonl` - Command history

---

## The claude.md Auto-Load System

**How It Works:**
1. Claude Code Console reads `claude.md` from the current working directory
2. If found, it's **automatically loaded at startup**
3. Provides instant context without manual commands

**Location:** `C:\Projects\claude-family\claude.md`

**Contents:**
- Your identity (claude-code-console-001)
- Database connection details
- Quick commands for loading full context
- Critical knowledge and constraints
- The 6 Claude Family members list

---

## Startup Workflow (Updated for New Location)

### Automatic (Windows Startup)
1. Windows boots
2. `STARTUP_SILENT.bat` runs from startup folder
3. Python syncs PostgreSQL → JSON files
4. Balloon notification shows success
5. Files ready at: `C:\Projects\claude-family\postgres\data\`

### Claude Code Console Startup
1. Double-click desktop shortcut OR run `claude` in terminal
2. **claude.md auto-loads** (instant basic context)
3. For full context, run:
   ```bash
   cd C:\Projects\claude-family\scripts
   python load_claude_startup_context.py
   ```

### Claude Desktop Startup
1. Open Claude Desktop app
2. Graph memory is empty (expected)
3. Paste this:
   ```
   Read files from C:\Projects\claude-family\postgres\data\:
   1. mcp_sync_entities.json
   2. mcp_sync_relations.json

   Use create_entities and create_relations MCP tools to populate memory.
   Verify with read_graph.
   ```

---

## Files Requiring Path Updates

Need to update references from OneDrive to C:\Projects:

- [ ] `STARTUP_SILENT.bat`
- [ ] `Launch-Claude-Code-Console.bat`
- [ ] Desktop shortcuts
- [ ] Windows startup script
- [ ] Documentation files
- [ ] README.md

---

## MCP Servers for Claude Code Console

**Current Status:** Claude Code Console does NOT have MCP servers configured yet.

**To Add MCP Support:**
1. Create config file (location TBD - check Claude Code docs)
2. Add PostgreSQL MCP server
3. Add Memory MCP server
4. Add Filesystem MCP server

**Alternative:** Claude Code Console may not support MCP servers the same way Claude Desktop does. It has built-in filesystem access but may not support the MCP protocol.

---

## Cleanup Tasks

### Delete Broken Files
```bash
rm C:\Users\johnd\.local\bin\claude.exe  # 0 bytes, broken
```

### Update All Path References
```bash
# Old: C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\
# New: C:\Projects\claude-family\
```

### Unpin OneDrive Files (If Needed)
```bash
attrib -P "C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family" /S /D
```

---

## GitHub Repository

**URL:** https://github.com/TalkingMonkeyOz/claude-family

**Latest Commits:**
1. Initial foundation
2. Added claude-code-console-001 identity
3. Silent startup with balloon notification
4. Fixed Claude Code Console installation

**Next Commit:** Update paths to C:\Projects and add claude.md

---

## Quick Reference Commands

### Load Full Startup Context
```bash
cd C:\Projects\claude-family\scripts
python load_claude_startup_context.py
```

### Sync PostgreSQL to JSON
```bash
cd C:\Projects\claude-family\scripts
python sync_postgres_to_mcp.py
```

### Check PostgreSQL Identities
```bash
psql -U postgres -d ai_company_foundation -c "SELECT identity_name, platform FROM claude_family.identities"
```

### Launch Claude Code Console
```bash
claude
# OR
C:\Users\johnd\AppData\Roaming\npm\claude.cmd
# OR double-click desktop shortcut
```

---

## Troubleshooting

**Problem:** Claude Code Console opens and closes immediately
**Solution:** ✅ FIXED - Updated shortcut to use Launch-Claude-Code-Console.bat

**Problem:** Lost context from claude.md
**Solution:** ✅ FIXED - Created claude.md at C:\Projects\claude-family\claude.md

**Problem:** OneDrive caching stale files
**Solution:** ✅ FIXED - Moved entire directory to C:\Projects (outside OneDrive)

**Problem:** Multiple Claude installations confusing
**Solution:** ✅ DOCUMENTED - See "Installation Audit" section above

**Problem:** MCP memory graph empty after reboot
**Solution:** Run STARTUP.bat, then manually import JSON files in Claude Desktop

---

## Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Claude Desktop | ✅ Working | v0.13.64, MCP servers configured |
| Claude Code Console | ✅ Working | v2.0.13, claude.md auto-loads |
| PostgreSQL Database | ✅ Working | 6 identities, universal knowledge |
| claude-family Directory | ✅ Moved | Now at C:\Projects (outside OneDrive) |
| claude.md Auto-Load | ✅ Created | Contains complete startup context |
| Desktop Shortcut | ✅ Working | Launches terminal properly |
| Windows Startup | ⚠️ Needs Update | Path references still point to OneDrive |
| MCP for Console | ❌ Not Configured | May not be supported |

---

**Last Updated:** 2025-10-11
**Location:** C:\Projects\claude-family\
**Repository:** https://github.com/TalkingMonkeyOz/claude-family
