---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.752066'
---

# Claude Family Postgres

Database: `ai_company_foundation`
Schema: `claude` (consolidated - 52 tables)

## Key Tables

| Table | Purpose |
|-------|---------|
| `sessions` | Session logging |
| `projects` | Project registry |
| `knowledge` | Synced from Obsidian vault |
| `process_registry` | Workflow definitions |
| `scheduled_jobs` | Cron-like jobs |
| `feedback` | Issue tracking |
| `column_registry` | Data Gateway constraints |

## Data Gateway

Before writing to constrained columns:
```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'X' AND column_name = 'Y';
```

## Connection

Via MCP postgres server - see [[MCP configuration]]

See also: [[Claude Hooks]] (validates writes)