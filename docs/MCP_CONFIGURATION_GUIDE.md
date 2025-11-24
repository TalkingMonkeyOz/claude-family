# MCP Configuration Guide - Claude Family

**Created:** 2025-10-16
**Author:** claude-code-console-001
**Purpose:** Complete reference for MCP setup across Claude platforms

---

## Overview

Model Context Protocol (MCP) enables Claude to access external tools, databases, filesystems, and services. Both Claude Desktop and Claude Code Console support MCP through separate configuration files.

---

## Platform-Specific Configs

### Claude Desktop

**Config Location:**
```
C:\Users\{username}\AppData\Roaming\Claude\claude_desktop_config.json
```

**Format:**
```json
{
  "mcpServers": {
    "server-name": {
      "command": "path/to/executable",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

**Characteristics:**
- Global configuration (affects all Desktop sessions)
- Direct executable paths
- Trusted by default (all tools immediately available)
- Requires Desktop restart to reload

### Claude Code Console

**Config Location:**
```
{project-directory}/.mcp.json
```

**Format:**
```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@package/name"],
      "env": {}
    }
  }
}
```

**Characteristics:**
- Project-specific configuration (portable with repo)
- Uses `cmd /c npx` pattern for portability
- Permission-gated (tools require explicit approval)
- Reloads automatically when entering project directory

---

## Current Claude Family Configuration

### Shared MCP Servers (Both Platforms)

1. **postgres** - PostgreSQL database access
2. **memory** - Knowledge graph persistence
3. **filesystem** - File operations
4. **py-notes-server** - Note management
5. **github** - GitHub integration
6. **tree-sitter** - Code parsing/AST analysis
7. **sequential-thinking** - Methodical problem-solving
8. **playwright** - Browser automation using Playwright

### Configuration Differences

| Server | Desktop DB/Path | Console DB/Path | Why Different? |
|--------|----------------|-----------------|----------------|
| postgres | `postgres` (root) | `ai_company_foundation` | Desktop needs all DBs, Console focused on Family schema |
| filesystem | `AI_projects`, `Downloads` | `C:\Projects\claude-family` | Desktop unrestricted, Console project-scoped |
| github | Token in env | Token in env (fixed) | Both use env var now (security) |

---

## Configuration Examples

### PostgreSQL MCP Server

**Desktop:**
```json
{
  "postgres": {
    "command": "C:\\Users\\johnd\\.local\\bin\\postgres-mcp.exe",
    "args": ["--access-mode=unrestricted"],
    "env": {
      "DATABASE_URI": "postgresql://user:pass@localhost:5432/postgres"
    }
  }
}
```

**Console:**
```json
{
  "postgres": {
    "type": "stdio",
    "command": "cmd",
    "args": [
      "/c",
      "npx",
      "-y",
      "@modelcontextprotocol/server-postgres",
      "postgresql://user:pass@localhost/ai_company_foundation"
    ],
    "env": {}
  }
}
```

**Key Differences:**
- Desktop uses native executable (`postgres-mcp.exe`)
- Console uses npx for portability
- Different databases (root vs specific)

### Filesystem MCP Server

**Desktop:**
```json
{
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
```

**Console:**
```json
{
  "filesystem": {
    "type": "stdio",
    "command": "cmd",
    "args": [
      "/c",
      "npx",
      "-y",
      "@modelcontextprotocol/server-filesystem",
      "C:\\Projects"
    ],
    "env": {}
  }
}
```

**Key Differences:**
- Desktop has multiple paths (unrestricted access)
- Console restricted to project directory tree
- Security model differs (Desktop trusted, Console sandboxed)

### GitHub MCP Server (Secure)

**Both Platforms (Environment Variable Approach):**

```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {}
  }
}
```

**Setup:**
```powershell
# Set environment variable (persistent)
[System.Environment]::SetEnvironmentVariable(
    'GITHUB_PERSONAL_ACCESS_TOKEN',
    'your_token_here',
    [System.EnvironmentVariableTarget]::User
)
```

**Why This Works:**
- MCP GitHub server reads `GITHUB_PERSONAL_ACCESS_TOKEN` from environment
- Token not hardcoded in config files
- Safe to commit configs to git

### Tree-Sitter MCP Server

**Desktop:**
```json
{
  "tree-sitter": {
    "command": "C:\\venvs\\mcp\\Scripts\\mcp-server-tree-sitter.exe"
  }
}
```

**Console:**
```json
{
  "tree-sitter": {
    "type": "stdio",
    "command": "C:\\venvs\\mcp\\Scripts\\mcp-server-tree-sitter.exe",
    "args": [],
    "env": {}
  }
}
```

**Key Differences:**
- Same executable path (installed once, shared)
- Console adds `type: stdio` (required for Console)
- Both work identically

### Playwright MCP Server

**Desktop:**
```json
{
  "playwright": {
    "command": "C:\\Program Files\\nodejs\\npx.cmd",
    "args": [
      "-y",
      "@playwright/mcp@latest"
    ]
  }
}
```

**Console:**
```json
{
  "playwright": {
    "type": "stdio",
    "command": "cmd",
    "args": [
      "/c",
      "npx",
      "-y",
      "@playwright/mcp@latest"
    ],
    "env": {}
  }
}
```

**Key Features:**
- Browser automation via Playwright
- Uses accessibility tree snapshots (no screenshots needed)
- Web navigation, form-filling, data extraction
- Automated testing driven by LLMs
- Installed: 2025-10-31

---

## Permission Management (Console Only)

### Permission File Location

```
~/.claude/settings.local.json
```

### Pre-Approve All MCP Tools

```json
{
  "permissions": {
    "allow": [
      "mcp__postgres__*",
      "mcp__memory__*",
      "mcp__filesystem__*",
      "mcp__py-notes-server__*",
      "mcp__github__*",
      "mcp__tree-sitter__*",
      "mcp__sequential-thinking__*",
      "mcp__playwright__*"
    ],
    "deny": [],
    "ask": []
  }
}
```

### Granular Permissions

```json
{
  "permissions": {
    "allow": [
      "mcp__postgres__query",
      "mcp__memory__read_graph",
      "mcp__filesystem__list_allowed_directories"
    ],
    "ask": [
      "mcp__filesystem__write_file",
      "mcp__postgres__*"
    ]
  }
}
```

---

## Troubleshooting

### MCP Server Won't Connect

**Check Logs:**
```bash
# Desktop logs
%APPDATA%\Claude\logs\mcp-server-{name}.log

# Console logs
~/.claude/debug/latest
```

**Common Issues:**
1. Executable not found → Check paths
2. Permission denied → Run as admin or fix file permissions
3. Port conflict → Check if another instance running
4. Dependencies missing → Install required packages

### Tool Not Appearing in Console

**Diagnosis:**
1. Check if server connected: Review `~/.claude/debug/latest`
2. Look for `[DEBUG] MCP server "name": Successfully connected`
3. Check capabilities: `Connection established with capabilities: {...}`
4. If connected but tools hidden → Permission issue

**Solution:**
- Add tool to `~/.claude/settings.local.json` allow list
- OR wait for first use permission prompt

### Desktop and Console Conflicts

**Symptoms:**
- Changes in one affect the other
- Servers fail to start
- Database lock errors

**Reality:**
This shouldn't happen! Configs are completely isolated.

**If it does happen:**
1. Verify separate config files exist
2. Check database connection strings (should be different)
3. Ensure filesystem paths don't overlap write operations
4. Check if same port being used by multiple servers

---

## Best Practices

### 1. Keep Configs Separate

**Don't:**
- Share config files between platforms
- Symlink Desktop config to Console config
- Use same database connection for both

**Do:**
- Maintain separate configs
- Use different databases or schemas per platform
- Document differences in comments

### 2. Use Environment Variables for Secrets

**Don't:**
```json
{
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_hardcoded_token"
  }
}
```

**Do:**
```json
{
  "env": {}
}
```

Then set system environment variable.

### 3. Version Control Strategy

**Commit to Git:**
- `.mcp.json.template` (with placeholders)
- Documentation about how to configure
- Setup scripts

**Don't Commit:**
- `.mcp.json` (if it contains secrets or machine-specific paths)
- Desktop config (machine-specific)

**Gitignore:**
```
# MCP configs with secrets
.mcp.json

# But allow template
!.mcp.json.template
```

### 4. Template Approach

**Create `.mcp.json.template`:**
```json
{
  "mcpServers": {
    "postgres": {
      "type": "stdio",
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://USER:PASS@localhost/DATABASE"
      ],
      "env": {}
    },
    "github": {
      "type": "stdio",
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<SET_VIA_ENVIRONMENT_VARIABLE>"
      }
    }
  }
}
```

**Setup Script:**
```bash
#!/bin/bash
# Generate .mcp.json from template
cp .mcp.json.template .mcp.json

# Prompt for values
read -p "PostgreSQL password: " PG_PASS
sed -i "s/USER:PASS/postgres:$PG_PASS/" .mcp.json

echo "✓ .mcp.json generated from template"
echo "! Set GITHUB_PERSONAL_ACCESS_TOKEN environment variable"
```

### 5. Testing MCP Servers

**Before Adding to Config:**
```bash
# Test server manually
npx -y @modelcontextprotocol/server-github

# Should output server info, not errors
```

**After Adding to Config:**
```bash
# Desktop: Restart app
# Console: cd into project directory

# Try using a tool from the server
# Check logs if it fails
```

---

## Migration Guide

### From Desktop-Only to Multi-Platform

**Step 1: Document Desktop Config**
```bash
# Backup Desktop config
cp "%APPDATA%\Claude\claude_desktop_config.json" ./desktop-config-backup.json
```

**Step 2: Create Console Config**
```bash
# Start with template
cp .mcp.json.template .mcp.json

# Adapt server definitions
# - Change paths to portable (npx)
# - Change databases to project-specific
# - Remove machine-specific paths
```

**Step 3: Test Isolation**
```bash
# Start both platforms
# Verify they don't conflict
# Check logs for connection issues
```

### From Console to Desktop

If you have a working Console setup and want to add Desktop:

**Step 1: Create Desktop Config**
```json
{
  "mcpServers": {
    // Copy from Console .mcp.json
    // Remove "type": "stdio"
    // Change cmd /c npx to direct npx path
    // Update database/filesystem paths for Desktop scope
  }
}
```

**Step 2: Restart Desktop**
```
File → Quit Claude Desktop
Relaunch
```

**Step 3: Verify**
```
Settings → Features → MCP Servers
Should show all servers as connected
```

---

## Quick Reference

### Console MCP Setup Checklist

- [ ] Create `.mcp.json` in project root
- [ ] Add MCP servers with `type: stdio`
- [ ] Use `cmd /c npx` pattern for portability
- [ ] Set environment variables for secrets
- [ ] Pre-approve tools in `~/.claude/settings.local.json`
- [ ] Test with simple query
- [ ] Check `~/.claude/debug/latest` for connection confirmation

### Desktop MCP Setup Checklist

- [ ] Edit `%APPDATA%\Claude\claude_desktop_config.json`
- [ ] Use direct executable paths
- [ ] Set environment variables for secrets
- [ ] Restart Desktop app
- [ ] Check Settings → Features → MCP Servers
- [ ] Check `%APPDATA%\Claude\logs\` for errors

---

## Resources

- **MCP Documentation:** https://modelcontextprotocol.io/
- **MCP Server Registry:** https://github.com/modelcontextprotocol/servers
- **Claude Code Docs:** https://docs.claude.com/claude-code
- **Family Security Guide:** `./GITHUB_TOKEN_SECURITY.md`
- **Reality Check:** `../REALITY_CHECK_UPDATED_2025-10-16.md`

---

**Last Updated:** 2025-10-16
**Author:** claude-code-console-001
**Status:** ✅ Complete and tested
