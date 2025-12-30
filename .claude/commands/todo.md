# /todo - Persistent TODO Management

**Purpose**: Manage persistent TODO items that survive across sessions.

**Usage**:
- `/todo add <content>` - Add new todo
- `/todo list` - Show active todos
- `/todo complete <id>` - Mark todo as completed
- `/todo start <id>` - Mark todo as in progress
- `/todo cancel <id>` - Cancel a todo
- `/todo delete <id>` - Soft delete a todo
- `/todo archive` - Archive completed todos older than 90 days

---

## Implementation

### Step 1: Get Current Project ID

```sql
SELECT project_id::text
FROM claude.projects
WHERE project_name = '{current_project_name}';
```

Store result in `$PROJECT_ID`.

### Step 2: Execute Requested Operation

#### `/todo add <content>`

Adds a new todo to the current project.

**Arguments**:
- `content` - The todo description (required)
- `--priority <1-5>` - Priority level (optional, default: 3)

**SQL**:
```sql
-- Get current session ID
SELECT session_id::text
FROM claude.sessions
WHERE project_id = $PROJECT_ID::uuid
ORDER BY session_start DESC
LIMIT 1;
-- Store in $SESSION_ID

-- Generate active_form from content
-- Example: "Fix bug" → "Fixing bug"
-- Add "ing" to first verb, or use as-is if short

-- Insert todo
INSERT INTO claude.todos (
    project_id,
    created_session_id,
    content,
    active_form,
    priority
)
VALUES (
    $PROJECT_ID::uuid,
    $SESSION_ID::uuid,
    '{content}',
    '{active_form}',
    {priority}
)
RETURNING todo_id::text, content, status;
```

**Output**:
```
✅ Added todo: {content}
   ID: {todo_id}
   Priority: {priority}
```

---

#### `/todo list`

Shows active todos for the current project.

**SQL**:
```sql
SELECT
    todo_id::text,
    content,
    active_form,
    status,
    priority,
    to_char(created_at, 'YYYY-MM-DD HH24:MI') as created
FROM claude.todos
WHERE project_id = $PROJECT_ID::uuid
  AND status IN ('pending', 'in_progress')
  AND NOT is_deleted
ORDER BY
    CASE status
        WHEN 'in_progress' THEN 1
        WHEN 'pending' THEN 2
    END,
    priority ASC,
    display_order ASC,
    created_at ASC;
```

**Output**:
```
📋 Active Todos for {project_name}:

🔵 In Progress (2):
  1. [abc-123] Fix authentication bug (P2) - Created: 2025-12-26 10:30
  2. [def-456] Update documentation (P3) - Created: 2025-12-26 09:15

⚪ Pending (4):
  3. [ghi-789] Implement new feature (P1) - Created: 2025-12-25 14:20
  4. [jkl-012] Review code changes (P3) - Created: 2025-12-24 11:45
  ...

Total: 2 in progress, 4 pending
```

---

#### `/todo start <id>`

Marks a todo as in progress.

**SQL**:
```sql
UPDATE claude.todos
SET
    status = 'in_progress',
    updated_at = NOW()
WHERE todo_id = '{id}'::uuid
  AND project_id = $PROJECT_ID::uuid
  AND NOT is_deleted
RETURNING content, status;
```

**Output**:
```
▶️ Started: {content}
```

---

#### `/todo complete <id>`

Marks a todo as completed.

**SQL**:
```sql
-- Get current session ID
SELECT session_id::text
FROM claude.sessions
WHERE project_id = $PROJECT_ID::uuid
ORDER BY session_start DESC
LIMIT 1;
-- Store in $SESSION_ID

-- Update todo
UPDATE claude.todos
SET
    status = 'completed',
    completed_at = NOW(),
    completed_session_id = $SESSION_ID::uuid,
    updated_at = NOW()
WHERE todo_id = '{id}'::uuid
  AND project_id = $PROJECT_ID::uuid
  AND NOT is_deleted
RETURNING content, status;
```

**Output**:
```
✅ Completed: {content}
```

---

#### `/todo cancel <id>`

Cancels a todo (marks as cancelled, not deleted).

**SQL**:
```sql
UPDATE claude.todos
SET
    status = 'cancelled',
    updated_at = NOW()
WHERE todo_id = '{id}'::uuid
  AND project_id = $PROJECT_ID::uuid
  AND NOT is_deleted
RETURNING content, status;
```

**Output**:
```
❌ Cancelled: {content}
```

---

#### `/todo delete <id>`

Soft deletes a todo (sets is_deleted flag).

**SQL**:
```sql
UPDATE claude.todos
SET
    is_deleted = TRUE,
    deleted_at = NOW(),
    updated_at = NOW()
WHERE todo_id = '{id}'::uuid
  AND project_id = $PROJECT_ID::uuid
RETURNING content;
```

**Output**:
```
🗑️ Deleted: {content}
```

---

#### `/todo archive`

Archives completed todos older than 90 days.

**SQL**:
```sql
-- Find todos to archive
SELECT
    COUNT(*) as count
FROM claude.todos
WHERE project_id = $PROJECT_ID::uuid
  AND status = 'completed'
  AND completed_at < NOW() - INTERVAL '90 days'
  AND NOT is_deleted;

-- Archive them
UPDATE claude.todos
SET
    status = 'archived',
    updated_at = NOW()
WHERE project_id = $PROJECT_ID::uuid
  AND status = 'completed'
  AND completed_at < NOW() - INTERVAL '90 days'
  AND NOT is_deleted
RETURNING todo_id::text;
```

**Output**:
```
📦 Archived {count} completed todos older than 90 days
```

---

## Error Handling

### Todo Not Found
```
❌ Error: Todo {id} not found or already deleted
```

### Invalid Priority
```
❌ Error: Priority must be between 1 and 5
```

### Invalid Status
```
❌ Error: Invalid status. Valid: pending, in_progress, completed, cancelled, archived
```

---

## Integration with TodoWrite

The `/todo` command manages **persistent** todos in the database, while `TodoWrite` manages **ephemeral** todos in the conversation.

**Workflow**:
1. On **session-start**: Load active todos from DB → populate TodoWrite
2. During **session**: Use TodoWrite as normal
3. On **session-end**: Sync TodoWrite changes back to DB

This gives you the best of both worlds:
- TodoWrite for in-conversation tracking
- Database for persistence across sessions

---

## Examples

### Add a todo
```
/todo add Fix authentication bug --priority 2
✅ Added todo: Fix authentication bug
   ID: abc-123-def-456
   Priority: 2
```

### Start working on it
```
/todo start abc-123
▶️ Started: Fix authentication bug
```

### Mark it complete
```
/todo complete abc-123
✅ Completed: Fix authentication bug
```

### List active todos
```
/todo list
📋 Active Todos for claude-family:

🔵 In Progress (1):
  1. [def-456] Update documentation (P3)

⚪ Pending (3):
  2. [ghi-789] Implement new feature (P1)
  3. [jkl-012] Review code changes (P3)
  ...

Total: 1 in progress, 3 pending
```

---

**Created**: 2025-12-26
**Version**: 1.0
**Author**: Claude (Sonnet 4.5)
**Related**: session-start, session-end
