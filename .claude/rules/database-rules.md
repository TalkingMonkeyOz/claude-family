# Database Rules

## Schema Requirements

- **ALWAYS** use `claude.*` schema for infrastructure tables
- **NEVER** use legacy schemas: `claude_family.*`, `claude_pm.*`
- Check `claude.column_registry` before writing to constrained columns

## Data Gateway Pattern

Before INSERT/UPDATE on constrained columns:
```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'TABLE' AND column_name = 'COLUMN';
```

## Key Tables

| Table | Purpose |
|-------|---------|
| `claude.sessions` | Session tracking |
| `claude.todos` | Todo persistence |
| `claude.feedback` | Bugs, ideas, changes |
| `claude.features` | Feature tracking |
| `claude.projects` | Project registry |

## MCP-First (Use BEFORE Raw SQL)

Raw SQL to claude.* tables is PROHIBITED when an MCP tool exists.

| Instead of... | Use This (ToolSearch first) |
|---------------|-----------------------------|
| `INSERT INTO claude.feedback` | `project-tools.create_feedback` |
| `INSERT INTO claude.features` | `project-tools.create_feature` |
| `INSERT INTO claude.build_tasks` | `project-tools.add_build_task` |
| `UPDATE claude.*.status` | `project-tools.update_work_status` |
| `SELECT...build_tasks WHERE status='todo'` | `project-tools.get_ready_tasks` |
| `INSERT INTO claude.knowledge` | `project-tools.store_knowledge` |
| `SELECT FROM claude.knowledge` | `project-tools.recall_knowledge` |
| `INSERT INTO claude.session_facts` | `project-tools.store_session_fact` |

Raw SQL is OK for: SELECT queries without MCP equivalent, analytics, schema inspection.

## Common Constraints

- `status` fields: Check registry (varies by table)
- `priority`: Always 1-5 (1=critical, 5=low)
- `feedback_type`: bug, design, question, change, idea
