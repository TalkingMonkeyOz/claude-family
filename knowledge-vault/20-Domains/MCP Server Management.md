---
title: MCP Server Management
category: domain-knowledge
domain: claude-code
created: 2025-12-28
updated: 2026-02-10
tags:
  - mcp
  - configuration
  - claude-code
  - servers
status: active
---

# MCP Server Management

**Domain**: Model Context Protocol (MCP)
**Purpose**: Understanding and managing MCP servers for Claude Code

---

## What Are MCP Servers?

MCP (Model Context Protocol) servers extend Claude Code's capabilities by providing:
- External tool integrations (databases, APIs, file systems)
- Specialized knowledge (documentation, code examples)
- Domain-specific functionality (Tailwind CSS, Material-UI, Playwright)

---

## MCP Architecture

```
Claude Code
    ↓
MCP Client (built-in)
    ↓
MCP Servers (stdio communication)
    ↓
External Resources (DB, APIs, docs, etc.)
```

**Key Concepts:**
- **stdio**: Standard input/output communication
- **npx**: Node package executor (on-demand installation)
- **Environment variables**: Configuration (DB URIs, API keys)

---

## Configuration Levels

### 1. Global MCPs (~/.claude/mcp.json)
**Scope**: Available to ALL Claude sessions
**Use For**: Core infrastructure (postgres, memory, filesystem)

**Example:**
```json
{
  "mcpServers": {
    "postgres": {
      "type": "stdio",
      "command": "C:/venvs/mcp/Scripts/postgres-mcp.exe",
      "args": ["--access-mode=unrestricted"],
      "env": {
        "DATABASE_URI": "postgresql://..."
      }
    }
  }
}
```

**Best Practice**: Keep minimal - only truly universal MCPs

---

### 2. Project MCPs (project/.mcp.json)
**Scope**: Specific project only
**Use For**: Tech stack-specific tools (Tailwind, MUI, etc.)

**Example:**
```json
{
  "mcpServers": {
    "tailwindcss": {
      "type": "stdio",
      "command": "cmd",
      "args": ["/c", "npx", "-y", "tailwindcss-mcp-server"],
      "env": {}
    }
  }
}
```

**Best Practice**: Only include MCPs needed for this tech stack

---

## Windows-Specific Configuration

### Issue: npx Requires cmd /c Wrapper

**Problem:**
```json
{
  "command": "npx",
  "args": ["-y", "package-name"]
}
```

**Error**: `Windows requires 'cmd /c' wrapper to execute npx`

**Solution:**
```json
{
  "command": "cmd",
  "args": ["/c", "npx", "-y", "package-name"]
}
```

**Why**: Windows shell doesn't execute npx directly; needs cmd.exe wrapper

---

## MCP Lifecycle Management

### Database Tracking

**Table**: `claude.mcp_configs`

**Columns:**
- `project_name`: Which project uses this MCP
- `mcp_server_name`: Identifier (e.g., "tailwindcss", "mui")
- `mcp_package`: npm package or executable path
- `is_active`: Currently enabled?
- `install_date`: When added
- `removal_date`: When deactivated
- `reason`: Why this MCP is needed

**Benefits:**
- Track MCP usage across projects
- Audit which MCPs are actually used
- Document why each MCP was added

---

### Workspaces Integration

**Table**: `claude.workspaces`
**Column**: `startup_config->'mcp_servers'`

**Example:**
```sql
UPDATE claude.workspaces
SET startup_config = jsonb_set(
  startup_config,
  '{mcp_servers}',
  '["tailwindcss", "playwright"]'::jsonb
)
WHERE project_name = 'finance-htmx';
```

**Purpose**: Link project to its required MCPs

---

## Common MCP Servers

### Infrastructure (Global)

| MCP | Package | Purpose |
|-----|---------|---------|
| **postgres** | `postgres-mcp` | Database access, schema introspection |
| **project-tools** | Custom Python | Work tracking, knowledge, config ops, conversations, books (40+ tools) |
| **sequential-thinking** | `@modelcontextprotocol/server-sequential-thinking` | Complex reasoning |
| **orchestrator** | Custom Python | Agent spawning, messaging |
| ~~memory~~ | ~~`@modelcontextprotocol/server-memory`~~ | Removed 2026-01 (replaced by project-tools knowledge) |
| ~~filesystem~~ | ~~`@modelcontextprotocol/server-filesystem`~~ | Removed 2026-01 (Claude has built-in Read/Write/Edit) |

### project-tools v3 Tool Categories

The project-tools MCP evolved from a CRUD wrapper (v1) to a workflow engine (v2) to a comprehensive operations platform (v3).

**Four Pillars** (15 new tools in v3):

| Pillar | Tools | Purpose |
|--------|-------|---------|
| **P0: Conversations** | extract_conversation, search_conversations, extract_insights | Extract and search session JSONL logs |
| **P1: Config Ops** | update_claude_md, deploy_claude_md, deploy_project, regenerate_settings | File+DB atomic config operations |
| **P2: Knowledge** | store_book, store_book_reference, recall_book_reference + enhanced recall | Structured knowledge with embeddings |
| **P3: Work Tracking** | Enhanced create_linked_task, start_session, end_session | Richer context, auto-extraction |

**Total**: 40+ tools (27 from v2 + 15 new in v3)

**See**: [[Application Layer v3]] for detailed architecture.

---

### Tech Stack Specific (Project)

| MCP | Package | Use Case |
|-----|---------|----------|
| **tailwindcss** | `tailwindcss-mcp-server` | Tailwind/DaisyUI projects |
| **mui** | `@mui/mcp@latest` | React + Material-UI projects |
| **playwright** | `@playwright/mcp` | Browser automation (or use orchestrator agent) |

---

## Research: Playwright MCP vs Orchestrator Agent

### Issue Discovered: 2025-12-28

**Context**: Both projects (finance-htmx, finance-mui) had Playwright MCP configured.

**Problem**: Redundant - orchestrator already has playwright agent

**Analysis:**

**Option 1: Playwright MCP**
- ✅ Direct browser control
- ✅ Integrated in session
- ❌ Another process to manage
- ❌ Context overhead (~14k tokens)

**Option 2: Orchestrator Playwright Agent**
- ✅ Spawns on-demand
- ✅ No context overhead when not in use
- ✅ Proven to work well
- ❌ Slight spawn delay

**Decision**: Use orchestrator agent, remove MCP

**Implementation:**
```python
# Instead of Playwright MCP
mcp__orchestrator__spawn_agent(
  agent_type="web-tester-haiku",
  task="Test HTMX form submission",
  workspace_dir="C:/Projects/finance-htmx"
)
```

**Result:**
- finance-htmx: Only `tailwindcss` MCP
- finance-mui: Only `mui` MCP
- Both use orchestrator for testing

---

## MCP Configuration Patterns

### Pattern 1: Tailwind/DaisyUI Stack

**Project Type**: HTMX + Alpine.js + DaisyUI

**Required MCP:**
```json
{
  "tailwindcss": {
    "type": "stdio",
    "command": "cmd",
    "args": ["/c", "npx", "-y", "tailwindcss-mcp-server"],
    "metadata": {
      "description": "Tailwind utilities and DaisyUI docs",
      "why_needed": "DaisyUI is Tailwind-based"
    }
  }
}
```

**Use Cases:**
- "Show me a DaisyUI card component"
- "Convert this CSS to Tailwind classes"
- "What's the DaisyUI color palette?"

---

### Pattern 2: React + MUI Stack

**Project Type**: React + TypeScript + Material-UI

**Required MCP:**
```json
{
  "mui": {
    "type": "stdio",
    "command": "cmd",
    "args": ["/c", "npx", "-y", "@mui/mcp@latest"],
    "metadata": {
      "description": "Official MUI component docs",
      "why_needed": "DataGrid, Charts, DatePicker APIs"
    }
  }
}
```

**Use Cases:**
- "Show me DataGrid column definition API"
- "How do I use MUI-X DatePicker?"
- "What props does the Card component accept?"

---

### Pattern 3: Full-Stack with Database

**Project Type**: Any project with PostgreSQL

**Global MCPs:**
- postgres (database queries)
- project-tools (work tracking, knowledge persistence)

**Project MCPs:**
- Tech stack specific (as above)

**Workflow:**
1. Query database via postgres MCP
2. Generate code using tech stack MCP (Tailwind/MUI)
3. Store learned patterns via project-tools knowledge functions

---

## Best Practices

### 1. Minimize Context Overhead
**Problem**: Each MCP adds tools to context (~1-15k tokens)
**Solution**: Only include MCPs you actually need

**Example:**
- ❌ Don't add Playwright MCP if using orchestrator agent
- ❌ Don't add MUI MCP to HTMX projects
- ✅ Add only tech-stack-specific MCPs

---

### 2. Use cmd /c on Windows
**Problem**: npx-based MCPs fail without wrapper
**Solution**: Always use `"command": "cmd"` with `"/c"` arg

**Template:**
```json
{
  "command": "cmd",
  "args": ["/c", "npx", "-y", "package-name"]
}
```

---

### 3. Document in Metadata
**Problem**: Future you forgets why MCP was added
**Solution**: Include metadata block

```json
{
  "metadata": {
    "description": "What it does",
    "why_needed": "Why this project needs it",
    "sources": ["https://..."]
  }
}
```

---

### 4. Track in Database
**Problem**: No visibility into MCP usage across projects
**Solution**: Register all MCPs in `claude.mcp_configs`

```sql
INSERT INTO claude.mcp_configs (
  config_id, project_name, mcp_server_name,
  mcp_package, is_active, reason
) VALUES (
  gen_random_uuid(), 'finance-htmx', 'tailwindcss',
  'tailwindcss-mcp-server', true,
  'DaisyUI requires Tailwind documentation'
);
```

---

### 5. Test Before Promoting
**Workflow:**
1. Add MCP to project `.mcp.json`
2. Test functionality
3. If useful, add to database
4. If universal, consider global config

---

## Troubleshooting

### Issue: MCP Not Loading

**Symptoms:**
- MCP listed in config but not available
- No error message

**Check:**
1. File exists: `ls .mcp.json`
2. Valid JSON: `cat .mcp.json | python -m json.tool`
3. Correct command: `cmd /c` on Windows
4. Package available: `npx -y package-name --version`

---

### Issue: "Windows requires cmd /c wrapper"

**Cause**: Using `"command": "npx"` on Windows

**Fix:**
```json
{
  "command": "cmd",
  "args": ["/c", "npx", "-y", "package"]
}
```

---

### Issue: MCP Using Too Much Context

**Symptoms:**
- Context warning about token usage
- Many tools listed from one MCP

**Solutions:**
1. Remove MCP if not needed
2. Use orchestrator agent instead (spawns on-demand)
3. Split into separate sessions for different tasks

---

## MCP Development Workflow

### Adding a New MCP to a Project

1. **Research**: Find MCP package
   - npm registry
   - MCP directory
   - Vendor documentation

2. **Test Standalone:**
   ```bash
   npx -y package-name
   # Verify it works
   ```

3. **Add to .mcp.json:**
   ```json
   {
     "mcpServers": {
       "new-mcp": {
         "type": "stdio",
         "command": "cmd",
         "args": ["/c", "npx", "-y", "package-name"]
       }
     }
   }
   ```

4. **Test in Session:**
   - Restart Claude Code
   - Check diagnostics: `/doctor`
   - Try using the MCP

5. **Register in Database:**
   ```sql
   INSERT INTO claude.mcp_configs ...
   ```

6. **Update Workspaces:**
   ```sql
   UPDATE claude.workspaces
   SET startup_config = jsonb_set(...)
   ```

7. **Document:**
   - Add to project SETUP.md
   - Note in CLAUDE.md
   - Update this knowledge doc

---

## Related Documentation

- **Hooks**: See [[Claude Code Hooks]]
- **Project Setup**: See [[40-Procedures/New Project SOP]]
- **Orchestrator Agents**: See [[Agentic Orchestration]]
- **Database Schema**: `claude.mcp_configs`, `claude.workspaces`

---

## Future Improvements

### Ideas to Explore:

1. **Auto-Suggest MCPs**: Based on project type, suggest relevant MCPs
2. **Usage Analytics**: Track which MCPs are actually invoked
3. **Performance Monitoring**: Measure MCP response times
4. **Health Checks**: Periodic verification of MCP availability
5. **Version Management**: Track MCP package versions

---

**Version**: 1.2
**Created**: 2025-12-28
**Updated**: 2026-02-11
**Location**: 20-Domains/MCP Server Management.md
