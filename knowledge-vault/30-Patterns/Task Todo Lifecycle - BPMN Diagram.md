---
projects:
  - claude-family
tags:
  - architecture
  - tasks
  - hooks
  - workflow
synced: false
---

# Task & Todo Lifecycle - BPMN Diagram

How work items flow through the system: creation, sync, state transitions, and completion.

**Detail diagrams**: [[Task Todo Lifecycle - Detail Flows]]

---

## Overview: The Two Paths

Work enters via two paths converging at `claude.todos`:

1. **TaskCreate path** (primary) - In-memory task → DB sync → build_task bridge
2. **TodoWrite path** (legacy) - Direct DB sync (no bridging)

Both enforced by **task_discipline_hook** which blocks Write/Edit until tasks exist.

---

## Diagram 1: Task Creation & Sync Flow

```mermaid
flowchart TB
    subgraph User["Claude Conversation"]
        TC[/"TaskCreate(subject, desc)"/]
        TU[/"TaskUpdate(id, status)"/]
    end

    subgraph Hook["task_sync_hook.py (PostToolUse)"]
        H1["Parse task from tool_response"]
        H2["Resolve project_id"]
        D1{"Duplicate?\nfuzzy ≥75%\nsubstr ≥20"}
        D2["Reuse todo_id"]
        D3["INSERT claude.todos"]
        B1{"Build task\nmatch ≥75%?"}
        B2["Map: todo_id + bt_code"]
        B3["Map: todo_id only"]
        H4["Write task_map JSON"]
    end

    subgraph Update["task_sync_hook.py (TaskUpdate)"]
        U1["Load map → todo_id"]
        U2{"Status?"}
        U2a["SET status='archived'\n(was: is_deleted=true)"]
        U2b["UPDATE claude.todos"]
        U3{"Bridged to\nbuild_task?"}
        U4["UPDATE build_tasks\n+ INSERT audit_log"]
        U6{"Last task\nfor feature?"}
        U7["Return additionalContext:\nadvance_status suggestion"]
    end

    TC --> H1 --> H2 --> D1
    D1 -->|"Yes"| D2 --> B1
    D1 -->|"No"| D3 --> B1
    B1 -->|"Yes"| B2 --> H4
    B1 -->|"No"| B3 --> H4

    TU --> U1 --> U2
    U2 -->|"deleted"| U2a --> done3["Done"]
    U2 -->|"other"| U2b --> U3
    U3 -->|"Yes"| U4 --> U6
    U3 -->|"No"| done1["Done"]
    U6 -->|"Yes"| U7
    U6 -->|"No"| done2["Done"]

    style TC fill:#4CAF50,color:white
    style TU fill:#FF9800,color:white
    style D1 fill:#FFF9C4
    style B1 fill:#FFF9C4
    style U3 fill:#FFF9C4
    style U6 fill:#FFF9C4
```

---

## Diagram 2: Task Discipline Gate

```mermaid
flowchart LR
    A[/"Write / Edit / Task"/] --> G1{"task_map\nexists?"}
    G1 -->|"No"| DENY1["DENY: No tasks"]
    G1 -->|"Yes"| G2{"Session ID\nmatches?"}
    G2 -->|"No"| DENY2["DENY: Stale"]
    G2 -->|"Yes"| G3{"Tasks in\nmap?"}
    G3 -->|"Yes"| ALLOW["ALLOW"]
    G3 -->|"No"| DENY1

    style A fill:#2196F3,color:white
    style ALLOW fill:#4CAF50,color:white
    style DENY1 fill:#F44336,color:white
    style DENY2 fill:#F44336,color:white
```

**Not gated**: Read, Grep, Glob, Bash, WebSearch (research tools always allowed)

---

## Diagram 3: Staleness & Auto-Archive

```mermaid
flowchart TB
    subgraph Startup["session_startup_hook (SessionStart)"]
        S1["Query pending todos\n>7 days old"]
        S2{"Any stale?"}
        S3["UPDATE status='archived'"]
        S4["Write fresh task_map\nwith new session_id"]
        S5["Report: 'Auto-archived N items'"]
    end

    subgraph Resume["start_session() → _format_resume()"]
        R1["Query todos with age_days"]
        R2{"age_days > 7\n& pending?"}
        R3["Bucket: stale"]
        R4["Bucket: pending/in_progress"]
        R5["STALE section in display\n(shown but NOT in restore_tasks)"]
    end

    S1 --> S2
    S2 -->|"Yes"| S3 --> S4 --> S5
    S2 -->|"No"| S4

    R1 --> R2
    R2 -->|"Yes"| R3 --> R5
    R2 -->|"No"| R4

    style S3 fill:#FF9800,color:white
    style R3 fill:#FFF9C4
    style R5 fill:#FFF9C4
```

**Key rules**:
- `deleted` via TaskUpdate → maps to `archived` (preserves audit trail)
- Pending >7 days → auto-archived on SessionStart
- Stale items shown in resume display but NOT restored via TaskCreate
- `in_progress` items are NEVER auto-archived (interrupted work, not abandoned)

---

## State Machine Reference

### Build Tasks
```
todo ──→ in_progress ──→ completed
  │          │
  └──→ cancelled   └──→ blocked ──→ in_progress
```

### Features
```
draft ──→ planned ──→ in_progress ──→ completed (requires all_tasks_done)
             │            │
             └──→ cancelled   └──→ blocked
```

### Feedback
```
new ──→ triaged ──→ in_progress ──→ resolved
  │        │            │
  └──→ duplicate  └──→ wont_fix   └──→ wont_fix
```

---

## Data Store Summary

| Store | Type | Written By | Lifetime |
|-------|------|-----------|----------|
| TaskList | In-memory | TaskCreate/TaskUpdate | Session only |
| task_map JSON | Temp file | task_sync_hook | Session (temp dir) |
| claude.todos | DB table | task_sync_hook, todo_sync_hook | Persistent |
| claude.build_tasks | DB table | MCP tools, task_sync_hook | Persistent |
| claude.features | DB table | MCP tools | Persistent |
| claude.audit_log | DB table | WorkflowEngine, task_sync_hook | Immutable |
| claude.session_state | DB table | start_work, complete_work | Per-project |

---

## Todo Status Flow

```
pending ──→ in_progress ──→ completed
  │              │
  └──→ archived  └──→ archived (manual only)
       (auto: >7d)
       (manual: TaskUpdate 'deleted')
```

Valid statuses: `pending`, `in_progress`, `completed`, `cancelled`, `archived`

---

## Known Gaps

| # | Issue | Impact | Status |
|---|-------|--------|--------|
| 1 | Raw SQL bypasses WorkflowEngine (no DB triggers) | Medium | Open |
| 2 | ~~Stale task_map blocks Write/Edit after crash~~ | ~~Medium~~ | **Fixed** (task_map reset on SessionStart) |
| 3 | TodoWrite doesn't bridge to build_tasks | Low | By design |
| 4 | ~~Feature completion is advisory only~~ | ~~Low~~ | **Improved** (additionalContext surfaced) |
| 5 | `create_feature` skips 'draft', starts at 'planned' | Low | Open |
| 6 | Feedback priority=string, features priority=int | Low | Open |

---

**Version**: 1.1
**Created**: 2026-02-16
**Updated**: 2026-02-16
**Location**: knowledge-vault/30-Patterns/Task Todo Lifecycle - BPMN Diagram.md
