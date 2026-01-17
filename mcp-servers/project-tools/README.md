# Claude Project Tools MCP

MCP server providing project-aware tooling for the Claude Family ecosystem.

## Features

### Tier 1: Core Tools

| Tool | Purpose |
|------|---------|
| `get_project_context` | Load project info, settings, tech stack, active features |
| `get_incomplete_todos` | Get unfinished todos across sessions |
| `restore_session_todos` | Get todos from past session (for TodoWrite) |
| `create_feedback` | Create feedback with validation |
| `create_feature` | Create feature with plan_data |
| `add_build_task` | Add task to a feature |
| `get_ready_tasks` | Get unblocked build_tasks |
| `update_work_status` | Update status of any work item |
| `find_skill` | Search skill_content by task |
| `todos_to_build_tasks` | Convert todos to persistent tasks |

## Installation

### Prerequisites

- Python 3.10+
- MCP SDK: `pip install mcp`
- psycopg (v2 or v3): `pip install psycopg` or `pip install psycopg2-binary`

### Add to Claude Code

Add to `~/.claude.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "project-tools": {
      "type": "stdio",
      "command": "C:\\venvs\\mcp\\Scripts\\python.exe",
      "args": ["C:\\Projects\\claude-family\\mcp-servers\\project-tools\\server.py"],
      "env": {
        "DATABASE_URI": "postgresql://user:pass@localhost/ai_company_foundation"
      }
    }
  }
}
```

## Usage Examples

### Get Project Context

```
mcp__project-tools__get_project_context(project_path="claude-manager-mui")
```

Returns:
```json
{
  "project_id": "uuid",
  "project_name": "claude-manager-mui",
  "project_type": "tauri-react",
  "tech_stack": ["React", "TypeScript", "Tauri", "Rust"],
  "active_features": [...],
  "incomplete_todos_count": 5,
  "last_session": {...}
}
```

### Create Feedback

```
mcp__project-tools__create_feedback(
  project="claude-manager-mui",
  feedback_type="bug",
  description="Config tab doesn't save changes"
)
```

### Restore Todos from Previous Session

```
mcp__project-tools__restore_session_todos(session_id="abc-123-def")
```

Returns data formatted for TodoWrite.

## Database Tables Used

- `claude.projects` - Project registry
- `claude.workspaces` - Project paths and types
- `claude.todos` - Todo persistence
- `claude.feedback` - Bugs, ideas, questions
- `claude.features` - Feature tracking
- `claude.build_tasks` - Task tracking
- `claude.sessions` - Session history
- `claude.column_registry` - Valid values for validation
- `claude.skill_content` - Searchable skills

## Security

- All database queries use parameterized statements
- Values validated against column_registry before insert/update
- No arbitrary command execution
- stdio transport only (no network binding)

## Rollout to Projects

### Global Installation (All Projects)

The MCP is configured globally in `~/.claude.json` under `mcpServers`. This means it's available to **all** Claude Code sessions automatically.

### Per-Project Activation

Projects are identified by:
1. `project_name` in `claude.workspaces`
2. `project_path` in `claude.workspaces`
3. `project_name` in `claude.projects`

To add a new project to the system:

```sql
-- 1. Create project entry if not exists
INSERT INTO claude.projects (project_id, project_name, project_type, settings)
VALUES (gen_random_uuid(), 'my-project', 'Application', '{}');

-- 2. Create workspace entry linking path to project
INSERT INTO claude.workspaces (workspace_id, project_id, project_name, project_path, project_type)
SELECT gen_random_uuid(), project_id, 'my-project', 'C:\Projects\my-project', 'tauri-react'
FROM claude.projects WHERE project_name = 'my-project';
```

### Benefits for Projects

| Before | After |
|--------|-------|
| Todos lost between sessions | `restore_session_todos` brings them back |
| Work items scattered | `create_feedback`, `create_feature`, `add_build_task` with validation |
| No project context at start | `get_project_context` loads everything |
| Manual skill lookup | `find_skill` searches by task description |
| Todos = session only | `todos_to_build_tasks` promotes to persistent tracking |

### Tested Projects

- [x] claude-family (2026-01-17)
- [ ] claude-manager-mui
- [ ] nimbus-import
- [ ] ATO-Tax-Agent

---

**Version**: 1.1
**Created**: 2026-01-17
**Updated**: 2026-01-17
**Author**: Claude Family
