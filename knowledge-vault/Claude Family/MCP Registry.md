---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.762883'
---

# MCP Registry

Complete registry of all installed MCPs, project assignments, and installation guidelines.

---

## Installed MCPs

### postgres
**Purpose**: Database access to `ai_company_foundation`
**Tokens**: ~6k
**Package**: `postgres-mcp.exe` (custom build)

| Project | Status |
|---------|--------|
| claude-family | ✅ Global |
| ATO-Tax-Agent | ✅ Project |
| mission-control-web | ✅ Global |
| nimbus-import | ✅ Global |

---

### orchestrator
**Purpose**: Spawn specialized agents (14 types) + inter-Claude messaging
**Tokens**: ~9k
**Package**: Custom Python server (`mcp-servers/orchestrator/`)
**Full docs**: [[Orchestrator MCP]]

| Project             | Status    |
| ------------------- | --------- |
| claude-family       | ✅ Global  |
| ATO-Tax-Agent       | ✅ Project |
| mission-control-web | ✅ Global  |
| nimbus-import       | ✅ Global  |

---

### mui-mcp
**Purpose**: MUI X documentation and patterns
**Tokens**: ~2k
**Package**: `@mui/mcp@latest`

| Project             | Status        |
| ------------------- | ------------- |
| nimbus-import       | ✅ Project     |
| ATO-Tax-Agent       | ✅ Project     |
| mission-control-web | ❌ Uses shadcn |

---

### filesystem
**Purpose**: File operations via MCP
**Tokens**: ~9k (heavy!)
**Package**: `@modelcontextprotocol/server-filesystem`

| Project | Status |
|---------|--------|
| claude-family | ✅ Project-specific (in ~/.claude.json projects) |
| ATO-Tax-Agent | ❌ Not loaded |
| Others | ❌ Not loaded by default |

**Note**: Moved from global to project-specific to save tokens. Often unnecessary - built-in Read/Write/Edit tools work fine.

---

### memory
**Purpose**: Persistent entity graph
**Tokens**: ~6k
**Package**: `@modelcontextprotocol/server-memory`

| Project | Status |
|---------|--------|
| claude-family | ✅ Project-specific (in ~/.claude.json projects) |
| ATO-Tax-Agent | ❌ Not loaded (postgres preferred) |
| Others | ❌ Not loaded by default |

**Note**: Moved from global to project-specific. Consider using postgres tables instead for persistence.

---

### sequential-thinking
**Purpose**: Complex multi-step reasoning
**Tokens**: ~2k
**Package**: `@modelcontextprotocol/server-sequential-thinking`

| Project | Status |
|---------|--------|
| All | ✅ Global |

---

### python-repl
**Purpose**: Execute Python code
**Tokens**: ~2k
**Package**: `mcp-python.exe`

| Project | Status |
|---------|--------|
| claude-family | ✅ Global |
| ATO-Tax-Agent | ❌ Not needed |

---

## Installation Guidelines

### When to Install an MCP

**Ask these questions:**

1. **Is it needed globally or per-project?**
   - Global = every project benefits
   - Project = specific domain (e.g., MUI for React projects)

2. **What's the token cost?**
   - Under 3k = fine
   - 3-6k = consider if needed
   - Over 6k = only if essential

3. **Is there a built-in alternative?**
   - filesystem → Read/Write/Edit tools
   - memory → postgres tables
   - web fetch → WebFetch tool

---

### Installation Process

#### Step 1: Choose Scope

| Scope | Config File | Use When |
|-------|-------------|----------|
| **Global** | `~/.claude.json` mcpServers | Every project needs it |
| **Project** | `.mcp.json` in project root | Shared with team (git tracked) |
| **Local** | `~/.claude.json` projects[path].mcpServers | Just this machine |

#### Step 2: Add Config

**For npx packages (Windows):**
```json
{
  "mcp-name": {
    "type": "stdio",
    "command": "cmd",
    "args": ["/c", "npx", "-y", "@package/name@latest"],
    "env": {}
  }
}
```

**For exe/python:**
```json
{
  "mcp-name": {
    "type": "stdio",
    "command": "C:\\path\\to\\executable.exe",
    "args": ["--flags"],
    "env": {"VAR": "value"}
  }
}
```

#### Step 3: Enable in Settings

Add to `.claude/settings.local.json`:
```json
{
  "enabledMcpjsonServers": ["postgres", "orchestrator", "new-mcp"]
}
```

#### Step 4: Update Registry

1. Add entry to this vault note
2. Update `Claude Tools Reference.md`
3. Sync vault: `python scripts/sync_obsidian_to_db.py`

#### Step 5: Notify Other Projects

If global MCP, check each project:
- Does it need this MCP?
- Will it exceed token budget?
- Update project's `.claude/settings.local.json`

---

## Token Budget Guidelines

| Project Type | Target | Max |
|--------------|--------|-----|
| Simple tool | 15k | 20k |
| Full app | 20k | 25k |
| Infrastructure | 25k | 30k |

**Current ATO Budget:**
- postgres: ~6k
- orchestrator: ~9k
- mui-mcp: ~2k
- **Total: ~17k** ✅

---

## Config File Locations

| File | Path | Scope |
|------|------|-------|
| Global MCPs | `~/.claude.json` → `mcpServers` | All projects |
| Project MCPs | `{project}/.mcp.json` | Git-tracked, shared |
| Local overrides | `~/.claude.json` → `projects[path].mcpServers` | This machine only |
| Enabled list | `{project}/.claude/settings.local.json` | Which to load |

---

## Evaluation Checklist

Before adding MCP to a project:

- [ ] Token cost acceptable?
- [ ] No built-in alternative?
- [ ] Project actually needs it?
- [ ] Windows `cmd /c` wrapper added?
- [ ] Tested locally?
- [ ] Registry updated?
- [ ] Other Claudes notified?

See also: [[MCP configuration]], [[Setting's File]], [[Claude Tools Reference]]