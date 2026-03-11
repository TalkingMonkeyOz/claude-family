---
projects:
  - claude-family
tags:
  - user-stories
  - session
  - launch
  - hooks
  - identity
synced: false
---

# Session User Story - Launch Project

**Actor**: John (developer)
**Goal**: Start working on ATO-tax-agent project
**Trigger**: Clicks "Launch" in Claude Family Manager WinForms launcher

See [[Session User Stories - Overview]]

---

## Step-by-Step Flow

### 1. User Clicks Launch Button

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

### 2. Claude Code Starts

**Command Line**:
```bash
cd C:\Projects\ATO-Tax-Agent
claude --model sonnet
```

**Current Working Directory**: `C:\Projects\ATO-Tax-Agent`

---

### 3. SessionStart Hook Fires

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

### 4. Session Startup Script Runs

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

**Gap**: Should read from CLAUDE.md or projects.default_identity_id (see [[Identity System - Overview]])

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

### 5. Claude Receives Context

Claude now knows:
- Session ID (internal only, not in env)
- Project name
- What was being worked on last time
- Pending todos
- No pending messages

**First Prompt**: User sees Claude ready to work with restored context.

---

## Data Flow Summary

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

## Files Involved

| File | Purpose |
|------|---------|
| `ClaudeLauncherWinForms\Services\LaunchService.cs` | Launches Windows Terminal with Claude |
| `.claude/hooks.json` | SessionStart hook definition |
| `.claude-plugins/claude-family-core/scripts/session_startup_hook.py` | Creates session, loads state |
| `C:\Users\johnd\.claude\CLAUDE.md` | Global instructions |
| `C:\Projects\ATO-Tax-Agent\CLAUDE.md` | Project instructions |

---

## Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.sessions` | INSERT | New session record |
| `claude.session_state` | SELECT | Saved todo list, focus, next steps |
| `claude.messages` | SELECT | Check for pending messages |

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Session User Story - Launch Project.md
