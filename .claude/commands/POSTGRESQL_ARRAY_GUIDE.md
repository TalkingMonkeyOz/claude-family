# PostgreSQL Array Insertion Guide

## CRITICAL: How to Insert Arrays Properly

### ❌ WRONG - These Will Fail:

```python
# DON'T pass strings with commas
tasks = "'Task 1, Task 2, Task 3'"  # WRONG!

# DON'T use text arrays for UUID columns
related = "ARRAY['some-text', 'other-text']"  # WRONG for uuid[] columns!
```

### ✅ CORRECT - Use These Patterns:

#### For Text Arrays (tasks_completed, learnings_gained, etc.):

```sql
-- Using ARRAY constructor (RECOMMENDED)
UPDATE claude_family.session_history
SET tasks_completed = ARRAY['Task 1', 'Task 2', 'Task 3']
WHERE session_id = 'uuid-here'::uuid;

-- Using curly braces (alternative)
UPDATE claude_family.session_history
SET tasks_completed = '{"Task 1", "Task 2", "Task 3"}'
WHERE session_id = 'uuid-here'::uuid;
```

#### For UUID Arrays (related_knowledge):

```sql
-- MUST cast text to UUID
INSERT INTO claude_family.shared_knowledge (related_knowledge)
VALUES (ARRAY['uuid1'::uuid, 'uuid2'::uuid]);

-- Or use NULL if no related knowledge
INSERT INTO claude_family.shared_knowledge (related_knowledge)
VALUES (NULL);
```

#### From Python with psycopg2:

```python
import psycopg2

# For text arrays - use list and let psycopg2 handle it
tasks = ['Task 1', 'Task 2', 'Task 3']
cur.execute("""
    UPDATE claude_family.session_history
    SET tasks_completed = %s
    WHERE session_id = %s
""", (tasks, session_id))

# For UUID arrays - must cast
related_uuids = ['uuid1', 'uuid2']
cur.execute("""
    INSERT INTO claude_family.shared_knowledge (related_knowledge)
    VALUES (%s::uuid[])
""", (related_uuids,))

# Or for NULL
cur.execute("""
    INSERT INTO claude_family.shared_knowledge (related_knowledge)
    VALUES (NULL)
""")
```

## Common Errors and Fixes:

### Error: `malformed array literal`
**Cause**: Passing plain string instead of array
```sql
-- WRONG
tasks_completed = 'Task 1, Task 2, Task 3'

-- RIGHT
tasks_completed = ARRAY['Task 1', 'Task 2', 'Task 3']
```

### Error: `column is of type uuid[] but expression is of type text[]`
**Cause**: Passing text array to UUID column
```sql
-- WRONG
related_knowledge = ARRAY['text1', 'text2']

-- RIGHT
related_knowledge = NULL
-- or
related_knowledge = ARRAY['uuid1'::uuid, 'uuid2'::uuid]
```

## Quick Reference:

| Column | Type | Example Value |
|--------|------|---------------|
| tasks_completed | text[] | `ARRAY['Task 1', 'Task 2']` |
| learnings_gained | text[] | `ARRAY['Learned X', 'Discovered Y']` |
| challenges_encountered | text[] | `ARRAY['Issue with Z']` |
| applies_to_projects | text[] | `ARRAY['project-name']` or `ARRAY['all']` |
| related_knowledge | uuid[] | `NULL` or `ARRAY['uuid1'::uuid]` |

## Best Practice:

When closing a session, use the postgres MCP tool directly instead of generating Python code:

```
mcp__postgres__execute_sql(sql="""
UPDATE claude_family.session_history
SET
    session_end = NOW(),
    session_summary = 'Summary here',
    tasks_completed = ARRAY['Task 1', 'Task 2'],
    learnings_gained = ARRAY['Learning 1'],
    challenges_encountered = ARRAY['Challenge 1']
WHERE session_id = 'your-session-uuid'::uuid
""")
```
