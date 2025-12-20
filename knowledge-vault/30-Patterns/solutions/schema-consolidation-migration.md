---
category: infrastructure
confidence: 95
created: 2025-12-19
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.788233'
tags:
- postgresql
- migration
- schema
- claude-family
title: Schema Consolidation Migration Pattern
type: pattern
---

# Schema Consolidation Migration Pattern

## Summary
When scripts call legacy schema functions that reference deleted tables, replace with direct SQL queries to the consolidated schema.

## Details
During schema consolidation (e.g., merging `claude_family.*`, `claude_pm.*` into `claude.*`), stored functions may still reference old table names that no longer exist.

### Problem
```python
# Old code calls legacy function
conn.execute("SELECT claude_family.log_session(...)")
# Fails because function references deleted tables
```

### Solution

1. **Check function definitions**:
```sql
SELECT pg_get_functiondef(oid) 
FROM pg_proc 
WHERE proname = 'function_name';
```

2. **Identify referenced tables**:
Look for table references in the function body.

3. **Replace with direct SQL**:
```python
# Replace function call with direct query
conn.execute("""
    INSERT INTO claude.sessions (session_id, project_name, session_start)
    VALUES (%s, %s, NOW())
""", (session_id, project_name))
```

## Code Example
```python
# BEFORE: Calling legacy function
def log_session_old(project_name: str):
    conn.execute("SELECT claude_family.log_session(%s)", (project_name,))

# AFTER: Direct SQL to consolidated schema
def log_session_new(project_name: str):
    conn.execute("""
        INSERT INTO claude.sessions (
            session_id, 
            project_name, 
            session_start,
            identity_id
        ) VALUES (
            gen_random_uuid(),
            %s,
            NOW(),
            (SELECT identity_id FROM claude.identities WHERE identity_name = 'claude-code-unified')
        )
        RETURNING session_id
    """, (project_name,))
```

## Migration Checklist
- [ ] Identify all scripts calling legacy functions
- [ ] Check each function's definition
- [ ] Replace with direct SQL to new schema
- [ ] Test each migration
- [ ] Drop legacy functions after verification

## Related
- [[psycopg3-vs-psycopg2]]
- [[database-connection-patterns]]