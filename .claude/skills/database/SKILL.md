# Database Operations Skill

**Status**: Active
**Last Updated**: 2025-12-19

---

## Overview

This skill provides guidance for database operations with the Claude Family PostgreSQL database (`ai_company_foundation`).

---

## Quick Reference

### Connection

```python
# Python (psycopg3)
import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="ai_company_foundation",  # Note: dbname, not database
    user="postgres",
    password="your_password"
)
```

### Primary Schema

Use `claude.*` for all new work. Legacy schemas (`claude_family`, `claude_pm`, `claude_mission_control`) are deprecated.

### Core Tables

| Table | Purpose |
|-------|---------|
| `claude.sessions` | Session tracking and logging |
| `claude.knowledge` | Persistent knowledge entries |
| `claude.feedback` | GitHub-style issue tracking |
| `claude.features` | Feature planning |
| `claude.build_tasks` | Development tasks |
| `claude.projects` | Project registry |
| `claude.column_registry` | Valid values for constrained columns |

---

## Data Gateway (MANDATORY)

Before writing to any constrained column, check valid values:

```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'TABLE' AND column_name = 'COLUMN';
```

### Common Constraints

| Table.Column | Valid Values |
|--------------|--------------|
| `feedback.feedback_type` | bug, design, question, change |
| `*.priority` | 1-5 (1=critical, 5=low) |
| `*.status` | Check registry - varies by table |

---

## Key Gotchas

### 1. psycopg3 vs psycopg2

```python
# psycopg2 uses 'database'
conn = psycopg2.connect(database="ai_company_foundation")

# psycopg3 uses 'dbname'
conn = psycopg.connect(dbname="ai_company_foundation")
```

### 2. UUID Array Casting

```sql
-- WRONG: PostgreSQL doesn't auto-cast text[] to uuid[]
INSERT INTO table (uuid_array_col) VALUES (ARRAY['id1', 'id2']);

-- CORRECT: Explicit cast
INSERT INTO table (uuid_array_col) VALUES (ARRAY['id1', 'id2']::uuid[]);
```

### 3. DISTINCT with ORDER BY

```sql
-- WRONG: Column in ORDER BY must be in SELECT for DISTINCT
SELECT DISTINCT title FROM knowledge ORDER BY created_at;

-- CORRECT: Include the ORDER BY column
SELECT DISTINCT title, created_at FROM knowledge ORDER BY created_at;
```

### 4. Schema Consolidation

Legacy functions in `claude_family.*` may reference deleted tables. Check function definitions with:

```sql
SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'function_name';
```

Replace with direct queries to `claude.*` schema.

---

## Common Queries

```sql
-- Check project status
SELECT * FROM claude.projects WHERE project_name = 'your-project';

-- Recent sessions
SELECT session_start, summary FROM claude.sessions
WHERE project_name = 'your-project' ORDER BY session_start DESC LIMIT 5;

-- Valid values for any field
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'TABLE' AND column_name = 'COLUMN';

-- Check open feedback
SELECT feedback_id::text, feedback_type, description, status
FROM claude.feedback
WHERE status IN ('new', 'in_progress')
ORDER BY created_at DESC;
```

---

## Related Skills

- `testing-patterns` - Database testing approaches
- `feature-workflow` - Feature tracking in database

---

**Version**: 1.0
