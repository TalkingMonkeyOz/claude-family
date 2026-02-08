---
projects:
  - claude-family
tags:
  - user-stories
  - session
  - persistence
  - knowledge-capture
synced: false
---

# Session User Story - End Session

**Actor**: John (developer)
**Goal**: Save session state and summary before closing Claude
**Trigger**: User runs `/session-end` slash command

See [[Session User Stories - Overview]]

---

## Step-by-Step Flow

### 1. User Runs /session-end

**Command**: User types `/session-end` in Claude conversation

**Slash Command File**: `.claude/commands/session-end.md`

```markdown
You are ending this session. Follow these steps:

1. Generate session summary from conversation history
2. Extract tasks completed and learnings
3. Update session record in database
4. Save session state for next time
5. Capture knowledge to memory graph
```

---

### 2. Claude Generates Summary

**Claude Reviews Conversation**:
```
Tasks completed:
- Implemented TaxCalculator validation logic
- Added unit tests for Form1040 calculations
- Fixed bug in deduction calculations

Learnings:
- ATO tax forms require special rounding rules
- Deductions must be validated against income thresholds
```

---

### 3. Claude Updates Session Record

**MCP Tool**: `mcp__postgres__execute_sql`

```sql
UPDATE claude.sessions
SET
    session_end = NOW(),
    session_summary = 'Implemented tax calculation validation and unit tests. Fixed deduction calculation bug.',
    tasks_completed = ARRAY[
        'Implemented TaxCalculator validation logic',
        'Added unit tests for Form1040 calculations',
        'Fixed bug in deduction calculations'
    ],
    learnings_gained = ARRAY[
        'ATO tax forms require special rounding rules',
        'Deductions must be validated against income thresholds'
    ]
WHERE session_id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid;
```

**Database Write** → `claude.sessions` (UPDATE):
```sql
session_id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
session_end: 2025-12-26 14:30:00
session_summary: 'Implemented tax calculation validation and unit tests...'
tasks_completed: ['Implemented TaxCalculator validation logic', ...]
learnings_gained: ['ATO tax forms require special rounding rules', ...]
```

---

### 4. Claude Saves Session State

**Current Todo List** (from TodoWrite tool):
```json
[
  {"content": "Add edge case tests for zero income", "status": "pending"},
  {"content": "Document tax calculation rules", "status": "pending"}
]
```

**MCP Tool**: `mcp__postgres__execute_sql`

```sql
INSERT INTO claude.session_state (
    project_name,
    todo_list,
    current_focus,
    next_steps,
    updated_at
) VALUES (
    'ATO-Tax-Agent',
    '["Add edge case tests for zero income", "Document tax calculation rules"]'::jsonb,
    'Tax calculation validation',
    'Complete edge case testing and documentation',
    NOW()
)
ON CONFLICT (project_name)
DO UPDATE SET
    todo_list = EXCLUDED.todo_list,
    current_focus = EXCLUDED.current_focus,
    next_steps = EXCLUDED.next_steps,
    updated_at = NOW();
```

**Database Write** → `claude.session_state` (UPSERT):
```sql
project_name: ATO-Tax-Agent
todo_list: ["Add edge case tests for zero income", "Document tax calculation rules"]
current_focus: Tax calculation validation
next_steps: Complete edge case testing and documentation
pending_actions: NULL
updated_at: 2025-12-26 14:30:00
```

---

### 5. Claude Captures Knowledge

**MCP Tool**: `mcp__project-tools__store_knowledge` (replaced memory MCP, 2026-01)

**Knowledge Captured**:
```python
store_knowledge(
    title="ATO Tax Calculation Rules",
    content="ATO tax forms require special rounding rules (round to nearest dollar). Deductions must be validated against income thresholds. Form 1040 has different validation rules than Form 1099.",
    knowledge_type="pattern",
    topic="tax-calculation",
    confidence=90
)
```

**Database Write** → `claude.knowledge` table (with auto-embedding via Voyage AI)

---

### 6. SessionEnd Hook Fires (Optional)

**Hook Config**: `.claude/hooks.json`

```json
{
  "name": "SessionEnd",
  "description": "Session cleanup",
  "events": ["Stop"],
  "command": "python scripts/session_cleanup.py"
}
```

**Actions**:
- Could send notification
- Could trigger backup
- Currently: No cleanup script configured

---

### 7. Claude Confirms to User

**Claude Response**:
```
Session saved successfully!

Summary: Implemented tax calculation validation and unit tests. Fixed deduction calculation bug.

Tasks completed: 3
Learnings captured: 2
Todo items saved: 2

Next session will resume with:
- Current focus: Tax calculation validation
- Next steps: Complete edge case testing and documentation
```

---

## Data Flow Summary

```
User runs /session-end
    ↓
Claude reads slash command instructions
    ↓
Claude reviews conversation history
    ↓
├─ Generate summary
├─ Extract tasks completed
└─ Extract learnings
    ↓
Claude updates database
    ↓
├─ UPDATE → claude.sessions (session_end, summary, tasks, learnings)
├─ UPSERT → claude.session_state (todo_list, focus, next_steps)
└─ CREATE → memory graph (knowledge entities)
    ↓
SessionEnd hook fires (optional)
    ↓
Claude confirms to user
```

---

## Files Involved

| File | Purpose |
|------|---------|
| `.claude/commands/session-end.md` | Slash command instructions |
| `.claude/hooks.json` | SessionEnd hook definition (if configured) |

---

## Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.sessions` | UPDATE | session_end, session_summary, tasks_completed, learnings_gained |
| `claude.session_state` | UPSERT | todo_list, current_focus, next_steps |
| Memory graph | CREATE | Knowledge entities and observations |

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Session User Story - End Session.md
