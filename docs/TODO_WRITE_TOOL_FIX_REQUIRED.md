# TodoWrite Tool - FIXED ✅

**Date Created**: 2025-12-31
**Date Fixed**: 2025-12-31
**Status**: COMPLETE
**Impact**: Todo tracking now persistent across sessions

---

## Solution Implemented ✅

**Approach**: PostToolUse hook intercepts TodoWrite calls and syncs to database

**Files Created**:
- `scripts/todo_sync_hook.py` - PostToolUse hook that watches for TodoWrite calls

**Files Modified**:
- `.claude-plugins/claude-family-core/scripts/session_startup_hook.py` - Added `get_todos_from_database()` function with smart auto-completion
- `claude.config_templates` - Registered PostToolUse hook for TodoWrite matcher
- `.claude/settings.local.json` - Regenerated with new hook

**How It Works**:
1. **TodoWrite Called**: User calls TodoWrite tool with todos array
2. **PostToolUse Hook Fires**: `todo_sync_hook.py` intercepts the call
3. **Sync to Database**: Hook syncs todos to `claude.todos` table (INSERT new, UPDATE existing, soft-delete removed)
4. **Session Startup**: `get_todos_from_database()` loads todos from DB (not session_state)
5. **Smart Auto-Completion**: Automatically marks obvious todos as completed (like "restart" when session starts)

**Smart Auto-Completion Rules**:
- "RESTART" + "CLAUDE" in content → mark completed (we're in a new session!)
- "Verify RAG" in content + RAG success in hooks.log → mark completed
- "Fix SessionStart" in content + SessionStart succeeded → mark completed

**Benefits**:
- ✅ Todos persist across sessions
- ✅ Auto-completion of obvious completed todos
- ✅ No more annoying stale todos like "check hook after restart" after restarting
- ✅ Full lifecycle tracking (created_session_id, completed_session_id, timestamps)
- ✅ TodoWrite continues to work normally (no breaking changes)

---

## Original Problem Statement

The `TodoWrite` tool creates in-memory todos that save to `session_state.todo_list` (JSONB) but **NEVER writes to the `claude.todos` table**.

This means:
1. Todos are ephemeral (lost after session unless saved to session_state)
2. No persistent tracking across sessions
3. Can't query historical todos
4. Can't link todos to sessions or messages
5. Duplicate storage (session_state vs proper table)

---

## Current Architecture (BROKEN)

```
TodoWrite Tool
  ↓
In-Memory State (this session only)
  ↓
session_state.todo_list (JSONB snapshot)
  ↓
claude.todos table (NEVER USED!)
```

---

## Desired Architecture (CORRECT)

```
TodoWrite Tool
  ↓
INSERT/UPDATE claude.todos table
  ↓
Load from claude.todos on session start
  ↓
Also save snapshot to session_state.todo_list (for session-resume)
```

---

## Database Schema (Already Exists!)

Table: `claude.todos`

```sql
CREATE TABLE claude.todos (
    todo_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES claude.projects(project_id),
    created_session_id UUID REFERENCES claude.sessions(session_id),
    completed_session_id UUID REFERENCES claude.sessions(session_id),
    content TEXT NOT NULL,
    active_form TEXT NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',  -- pending/in_progress/completed
    priority INTEGER DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    source_message_id UUID REFERENCES claude.messages(message_id)
);

-- Indexes
CREATE INDEX idx_todos_project_status ON claude.todos(project_id, status) WHERE NOT is_deleted;
CREATE INDEX idx_todos_display_order ON claude.todos(project_id, display_order) WHERE NOT is_deleted;
CREATE INDEX idx_todos_source_message ON claude.todos(source_message_id) WHERE source_message_id IS NOT NULL;
```

---

## Required Changes

### 1. TodoWrite Tool Behavior

**Current (Wrong)**:
```python
def TodoWrite(todos):
    # Creates in-memory state only
    in_memory_todos = todos
    # Saves to session_state.todo_list on session-end
```

**Fixed (Correct)**:
```python
def TodoWrite(todos):
    # Get current project_id and session_id
    project_id = get_current_project_id()
    session_id = get_current_session_id()

    # Load existing todos from database
    existing_todos = load_todos_from_db(project_id)

    for todo in todos:
        if todo matches existing:
            # UPDATE existing todo
            UPDATE claude.todos
            SET status = todo['status'],
                updated_at = NOW(),
                completed_at = NOW() if status='completed' else NULL,
                completed_session_id = session_id if status='completed' else NULL
            WHERE todo_id = existing_todo_id
        else:
            # INSERT new todo
            INSERT INTO claude.todos (
                project_id,
                created_session_id,
                content,
                active_form,
                status,
                priority
            ) VALUES (...)

    # Also save snapshot to session_state for backwards compatibility
    save_to_session_state(todos)
```

### 2. Session Start Behavior

**Current (Wrong)**:
```python
# Load from session_state.todo_list only
todos = session_state.todo_list
```

**Fixed (Correct)**:
```python
# Load from claude.todos table
todos = SELECT * FROM claude.todos
         WHERE project_id = current_project
           AND is_deleted = FALSE
           AND status IN ('pending', 'in_progress')
         ORDER BY display_order, priority, created_at

# Display in session startup context
```

### 3. Message Acknowledgment (action='actioned')

**Current**: Creates todo via MCP orchestrator acknowledge tool
**Fixed**: Should use same TodoWrite flow OR directly INSERT into claude.todos

---

## Migration Strategy

### Phase 1: Verify Database Ready
1. ✅ Confirm `claude.todos` table exists (DONE - it exists!)
2. Check for any existing todos (8 found for claude-family)
3. Verify schema matches requirements

### Phase 2: Update TodoWrite Tool
1. Modify TodoWrite to INSERT/UPDATE `claude.todos`
2. Keep session_state.todo_list for backwards compatibility
3. Add session_id tracking (created_session_id, completed_session_id)

### Phase 3: Update Session Start Hook
1. Load todos from `claude.todos` instead of session_state
2. Display in session startup context
3. Handle display_order for custom ordering

### Phase 4: Testing
1. Create todos with TodoWrite
2. Verify INSERT into database
3. End session, start new session
4. Verify todos loaded from database
5. Mark todo as completed
6. Verify UPDATE in database with completed_at and completed_session_id

---

## Benefits After Fix

1. ✅ **Persistent todos** across sessions
2. ✅ **Historical tracking** (when created, when completed, by which session)
3. ✅ **Queryable** ("show me all completed todos this week")
4. ✅ **Message linkage** (todos from acknowledged messages)
5. ✅ **Priority and ordering** (display_order field)
6. ✅ **Soft delete** (archive without losing data)
7. ✅ **Session attribution** (which session created/completed)

---

## Current Workaround (Until Fix)

**For This Session**:
1. Manually INSERT todos into `claude.todos` table
2. These will persist across sessions
3. Can query them later
4. Session-end will still save snapshot to session_state

**SQL to Insert Current Todos**:
```sql
-- Get project_id for claude-family
SELECT project_id FROM claude.projects WHERE project_name = 'claude-family';
-- Result: 20b5627c-e72c-4501-8537-95b559731b59

-- Insert 5 pending todos from this session
INSERT INTO claude.todos (project_id, content, active_form, status, priority) VALUES
('20b5627c-e72c-4501-8537-95b559731b59',
 '⚠️ RESTART CLAUDE CODE - Required to activate RAG UserPromptSubmit hook',
 'Restarting Claude Code for RAG activation',
 'pending', 1),

('20b5627c-e72c-4501-8537-95b559731b59',
 'Verify RAG working - Ask any question, check ~/.claude/hooks.log for rag_query_hook.py activity',
 'Verifying RAG system operational',
 'pending', 2),

('20b5627c-e72c-4501-8537-95b559731b59',
 'Git commit - 16 files changed (RAG implementation + message fixes + ATO plan)',
 'Committing RAG and session improvements',
 'pending', 2),

('20b5627c-e72c-4501-8537-95b559731b59',
 'ATO Project Phase 6.1 - Start implementing real form fields (32 hours, use coder-haiku)',
 'Starting ATO Phase 6.1 - Real Form Fields',
 'pending', 3),

('20b5627c-e72c-4501-8537-95b559731b59',
 'Review ATO Commercialization Plan - Decide on priorities and timeline',
 'Reviewing ATO commercialization roadmap',
 'pending', 3);
```

---

## Next Steps

1. **Immediate**: Manually insert current session todos into database (SQL above)
2. **This Week**: File issue to fix TodoWrite tool
3. **Future**: Update session-start to load from claude.todos
4. **Future**: Update session-end to sync both database and session_state

---

## References

- Database table: `claude.todos`
- Current usage: `mcp__orchestrator__acknowledge` with `action='actioned'` creates todos correctly
- TodoWrite tool: Currently bypasses database entirely
- Session state: `claude.session_state.todo_list` (JSONB, ephemeral snapshot)

---

**Priority**: HIGH - Affects todo persistence across all projects
**Effort**: 4-8 hours to fix TodoWrite tool + session hooks
**Risk**: Medium - Need to ensure backwards compatibility with existing workflows
