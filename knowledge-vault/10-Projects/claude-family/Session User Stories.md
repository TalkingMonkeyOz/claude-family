---
projects:
  - claude-family
tags:
  - user-stories
  - session
  - flows
  - validation
synced: false
---

# Session User Stories

**Purpose**: Traced paths through the system validating architecture documentation
**Related**: [[Session Lifecycle]], [[Database Schema - Core Tables]], [[Identity System]]

This document traces 5 key user stories through the Claude Family system, showing exactly what happens at each step, which files are involved, and what data is written to the database.

---

## User Story 1: Developer Launches Claude on Project

**Actor**: John (developer)
**Goal**: Start working on ATO-tax-agent project
**Trigger**: Clicks "Launch" in Claude Family Manager WinForms launcher

---

### Step-by-Step Flow

#### 1. User Clicks Launch Button

**File**: `ClaudeLauncherWinForms\Services\LaunchService.cs`

```csharp
// User clicks Launch on "ATO-Tax-Agent" workspace
var workspace = workspaceService.GetWorkspace("ATO-Tax-Agent");
// workspace.path = "C:\Projects\ATO-Tax-Agent"
// workspace.project_name = "ATO-tax-agent"

// Build command
var command = $"wt.exe -d \"{workspace.path}\" claude --model sonnet";

// Launch Windows Terminal
Process.Start("cmd.exe", $"/c {command}");
```

**Environment Variables Set**: NONE currently (this is a gap)

---

#### 2. Claude Code Starts

**Command Line**:
```bash
cd C:\Projects\ATO-Tax-Agent
claude --model sonnet
```

**Current Working Directory**: `C:\Projects\ATO-Tax-Agent`

---

#### 3. SessionStart Hook Fires

**Trigger**: Claude Code initialization
**Hook Config**: `.claude/hooks.json` (lines 74-84)

```json
{
  "name": "SessionStart",
  "description": "Initialize session and load context",
  "events": ["SessionStart"],
  "command": "python C:\\Projects\\claude-family\\.claude-plugins\\claude-family-core\\scripts\\session_startup_hook.py"
}
```

---

#### 4. Session Startup Script Runs

**File**: `.claude-plugins/claude-family-core/scripts/session_startup_hook.py`

**Actions**:

1. **Determine Project Name** (from cwd):
```python
project_name = os.path.basename(os.getcwd())
# Result: "ATO-Tax-Agent"
```

2. **Resolve Identity** (currently hardcoded):
```python
DEFAULT_IDENTITY_ID = 'ff32276f-9d05-4a18-b092-31b54c82fff9'  # claude-code-unified
identity_id = os.environ.get('CLAUDE_IDENTITY_ID', DEFAULT_IDENTITY_ID)
# Result: ff32276f-9d05-4a18-b092-31b54c82fff9
```

**Gap**: Should read from CLAUDE.md or projects.default_identity_id (see [[Identity System]])

3. **Create Session Record**:
```python
session_id = str(uuid.uuid4())
# Example: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'

cursor.execute("""
    INSERT INTO claude.sessions (
        session_id,
        identity_id,
        project_name,
        session_start
    ) VALUES (%s, %s, %s, NOW())
    RETURNING session_id
""", (session_id, identity_id, project_name))
```

**Database Write** → `claude.sessions`:
```sql
session_id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
identity_id: ff32276f-9d05-4a18-b092-31b54c82fff9
project_name: ATO-Tax-Agent
session_start: 2025-12-26 10:30:00
session_end: NULL
session_summary: NULL
tasks_completed: NULL
learnings_gained: NULL
```

4. **Load Saved State**:
```python
cursor.execute("""
    SELECT todo_list, current_focus, next_steps, pending_actions
    FROM claude.session_state
    WHERE project_name = %s
""", (project_name,))
```

**Database Read** ← `claude.session_state`:
```sql
project_name: ATO-Tax-Agent
todo_list: '["Implement tax calculation validation", "Add unit tests"]'
current_focus: "Tax form validation logic"
next_steps: "Complete TaxCalculator.cs implementation"
pending_actions: NULL
updated_at: 2025-12-25 16:45:00
```

5. **Check for Messages**:
```python
cursor.execute("""
    SELECT message_id, subject, body, from_project
    FROM claude.messages
    WHERE (to_project = %s OR to_project IS NULL)
      AND status = 'pending'
""", (project_name,))
```

**Database Read** ← `claude.messages`:
```sql
-- No pending messages
```

6. **Load CLAUDE.md**:
```python
# Global CLAUDE.md
global_claude_md = read_file('C:\\Users\\johnd\\.claude\\CLAUDE.md')

# Project CLAUDE.md
project_claude_md = read_file('C:\\Projects\\ATO-Tax-Agent\\CLAUDE.md')
```

7. **Return Context to Claude**:
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "project_name": "ATO-Tax-Agent",
  "session_state": {
    "todo_list": ["Implement tax calculation validation", "Add unit tests"],
    "current_focus": "Tax form validation logic",
    "next_steps": "Complete TaxCalculator.cs implementation"
  },
  "messages": []
}
```

**Gap**: `session_id` NOT exported to environment variable → MCP usage logging can't link to session

---

#### 5. Claude Receives Context

Claude now knows:
- Session ID (internal only, not in env)
- Project name
- What was being worked on last time
- Pending todos
- No pending messages

**First Prompt**: User sees Claude ready to work with restored context.

---

### Data Flow Summary

```
User Click (Launcher)
    ↓
Launch Windows Terminal → cd to project dir
    ↓
Claude Code starts
    ↓
SessionStart hook fires
    ↓
session_startup_hook.py runs
    ↓
├─ INSERT → claude.sessions (new session record)
├─ SELECT ← claude.session_state (load saved state)
├─ SELECT ← claude.messages (check inbox)
├─ Read CLAUDE.md files
└─ Return context to Claude
    ↓
Claude ready to work
```

---

### Files Involved

| File | Purpose |
|------|---------|
| `ClaudeLauncherWinForms\Services\LaunchService.cs` | Launches Windows Terminal with Claude |
| `.claude/hooks.json` | SessionStart hook definition |
| `.claude-plugins/claude-family-core/scripts/session_startup_hook.py` | Creates session, loads state |
| `C:\Users\johnd\.claude\CLAUDE.md` | Global instructions |
| `C:\Projects\ATO-Tax-Agent\CLAUDE.md` | Project instructions |

---

### Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.sessions` | INSERT | New session record |
| `claude.session_state` | SELECT | Saved todo list, focus, next steps |
| `claude.messages` | SELECT | Check for pending messages |

---

## User Story 2: Claude Spawns Agent

**Actor**: Claude (working on claude-family project)
**Goal**: Spawn doc-keeper-haiku agent to audit documentation
**Trigger**: User request or proactive skill invocation

---

### Step-by-Step Flow

#### 1. User Requests Agent

**User**: "Run the doc-keeper agent to audit the knowledge vault"

**Claude Decision**: Use orchestrator MCP server to spawn agent

---

#### 2. Claude Calls spawn_agent MCP Tool

**Tool**: `mcp__orchestrator__spawn_agent`

**Parameters**:
```json
{
  "agent_type": "doc-keeper-haiku",
  "task": "Audit knowledge vault for staleness and accuracy",
  "workspace_dir": "C:\\Projects\\claude-family"
}
```

---

#### 3. Orchestrator MCP Server Receives Call

**File**: `mcp-servers/orchestrator/server.py`

**Handler**: `handle_spawn_agent()`

**Actions**:

1. **Load Agent Spec**:
```python
agent_spec = load_agent_spec('doc-keeper-haiku')
# {
#   "agent_type": "doc-keeper-haiku",
#   "model": "haiku",
#   "mcp_config": "configs/agent-configs/doc-keeper-haiku.mcp.json",
#   "timeout": 300
# }
```

2. **Generate Agent Session ID**:
```python
agent_session_id = str(uuid.uuid4())
# Example: 'b2c3d4e5-f6a7-8901-bcde-f12345678901'
```

3. **Log Spawn to Database**:
```python
agent_logger.log_spawn(
    session_id=agent_session_id,
    agent_type='doc-keeper-haiku',
    task_description='Audit knowledge vault for staleness and accuracy',
    workspace_dir='C:\\Projects\\claude-family'
)
```

**Database Write** → `claude.agent_sessions`:
```sql
session_id: b2c3d4e5-f6a7-8901-bcde-f12345678901
agent_type: doc-keeper-haiku
task_description: Audit knowledge vault for staleness and accuracy
created_at: 2025-12-26 10:35:00
created_by: NULL  -- Gap: No parent session tracking
started_at: 2025-12-26 10:35:00
completed_at: NULL
success: NULL
result: NULL
error_message: NULL
estimated_cost_usd: NULL
```

**Gap**: `created_by` is NULL because parent session ID not tracked

---

#### 4. Orchestrator Launches Agent Process

**Command**:
```bash
claude \
  --model haiku \
  --mcp-config "C:\Projects\claude-family\mcp-servers\orchestrator\configs\agent-configs\doc-keeper-haiku.mcp.json" \
  --message "Audit knowledge vault for staleness and accuracy"
```

**Agent MCP Config** (`doc-keeper-haiku.mcp.json`):
```json
{
  "postgres": {
    "command": "python",
    "args": ["C:\\Projects\\claude-family\\mcp-servers\\postgres\\server.py"]
  },
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem",
             "C:\\Projects\\claude-family\\knowledge-vault"]
  }
}
```

Agent has access to:
- PostgreSQL database (read-only typically)
- Knowledge vault filesystem

---

#### 5. Agent Executes Task

**Agent Actions**:
1. Read knowledge vault files
2. Check for stale documents (updated_at > 30 days)
3. Verify cross-links
4. Generate report

**Agent Output**:
```
# Documentation Audit Report

## Stale Documents (5)
- Database Architecture.md (60 days old)
- Session Management.md (45 days old)
...

## Broken Links (2)
- Identity System.md → [[Missing Document]]
...

## Recommendations
1. Update Database Architecture.md
2. Create missing Identity System.md
```

---

#### 6. Agent Completes

**Orchestrator Detects Completion**:
```python
agent_logger.log_completion(
    session_id=agent_session_id,
    success=True,
    result=agent_output,
    estimated_cost_usd=0.08
)
```

**Database Write** → `claude.agent_sessions` (UPDATE):
```sql
session_id: b2c3d4e5-f6a7-8901-bcde-f12345678901
completed_at: 2025-12-26 10:40:00
success: TRUE
result: "# Documentation Audit Report\n\n..."
error_message: NULL
estimated_cost_usd: 0.08
```

---

#### 7. Result Returned to Claude

**Orchestrator Returns**:
```json
{
  "session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "success": true,
  "output": "# Documentation Audit Report...",
  "cost": 0.08
}
```

**Claude Receives Result**: Can now show user the audit report

---

### Data Flow Summary

```
User request
    ↓
Claude calls mcp__orchestrator__spawn_agent
    ↓
Orchestrator MCP server
    ↓
├─ INSERT → claude.agent_sessions (log spawn)
├─ Load agent spec
├─ Launch claude subprocess with agent config
└─ Wait for completion
    ↓
Agent executes task
    ↓
├─ Agent uses filesystem MCP to read vault
├─ Agent uses postgres MCP to query database
└─ Agent generates report
    ↓
Agent completes
    ↓
├─ UPDATE → claude.agent_sessions (log completion)
└─ Return result to Claude
    ↓
Claude shows report to user
```

---

### Files Involved

| File | Purpose |
|------|---------|
| `mcp-servers/orchestrator/server.py` | MCP server handling spawn_agent |
| `mcp-servers/orchestrator/agent_specs.json` | Agent type definitions |
| `mcp-servers/orchestrator/db_logger.py` | AgentLogger class |
| `mcp-servers/orchestrator/configs/agent-configs/doc-keeper-haiku.mcp.json` | Agent MCP config |

---

### Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.agent_sessions` | INSERT | Initial spawn record |
| `claude.agent_sessions` | UPDATE | Completion, success, result, cost |

---

## User Story 3: User Ends Session

**Actor**: John (developer)
**Goal**: Save session state and summary before closing Claude
**Trigger**: User runs `/session-end` slash command

---

### Step-by-Step Flow

#### 1. User Runs /session-end

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

#### 2. Claude Generates Summary

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

#### 3. Claude Updates Session Record

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

#### 4. Claude Saves Session State

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

#### 5. Claude Captures Knowledge

**MCP Tool**: `mcp__memory__create_entities`

**Knowledge Captured**:
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

**Database Write** → Memory graph (internal to memory MCP server)

---

#### 6. SessionEnd Hook Fires (Optional)

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

#### 7. Claude Confirms to User

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

### Data Flow Summary

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

### Files Involved

| File | Purpose |
|------|---------|
| `.claude/commands/session-end.md` | Slash command instructions |
| `.claude/hooks.json` | SessionEnd hook definition (if configured) |

---

### Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.sessions` | UPDATE | session_end, session_summary, tasks_completed, learnings_gained |
| `claude.session_state` | UPSERT | todo_list, current_focus, next_steps |
| Memory graph | CREATE | Knowledge entities and observations |

---

## User Story 4: Resume Session Next Day

**Actor**: John (developer)
**Goal**: Continue working on ATO-tax-agent project from previous day
**Trigger**: User launches Claude next day, runs `/session-resume`

---

### Step-by-Step Flow

#### 1. User Launches Claude (Same as Story 1)

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

#### 2. User Runs /session-resume

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

#### 3. Claude Queries Recent Sessions

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

#### 4. Claude Checks for Messages

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

#### 5. Claude Queries Memory Graph

**MCP Tool**: `mcp__memory__search_nodes`

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

#### 6. Claude Presents Context to User

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

### Data Flow Summary

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

### Files Involved

| File | Purpose |
|------|---------|
| `.claude/commands/session-resume.md` | Slash command instructions |

---

### Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.sessions` | SELECT | Last 3 completed sessions |
| `claude.session_state` | SELECT | Current focus, todos, next steps (loaded by SessionStart hook) |
| `claude.messages` | SELECT | Pending messages |
| Memory graph | SEARCH | Relevant knowledge entities |

---

## User Story 5: Cross-Project Message

**Actor**: Claude (claude-family project)
**Goal**: Send task request to ATO-tax-agent project
**Trigger**: Need to coordinate work across projects

---

### Step-by-Step Flow

#### 1. Claude Identifies Need to Message Another Project

**Scenario**: Claude working on claude-family needs ATO-tax-agent to run its test suite.

**Claude Decision**: Use orchestrator messaging system

---

#### 2. Claude Sends Message

**MCP Tool**: `mcp__orchestrator__send_message`

```json
{
  "message_type": "task_request",
  "subject": "Run test suite",
  "body": "Please run your full test suite and report any failures. The database schema was updated and we need to ensure compatibility.",
  "to_project": "ATO-Tax-Agent",
  "from_session_id": "e4f5a6b7-c8d9-0123-4567-890abcdef012",
  "priority": "normal"
}
```

---

#### 3. Orchestrator Creates Message Record

**File**: `mcp-servers/orchestrator/server.py`

**Handler**: `handle_send_message()`

```python
message_id = str(uuid.uuid4())

cursor.execute("""
    INSERT INTO claude.messages (
        message_id,
        message_type,
        subject,
        body,
        to_project,
        from_session_id,
        priority,
        status,
        created_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
    RETURNING message_id
""", (message_id, 'task_request', 'Run test suite', body,
      'ATO-Tax-Agent', from_session_id, 'normal'))
```

**Database Write** → `claude.messages`:
```sql
message_id: f5a6b7c8-d9e0-1234-5678-90abcdef0123
message_type: task_request
subject: Run test suite
body: Please run your full test suite and report any failures...
to_project: ATO-Tax-Agent
to_session_id: NULL
from_project: claude-family
from_session_id: e4f5a6b7-c8d9-0123-4567-890abcdef012
priority: normal
status: pending
created_at: 2025-12-26 15:00:00
read_at: NULL
acknowledged_at: NULL
```

---

#### 4. Message Waits for Recipient

**Status**: Message sits in `claude.messages` table with `status = 'pending'`

---

#### 5. User Launches Claude on ATO-Tax-Agent Project (Later)

**SessionStart Hook Fires**:

**File**: `session_startup_hook.py`

**Checks for Messages**:
```python
cursor.execute("""
    SELECT message_id, subject, body, from_project
    FROM claude.messages
    WHERE (to_project = %s OR to_project IS NULL)
      AND status = 'pending'
""", ('ATO-Tax-Agent',))
```

**Database Read** ← `claude.messages`:
```sql
message_id: f5a6b7c8-d9e0-1234-5678-90abcdef0123
subject: Run test suite
body: Please run your full test suite and report any failures...
from_project: claude-family
```

---

#### 6. Claude Receives Message at Session Start

**SessionStart Hook Returns**:
```json
{
  "session_id": "...",
  "project_name": "ATO-Tax-Agent",
  "session_state": {...},
  "messages": [
    {
      "message_id": "f5a6b7c8-d9e0-1234-5678-90abcdef0123",
      "subject": "Run test suite",
      "body": "Please run your full test suite and report any failures...",
      "from_project": "claude-family"
    }
  ]
}
```

**Claude Shows User**:
```
Session started for ATO-Tax-Agent.

You have 1 pending message:

From: claude-family
Subject: Run test suite
Body: Please run your full test suite and report any failures. The database schema was updated and we need to ensure compatibility.

Would you like me to run the test suite now?
```

---

#### 7. Claude Acts on Message

**User**: "Yes, run the tests"

**Claude Executes**:
```bash
dotnet test ATO-Tax-Agent.Tests.csproj
```

**Test Results**:
```
Total tests: 45
Passed: 43
Failed: 2

Failed tests:
- TaxCalculator_ValidateDeductions_WithNewSchema
- Form1040_Calculate_WithUpdatedRules
```

---

#### 8. Claude Marks Message as Read

**MCP Tool**: `mcp__orchestrator__acknowledge`

```json
{
  "message_id": "f5a6b7c8-d9e0-1234-5678-90abcdef0123",
  "action": "read"
}
```

**Database Write** → `claude.messages` (UPDATE):
```sql
message_id: f5a6b7c8-d9e0-1234-5678-90abcdef0123
status: read
read_at: 2025-12-26 15:30:00
```

---

#### 9. Claude Sends Reply

**MCP Tool**: `mcp__orchestrator__reply_to`

```json
{
  "original_message_id": "f5a6b7c8-d9e0-1234-5678-90abcdef0123",
  "body": "Test suite completed. 2 tests failed:\n\n1. TaxCalculator_ValidateDeductions_WithNewSchema\n2. Form1040_Calculate_WithUpdatedRules\n\nBoth failures are due to schema changes in deductions table. Fixing now.",
  "from_session_id": "a6b7c8d9-e0f1-2345-6789-0abcdef01234"
}
```

**Database Write** → `claude.messages` (new record):
```sql
message_id: a7b8c9d0-e1f2-3456-789a-bcdef0123456
message_type: notification
subject: Re: Run test suite
body: Test suite completed. 2 tests failed...
to_project: claude-family
from_project: ATO-Tax-Agent
from_session_id: a6b7c8d9-e0f1-2345-6789-0abcdef01234
in_reply_to: f5a6b7c8-d9e0-1234-5678-90abcdef0123
priority: normal
status: pending
created_at: 2025-12-26 15:35:00
```

---

#### 10. Original Sender Receives Reply (Next Session)

When Claude launches on claude-family project next time:

**SessionStart Hook Checks Messages**:
```sql
SELECT * FROM claude.messages
WHERE to_project = 'claude-family' AND status = 'pending';
```

**Finds Reply**:
```
From: ATO-Tax-Agent
Subject: Re: Run test suite
Body: Test suite completed. 2 tests failed...
```

**Claude Shows User**:
```
You have 1 pending message:

From: ATO-Tax-Agent (reply to your message)
Subject: Re: Run test suite
Body: Test suite completed. 2 tests failed:
1. TaxCalculator_ValidateDeductions_WithNewSchema
2. Form1040_Calculate_WithUpdatedRules
Both failures are due to schema changes in deductions table. Fixing now.
```

---

### Data Flow Summary

```
Claude (claude-family) sends message
    ↓
orchestrator.send_message()
    ↓
INSERT → claude.messages (status=pending, to_project=ATO-Tax-Agent)
    ↓
Message waits in database
    ↓
User launches Claude on ATO-Tax-Agent
    ↓
SessionStart hook checks messages
    ↓
SELECT ← claude.messages (WHERE to_project=ATO-Tax-Agent)
    ↓
Claude receives message, shows user
    ↓
Claude acts on message (runs tests)
    ↓
Claude marks message as read
    ↓
UPDATE → claude.messages (status=read, read_at=NOW())
    ↓
Claude sends reply
    ↓
INSERT → claude.messages (new message, to_project=claude-family, in_reply_to=original_id)
    ↓
Original sender's next session checks messages
    ↓
SELECT ← claude.messages (WHERE to_project=claude-family)
    ↓
Claude receives reply, shows user
```

---

### Files Involved

| File | Purpose |
|------|---------|
| `mcp-servers/orchestrator/server.py` | Handles send_message, reply_to, acknowledge |
| `session_startup_hook.py` | Checks for pending messages at session start |

---

### Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.messages` | INSERT | Original message (status=pending) |
| `claude.messages` | SELECT | Check for pending messages (at session start) |
| `claude.messages` | UPDATE | Mark as read (read_at timestamp) |
| `claude.messages` | INSERT | Reply message (in_reply_to links to original) |

---

## Validation Summary

These 5 user stories validate the following architecture components:

### ✅ Validated Components

| Component | User Stories | Tables Used |
|-----------|--------------|-------------|
| Session lifecycle | 1, 3, 4 | sessions, session_state |
| Identity resolution | 1 | sessions, identities |
| Agent spawning | 2 | agent_sessions |
| State persistence | 3, 4 | session_state |
| Message routing | 5 | messages |
| Hook system | 1, 3, 4, 5 | All tables |
| MCP integration | 2, 3, 4, 5 | All tables |
| Knowledge capture | 3, 4 | Memory graph |

---

### ⚠️ Gaps Identified

| Gap | Affected Stories | Impact |
|-----|------------------|--------|
| CLAUDE_SESSION_ID not exported | 1, 2, 3 | MCP usage logging broken |
| parent_session_id missing | 2 | Agent sessions orphaned |
| Identity hardcoded | 1 | All sessions appear as same identity |
| No FK constraints | All | Data integrity risks |
| Launcher doesn't set identity | 1 | Identity resolution incomplete |

---

### 🔗 Cross-References

Each user story uses multiple documents:

| Story | References |
|-------|-----------|
| 1. Launch Claude | [[Session Lifecycle]], [[Identity System]], [[Database Schema - Core Tables]] |
| 2. Spawn Agent | [[Database Schema - Core Tables]] (agent_sessions table) |
| 3. End Session | [[Session Lifecycle]], [[Database Schema - Core Tables]] (sessions, session_state) |
| 4. Resume Session | [[Session Lifecycle]], [[Database Schema - Core Tables]] (all core tables) |
| 5. Cross-Project Message | [[Database Schema - Core Tables]] (messages table) |

---

## Testing These Flows

To validate these user stories work correctly:

### Test 1: Launch and Resume
```bash
# 1. Launch Claude on project
cd C:\Projects\ATO-Tax-Agent
claude

# 2. Do some work, run /session-end
# 3. Exit Claude
# 4. Launch again next day
# 5. Run /session-resume

# Expected: Context restored, todos preserved
```

### Test 2: Agent Spawn
```sql
-- Before spawning agent
SELECT COUNT(*) FROM claude.agent_sessions;  -- Note count

-- Spawn agent via MCP
-- After agent completes

SELECT COUNT(*) FROM claude.agent_sessions;  -- Should be +1
SELECT * FROM claude.agent_sessions ORDER BY created_at DESC LIMIT 1;
-- Expected: New record with success=true, result populated
```

### Test 3: Cross-Project Messaging
```sql
-- Claude 1 sends message to Project A

-- Check message created
SELECT * FROM claude.messages WHERE to_project = 'ProjectA' AND status = 'pending';

-- Launch Claude on Project A
-- Expected: Message appears in session context

-- Claude 2 marks as read
SELECT status, read_at FROM claude.messages WHERE message_id = '...';
-- Expected: status=read, read_at populated

-- Claude 2 sends reply
SELECT * FROM claude.messages WHERE in_reply_to = '...' AND to_project = 'OriginalProject';
-- Expected: Reply message exists
```

---

## Related Documents

- [[Session Lifecycle]] - Complete session flow documentation
- [[Database Schema - Core Tables]] - Detailed table schemas
- [[Identity System]] - Identity resolution design
- [[Family Rules]] - Coordination procedures
- [[Session Quick Reference]] - Quick reference for session operations

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Session User Stories.md
