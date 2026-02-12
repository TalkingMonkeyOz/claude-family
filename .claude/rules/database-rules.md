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

## Common Constraints

- `status` fields: Check registry (varies by table)
- `priority`: Always 1-5 (1=critical, 5=low)
- `feedback_type`: bug, design, question, change, idea
