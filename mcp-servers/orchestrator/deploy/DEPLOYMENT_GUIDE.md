# Claude Agent Orchestrator - Deployment Guide

## Overview

This guide explains how to deploy the orchestrator MCP server to make it available in all Claude Code sessions.

## Prerequisites

1. **Python Requirements**:
   ```bash
   pip install mcp psycopg2-binary
   ```

2. **PostgreSQL Database** (optional, for logging):
   - Database: `ai_company_foundation`
   - Schema: `claude_family`
   - Table: `agent_sessions` (auto-created)

3. **Claude Code CLI**:
   - Must be installed and in PATH
   - Test with: `claude --version`

## Deployment Options

### Option 1: Global Deployment (Recommended)

Deploy to `~/.claude.json` so orchestrator is available in **all projects**.

**Steps:**

1. Backup existing config:
   ```bash
   copy C:\Users\johnd\.claude.json C:\Users\johnd\.claude.json.backup
   ```

2. Merge orchestrator into global config:
   ```json
   {
     "mcpServers": {
       "postgres": { ... },
       "memory": { ... },
       "filesystem": { ... },
       "sequential-thinking": { ... },
       "orchestrator": {
         "type": "stdio",
         "command": "C:\\Python313\\python.exe",
         "args": ["C:\\Projects\\claude-family\\mcp-servers\\orchestrator\\server.py"],
         "env": {}
       }
     }
   }
   ```

3. Restart Claude Code

4. Test:
   ```bash
   claude
   > /mcp list
   # Should show "orchestrator" in the list
   ```

**Pros:**
- Available everywhere
- Single configuration point
- Easy to update

**Cons:**
- Loads in all sessions (even when not needed)
- ~1k tokens overhead

---

### Option 2: Project-Specific Deployment

Deploy to individual projects that need agent orchestration.

**Steps:**

1. Create `.mcp.json` in project root:
   ```json
   {
     "mcpServers": {
       "orchestrator": {
         "type": "stdio",
         "command": "C:\\Python313\\python.exe",
         "args": ["C:\\Projects\\claude-family\\mcp-servers\\orchestrator\\server.py"],
         "env": {}
       }
     }
   }
   ```

2. Start Claude Code in that project directory

3. Test:
   ```bash
   cd C:/Projects/myproject
   claude
   > /mcp list
   # Should show "orchestrator"
   ```

**Pros:**
- Only loads when needed
- Zero overhead in other projects
- Project-specific configurations possible

**Cons:**
- Must deploy to each project individually
- More maintenance overhead

---

## Usage Examples

### List Available Agents

```bash
claude
> mcp__orchestrator__list_agent_types()
```

Output:
```json
[
  {
    "agent_type": "coder-haiku",
    "description": "Fast code writing for new features and simple refactoring",
    "model": "claude-haiku-4-5",
    "cost_per_task_usd": 0.035,
    "read_only": false,
    "use_cases": [...]
  },
  ...
]
```

### Spawn a Coder Agent

```bash
claude
> mcp__orchestrator__spawn_agent({
    "agent_type": "coder-haiku",
    "task": "Write a Python function to validate email addresses",
    "workspace_dir": "C:/Projects/myproject"
  })
```

Output:
```json
{
  "status": "success",
  "agent_type": "coder-haiku",
  "execution_time_seconds": 6.42,
  "estimated_cost_usd": 0.035,
  "output": "Here's an email validator function:\n\n```python\nimport re\n\ndef validate_email(email: str) -> bool:\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return re.match(pattern, email) is not None\n```"
}
```

### Spawn a Reviewer Agent

```bash
claude
> mcp__orchestrator__spawn_agent({
    "agent_type": "reviewer-sonnet",
    "task": "Review the authentication module for code quality and security",
    "workspace_dir": "C:/Projects/myproject"
  })
```

### Spawn a Security Auditor

```bash
claude
> mcp__orchestrator__spawn_agent({
    "agent_type": "security-sonnet",
    "task": "Audit the entire codebase for security vulnerabilities (SQL injection, XSS, etc.)",
    "workspace_dir": "C:/Projects/myproject",
    "timeout": 600
  })
```

---

## Configuration Options

### Custom Python Path

If Python is not in your default location, update the `command`:

```json
{
  "orchestrator": {
    "command": "C:\\CustomPath\\python.exe",
    "args": ["C:\\Projects\\claude-family\\mcp-servers\\orchestrator\\server.py"]
  }
}
```

### Disable Database Logging

Set environment variable:

```json
{
  "orchestrator": {
    "command": "C:\\Python313\\python.exe",
    "args": ["C:\\Projects\\claude-family\\mcp-servers\\orchestrator\\server.py"],
    "env": {
      "DISABLE_DB_LOGGING": "true"
    }
  }
}
```

### Custom PostgreSQL Connection

```json
{
  "orchestrator": {
    "env": {
      "POSTGRES_CONN": "postgresql://user:pass@host:5432/dbname"
    }
  }
}
```

---

## Troubleshooting

### Orchestrator Not Showing in /mcp list

1. Check config syntax:
   ```bash
   python -m json.tool ~/.claude.json
   ```

2. Verify Python path:
   ```bash
   C:\Python313\python.exe --version
   ```

3. Test server directly:
   ```bash
   python C:\Projects\claude-family\mcp-servers\orchestrator\server.py
   ```

4. Check Claude Code logs:
   ```
   %APPDATA%\Claude\logs\
   ```

### Agent Spawn Fails

1. Verify Claude CLI works:
   ```bash
   claude --version
   claude --model claude-haiku-4-5 --print
   ```

2. Check workspace path exists:
   ```bash
   dir C:\Projects\myproject
   ```

3. Test orchestrator prototype directly:
   ```bash
   cd C:\Projects\claude-family\mcp-servers\orchestrator
   python orchestrator_prototype.py list
   python orchestrator_prototype.py spawn coder-haiku "test task" C:/Projects/claude-family
   ```

### Database Logging Not Working

1. Check PostgreSQL is running:
   ```bash
   psql -U postgres -d ai_company_foundation
   ```

2. Verify table exists:
   ```sql
   SELECT * FROM claude_family.agent_sessions LIMIT 1;
   ```

3. Check psycopg2 installed:
   ```bash
   pip show psycopg2-binary
   ```

4. If all else fails, disable DB logging (see Configuration Options above)

---

## Performance Tuning

### Reduce Context Overhead

The orchestrator MCP adds ~1k tokens to context. If this is problematic:

- Use project-specific deployment (Option 2)
- Only deploy to projects that need orchestration
- Consider lazy-loading via slash command instead of MCP

### Optimize Agent Execution

- Use Haiku for simple tasks (3x cheaper, faster)
- Use Sonnet only for complex analysis
- Set appropriate timeouts
- Run multiple agents in parallel when possible

### Database Performance

- Add indexes if logging thousands of sessions:
  ```sql
  CREATE INDEX idx_agent_sessions_workspace
  ON claude_family.agent_sessions(workspace_dir);

  CREATE INDEX idx_agent_sessions_cost
  ON claude_family.agent_sessions(estimated_cost_usd);
  ```

- Archive old sessions periodically

---

## Security Considerations

### Workspace Jailing

- Agents are jailed to specified workspace directories
- Always use absolute paths
- Avoid sensitive directories (System32, .ssh, etc.)

### Tool Restrictions

- Review agent_specs.json carefully
- Whitelist tools for each agent type
- Never allow unrestricted Bash access

### Database Security

- Use read-only database user if possible
- Limit PostgreSQL access to localhost
- Never log sensitive data in tasks

### Input Validation

- Validate workspace paths before spawning
- Sanitize task descriptions
- Limit task length
- Consider additional security hardening (see SECURITY_AUDIT.md)

---

## Monitoring & Analytics

### View Agent Usage Stats

```sql
-- Total sessions by agent type
SELECT
  agent_type,
  COUNT(*) as total_sessions,
  SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
  AVG(execution_time_seconds) as avg_time,
  SUM(estimated_cost_usd) as total_cost
FROM claude_family.agent_sessions
GROUP BY agent_type
ORDER BY total_sessions DESC;
```

### Recent Agent Activity

```sql
SELECT
  agent_type,
  task_description,
  execution_time_seconds,
  success,
  spawned_at
FROM claude_family.agent_sessions
ORDER BY spawned_at DESC
LIMIT 20;
```

### Cost Analysis

```sql
-- Daily cost breakdown
SELECT
  DATE(spawned_at) as date,
  agent_type,
  COUNT(*) as sessions,
  SUM(estimated_cost_usd) as cost
FROM claude_family.agent_sessions
WHERE spawned_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(spawned_at), agent_type
ORDER BY date DESC, cost DESC;
```

---

## Next Steps

1. **Deploy globally** (Option 1) or **per-project** (Option 2)
2. **Test basic usage** with coder-haiku
3. **Explore advanced agents** (reviewer, security, analyst)
4. **Set up monitoring** (PostgreSQL queries)
5. **Expand agent types** as needed (see README.md - Expanding Agent Types)

---

**Version**: 1.0.0
**Updated**: 2025-11-04
**Status**: Production-ready prototype
