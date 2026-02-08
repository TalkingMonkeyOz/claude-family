---
projects:
  - claude-family
tags:
  - user-stories
  - session
  - context-restoration
  - memory
synced: false
---

# Session User Story - Resume Session

**Actor**: John (developer)
**Goal**: Continue working on ATO-tax-agent project from previous day
**Trigger**: User launches Claude next day, runs `/session-resume`

See [[Session User Stories - Overview]]

---

## Step-by-Step Flow

### 1. User Launches Claude (Same as Story 1)

SessionStart hook fires, creates new session, loads saved state.

**New Session ID**: `c3d4e5f6-a7b8-9012-cdef-123456789012`

**State Loaded**:
```json
{
  "todo_list": ["Add edge case tests for zero income", "Document tax calculation rules"],
  "current_focus": "Tax calculation validation",
  "next_steps": "Complete edge case testing and documentation"
}
```

---

### 2. User Runs /session-resume

**Slash Command**: `/session-resume`

**File**: `.claude/commands/session-resume.md`

```markdown
Provide session context to help user resume work:

1. Show project name
2. Show what was being worked on (current_focus)
3. Show pending todos
4. Show next steps
5. Show recent session summaries (last 3 sessions)
6. Check for pending messages
```

---

### 3. Claude Queries Recent Sessions

**MCP Tool**: `mcp__postgres__execute_sql`

```sql
SELECT
    session_start,
    session_end,
    session_summary,
    tasks_completed
FROM claude.sessions
WHERE project_name = 'ATO-Tax-Agent'
  AND session_end IS NOT NULL
ORDER BY session_start DESC
LIMIT 3;
```

**Database Read** ← `claude.sessions`:
```sql
-- Session 1 (yesterday)
session_start: 2025-12-26 10:30:00
session_end: 2025-12-26 14:30:00
session_summary: Implemented tax calculation validation and unit tests...
tasks_completed: ['Implemented TaxCalculator validation logic', ...]

-- Session 2 (2 days ago)
session_start: 2025-12-24 09:00:00
session_end: 2025-12-24 12:00:00
session_summary: Began work on Form 1040 validation logic
tasks_completed: ['Created TaxCalculator.cs', 'Set up test project']

-- Session 3 (3 days ago)
session_start: 2025-12-23 14:00:00
session_end: 2025-12-23 17:00:00
session_summary: Project setup and initial architecture
tasks_completed: ['Created solution structure', 'Added dependencies']
```

---

### 4. Claude Checks for Messages

**MCP Tool**: `mcp__postgres__execute_sql`

```sql
SELECT
    message_id,
    from_project,
    subject,
    body,
    created_at
FROM claude.messages
WHERE (to_project = 'ATO-Tax-Agent' OR to_project IS NULL)
  AND status = 'pending'
ORDER BY created_at DESC;
```

**Database Read** ← `claude.messages`:
```sql
message_id: d4e5f6a7-b8c9-0123-def0-123456789013
from_project: claude-family
subject: Code review request
body: Please review the new database schema changes
created_at: 2025-12-26 18:00:00
status: pending
```

---

### 5. Claude Queries Knowledge (Automatic via RAG)

**Mechanism**: UserPromptSubmit hook auto-queries `claude.knowledge` + `claude.vault_embeddings` on every prompt. No manual tool call needed.

**Manual fallback**: `mcp__project-tools__recall_knowledge`

```json
{
  "query": "ATO tax calculation"
}
```

**Result**:
```json
{
  "entities": [
    {
      "name": "ATO Tax Calculation Rules",
      "entityType": "domain-knowledge",
      "observations": [
        "ATO tax forms require special rounding rules (round to nearest dollar)",
        "Deductions must be validated against income thresholds",
        "Form 1040 has different validation rules than Form 1099"
      ]
    }
  ]
}
```

---

### 6. Claude Presents Context to User

**Claude Response**:
```
# Session Context - ATO-Tax-Agent

## Current Focus
Tax calculation validation

## Pending Todos
1. Add edge case tests for zero income
2. Document tax calculation rules

## Next Steps
Complete edge case testing and documentation

## Recent Sessions

### Yesterday (Dec 26, 10:30-14:30)
Implemented tax calculation validation and unit tests. Fixed deduction calculation bug.
- Implemented TaxCalculator validation logic
- Added unit tests for Form1040 calculations
- Fixed bug in deduction calculations

### 2 Days Ago (Dec 24, 09:00-12:00)
Began work on Form 1040 validation logic
- Created TaxCalculator.cs
- Set up test project

### 3 Days Ago (Dec 23, 14:00-17:00)
Project setup and initial architecture
- Created solution structure
- Added dependencies

## Pending Messages
1 pending message from claude-family:
- Subject: Code review request
- "Please review the new database schema changes"

## Relevant Knowledge
From memory graph:
- ATO tax forms require special rounding rules (round to nearest dollar)
- Deductions must be validated against income thresholds
- Form 1040 has different validation rules than Form 1099

Ready to continue! Would you like to start with the edge case tests or handle the pending message first?
```

---

## Data Flow Summary

```
User launches Claude
    ↓
SessionStart hook creates new session, loads state
    ↓
User runs /session-resume
    ↓
Claude queries database
    ↓
├─ SELECT ← claude.sessions (last 3 sessions)
├─ SELECT ← claude.messages (pending messages)
└─ SEARCH ← memory graph (relevant knowledge)
    ↓
Claude assembles context
    ↓
├─ Current focus from session_state
├─ Todos from session_state
├─ Recent work from sessions
├─ Pending messages
└─ Captured knowledge from memory
    ↓
Claude presents comprehensive context to user
```

---

## Files Involved

| File | Purpose |
|------|---------|
| `.claude/commands/session-resume.md` | Slash command instructions |

---

## Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.sessions` | SELECT | Last 3 completed sessions |
| `claude.session_state` | SELECT | Current focus, todos, next steps (loaded by SessionStart hook) |
| `claude.messages` | SELECT | Pending messages |
| Memory graph | SEARCH | Relevant knowledge entities |

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Session User Story - Resume Session.md
