---
name: todo
description: "Manage persistent TODO items in the database — add, list, complete, start, cancel, delete, archive"
user-invocable: true
disable-model-invocation: true
---

# Persistent TODO Management

**Usage**:
- `/todo add <content>` - Add new todo
- `/todo list` - Show active todos
- `/todo complete <id>` - Mark todo as completed
- `/todo start <id>` - Mark todo as in progress
- `/todo cancel <id>` - Cancel a todo
- `/todo delete <id>` - Soft delete a todo
- `/todo archive` - Archive completed todos older than 90 days

---

## Step 1: Get Current Project ID

```sql
SELECT project_id::text
FROM claude.projects
WHERE project_name = '{current_project_name}';
```

## Step 2: Execute Requested Operation

### `/todo add <content>`

```sql
SELECT session_id::text FROM claude.sessions
WHERE project_id = $PROJECT_ID::uuid
ORDER BY session_start DESC LIMIT 1;

INSERT INTO claude.todos (project_id, created_session_id, content, active_form, priority)
VALUES ($PROJECT_ID::uuid, $SESSION_ID::uuid, '{content}', '{active_form}', {priority})
RETURNING todo_id::text, content, status;
```

### `/todo list`

```sql
SELECT todo_id::text, content, active_form, status, priority,
    to_char(created_at, 'YYYY-MM-DD HH24:MI') as created
FROM claude.todos
WHERE project_id = $PROJECT_ID::uuid
  AND status IN ('pending', 'in_progress')
  AND NOT is_deleted
ORDER BY
    CASE status WHEN 'in_progress' THEN 1 WHEN 'pending' THEN 2 END,
    priority ASC, display_order ASC, created_at ASC;
```

### `/todo start <id>`

```sql
UPDATE claude.todos
SET status = 'in_progress', updated_at = NOW()
WHERE todo_id = '{id}'::uuid AND project_id = $PROJECT_ID::uuid AND NOT is_deleted
RETURNING content, status;
```

### `/todo complete <id>`

```sql
UPDATE claude.todos
SET status = 'completed', completed_at = NOW(),
    completed_session_id = $SESSION_ID::uuid, updated_at = NOW()
WHERE todo_id = '{id}'::uuid AND project_id = $PROJECT_ID::uuid AND NOT is_deleted
RETURNING content, status;
```

### `/todo cancel <id>`

```sql
UPDATE claude.todos
SET status = 'cancelled', updated_at = NOW()
WHERE todo_id = '{id}'::uuid AND project_id = $PROJECT_ID::uuid AND NOT is_deleted
RETURNING content, status;
```

### `/todo delete <id>`

```sql
UPDATE claude.todos
SET is_deleted = TRUE, deleted_at = NOW(), updated_at = NOW()
WHERE todo_id = '{id}'::uuid AND project_id = $PROJECT_ID::uuid
RETURNING content;
```

### `/todo archive`

```sql
UPDATE claude.todos
SET status = 'archived', updated_at = NOW()
WHERE project_id = $PROJECT_ID::uuid
  AND status = 'completed'
  AND completed_at < NOW() - INTERVAL '90 days'
  AND NOT is_deleted
RETURNING todo_id::text;
```

---

## Integration with TodoWrite

The `/todo` command manages **persistent** todos in the database, while `TodoWrite` manages **ephemeral** todos in the conversation. Session hooks sync between them.

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/todo/SKILL.md
