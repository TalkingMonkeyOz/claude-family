---
description: 'SQL and PostgreSQL best practices'
applyTo: '**/*.sql'
source: 'Claude Family (original)'
---

# SQL & PostgreSQL Guidelines

## Schema Conventions

- Use `snake_case` for table and column names
- Prefix tables with schema: `claude.sessions` not just `sessions`
- Use `uuid` for primary keys (with `gen_random_uuid()`)
- Always include `created_at` and `updated_at` timestamps

## Query Patterns

### SELECT Best Practices

```sql
-- Always specify columns, avoid SELECT *
SELECT session_id, session_start, summary
FROM claude.sessions
WHERE project_name = 'my-project'
ORDER BY session_start DESC
LIMIT 10;

-- Use table aliases for joins
SELECT s.session_id, p.project_name
FROM claude.sessions s
JOIN claude.projects p ON s.project_id = p.project_id;
```

### INSERT with Returning

```sql
-- Always use RETURNING for inserts that need the new ID
INSERT INTO claude.feedback (project_id, feedback_type, description)
VALUES ($1, $2, $3)
RETURNING feedback_id;
```

### UPDATE Safely

```sql
-- Always include WHERE clause
-- Use RETURNING to confirm what was updated
UPDATE claude.sessions
SET summary = $1, updated_at = NOW()
WHERE session_id = $2
RETURNING session_id, summary;
```

## Data Gateway (Claude Family Specific)

Before writing to constrained columns, check valid values:

```sql
SELECT valid_values
FROM claude.column_registry
WHERE table_name = 'TABLE_NAME' AND column_name = 'COLUMN_NAME';
```

Common constraints:
- `status` fields: Check registry - varies by table
- `priority`: Always 1-5 (1=critical, 5=low)
- `feedback.feedback_type`: bug, design, question, change

## Performance

- Create indexes for frequently filtered columns
- Use `EXPLAIN ANALYZE` to verify query plans
- Prefer `EXISTS` over `IN` for subqueries
- Use CTEs for readability, but know they're optimization fences

## Common Patterns

### Upsert (INSERT ... ON CONFLICT)

```sql
INSERT INTO claude.knowledge (title, description, source)
VALUES ($1, $2, $3)
ON CONFLICT (title) DO UPDATE
SET description = EXCLUDED.description,
    updated_at = NOW();
```

### Pagination

```sql
SELECT * FROM claude.sessions
WHERE project_id = $1
ORDER BY created_at DESC
LIMIT $2 OFFSET $3;
```

### JSON Operations

```sql
-- Extract from JSONB
SELECT metadata->>'key' as value
FROM claude.sessions
WHERE metadata->>'type' = 'feature';

-- Update JSONB field
UPDATE claude.sessions
SET metadata = metadata || '{"status": "complete"}'::jsonb
WHERE session_id = $1;
```

## Avoid

- `SELECT *` in production code
- Missing WHERE on UPDATE/DELETE
- N+1 query patterns
- Storing large blobs in database
- Using reserved words as column names
