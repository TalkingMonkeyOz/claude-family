# Inbox Check Bug Fix

**Date**: 2025-12-26
**File**: mcp-servers/orchestrator/server.py:127-147
**Status**: Fixed (requires restart)

---

## Problem

When using `mcp__orchestrator__check_inbox` without the `project_name` parameter, messages targeted to specific projects were not appearing, even when they had `status='pending'`.

### Reported Symptoms
- First call with `include_read=false`: 0 messages
- Second call with `include_read=true`: 2 pending messages appeared

### Root Cause

The check_inbox function had flawed logic for building the recipient filter:

```python
# OLD CODE (BUGGY)
or_conditions = []
if include_broadcasts:
    or_conditions.append("(to_session_id IS NULL AND to_project IS NULL)")
if project_name:
    or_conditions.append("to_project = %s")
if session_id:
    or_conditions.append("to_session_id = %s")

# Fallback only triggered if or_conditions was empty
if not or_conditions:
    or_conditions.append("to_session_id IS NULL")
```

**The bug**: When `include_broadcasts=True` (the default), `or_conditions` was never empty, so the fallback never triggered. This meant users who didn't pass `project_name` would ONLY see true broadcasts (where both `to_session_id` AND `to_project` are NULL), missing all project-targeted messages.

---

## Solution

Redesigned the recipient filter logic to handle three scenarios correctly:

1. **No filters provided** → Show all non-session-specific messages (broadcasts + project messages)
2. **Project filter provided** → Show messages to that project (+ broadcasts if requested)
3. **Session filter provided** → Show messages to that session (+ broadcasts if requested)

### Fixed Code

```python
# Build WHERE clause for recipients
or_conditions = []
has_specific_recipient = False

if project_name:
    or_conditions.append("to_project = %s")
    params.append(project_name)
    has_specific_recipient = True
if session_id:
    or_conditions.append("to_session_id = %s")
    params.append(session_id)
    has_specific_recipient = True

# If no specific recipient filter, show all non-session-specific messages
# This includes broadcasts AND project-targeted messages
if not has_specific_recipient:
    # Show all messages where to_session_id IS NULL (broadcasts + project messages)
    or_conditions.append("to_session_id IS NULL")
elif include_broadcasts:
    # Also include true broadcasts when specific recipient is provided
    or_conditions.append("(to_session_id IS NULL AND to_project IS NULL)")
```

---

## Test Results

### Test 1: No project_name (the bug scenario)

**Query:**
```sql
SELECT message_id, subject, to_project
FROM claude.messages
WHERE status = 'pending' AND (to_session_id IS NULL)
ORDER BY created_at DESC;
```

**Result:** ✅ 4 messages returned
- claude-family (1)
- Claude Family Manager v2 (2)
- mcw (1)

**Before:** Would return 0 messages (only looked for true broadcasts, none existed)

### Test 2: With project_name='claude-family'

**Query:**
```sql
SELECT message_id, subject, to_project
FROM claude.messages
WHERE status = 'pending'
  AND (to_project = 'claude-family' OR (to_session_id IS NULL AND to_project IS NULL))
ORDER BY created_at DESC;
```

**Result:** ✅ 1 message to claude-family + 0 true broadcasts

---

## Deployment

**Status**: Code fixed, not yet active
**Requires**: Restart Claude Code to reload orchestrator MCP server
**Files Changed**: mcp-servers/orchestrator/server.py

**To apply:**
1. Restart Claude Code (or reload MCP servers)
2. Verify fix with: `mcp__orchestrator__check_inbox(include_read=false)` without project_name
3. Should now see all pending messages across projects

---

## Impact

**Before**: Users needed to explicitly pass `project_name` parameter or they'd see 0 messages
**After**: Users can call check_inbox without parameters and see all their messages

**Breaking Change**: No
**Backward Compatible**: Yes - existing calls with project_name will work exactly as before

---

## Related

- **Issue Message**: message_id 3137a405-6a85-4159-aa08-f39f272ca1d1
- **Reported By**: claude-family-manager-v2 session
- **Session**: 2025-12-26

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
