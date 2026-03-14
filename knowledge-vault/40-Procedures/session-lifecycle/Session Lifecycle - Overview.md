---
projects:
  - claude-family
tags:
  - session
  - procedure
  - lifecycle
  - mandatory
synced: false
---

# Session Lifecycle - Overview

**Purpose**: Complete guide to how Claude sessions work from start to finish.
**Audience**: Claude instances and developers maintaining the system

This document explains every step of the session lifecycle: how sessions start, what happens during work, and how they end.

---

## What is a Session?

A **session** is a single continuous interaction between a user and a Claude instance, tracked from launch to termination.

**Key characteristics**:
- One session = one `claude` process
- Tracked in `claude.sessions` table
- Has unique `session_id` (UUID)
- Linked to an `identity_id` (which Claude instance)
- Linked to a `project_name` (which project)

### Why Session Tracking Matters

| Benefit | Description |
|---------|-------------|
| **Context persistence** | Resume where you left off across days/weeks |
| **Knowledge capture** | Learnings don't disappear when you close terminal |
| **Cost tracking** | Understand time/money spent per project |
| **Audit trail** | Who did what, when, on which project |
| **Coordination** | Multiple Claudes can see each other's work |

### Session vs Agent Session

| Aspect | Session | Agent Session |
|--------|---------|---------------|
| **What** | Interactive Claude Code | Spawned background agent |
| **Table** | `claude.sessions` | `claude.agent_sessions` |
| **Duration** | Minutes to hours | Seconds to minutes |
| **User interaction** | Yes, continuous | No, runs autonomously |
| **Logging** | Manual + hook | Automatic via orchestrator |

---

## Complete Lifecycle Flow

```
                        ┌──────────────┐
                        │ User launches│
                        │    Claude    │
                        └──────┬───────┘
                               │
                        ┌──────▼──────────┐
                        │  SessionStart   │
                        │  Hook Fires     │
                        └──────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────▼─────┐         ┌──────▼──────┐      ┌───────▼────────┐
  │ Create    │         │  Load saved │      │ Load CLAUDE.md │
  │ session   │         │    state    │      │   (global +    │
  │  record   │         │ (todo, focus)│      │    project)    │
  └─────┬─────┘         └──────┬──────┘      └───────┬────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                        ┌──────▼──────────┐
                        │ Display context │
                        │  to user        │
                        └──────┬──────────┘
                               │
                        ┌──────▼──────────┐
                        │  User works     │
                        │  (hours/days)   │
                        └──────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────▼─────┐         ┌──────▼──────┐      ┌───────▼────────┐
  │ TodoWrite │         │  MCP tools  │      │  Agent spawns  │
  │ persists  │         │  tracked    │      │    tracked     │
  │   state   │         │(mcp_usage)  │      │(SubagentStart) │
  └─────┬─────┘         └──────┬──────┘      └───────┬────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                        ┌──────▼──────────┐
                        │ /session-end    │
                        │   (manual)      │
                        └──────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────▼─────┐         ┌──────▼──────┐      ┌───────▼────────┐
  │ Generate  │         │   Update    │      │  Capture       │
  │  summary  │         │  session    │      │ knowledge      │
  │           │         │   record    │      │  (optional)    │
  └─────┬─────┘         └──────┬──────┘      └───────┬────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                        ┌──────▼──────────┐
                        │  User closes    │
                        │    terminal     │
                        └──────┬──────────┘
                               │
                        ┌──────▼──────────┐
                        │  SessionEnd     │
                        │  Hook Fires     │
                        └──────┬──────────┘
                               │
                        ┌──────▼──────────┐
                        │ Cleanup MCP     │
                        │   processes     │
                        └─────────────────┘
```

---

## Background Maintenance (Scheduler)

As of 2026-03-15, Windows Task Scheduler runs `scripts/job_runner.py` on a periodic schedule. This is separate from the interactive session lifecycle above.

**Active maintenance jobs** (6 total):

| Job | Purpose | Trigger |
|-----|---------|---------|
| `bpmn-sync` | Sync BPMN models to DB registry | Periodic |
| `knowledge-decay` | Decay low-confidence memories | Periodic |
| `memory-consolidation` | Promote SHORT→MID→LONG, archive stale | Daily |
| `system-maintenance` | Housekeeping (orphans, stale data) | Daily |
| `vault-embeddings` | Re-embed changed vault documents | Periodic |
| `insight-extraction` | Extract knowledge from past conversations | Daily |

**Setup**: Run `setup_scheduler.bat` as admin to register jobs. Jobs run independently of any session.

**SessionStart self-heal**: The SessionStart hook still calls `sync_project.py` (formerly `generate_project_settings.py`) to regenerate settings, skills, rules, commands, and agents from the database every time Claude Code opens. See [[Config Management SOP]] for details.

---

## Related Detail Documents

- [[Session Lifecycle - Session Start]] - Startup sequence and hook configuration
- [[Session Lifecycle - Session End]] - Ending, resuming, and state management
- [[Session Lifecycle - Reference]] - Key tables, troubleshooting, and best practices

---

## Related Documents

- [[Database Schema - Core Tables]] - sessions, session_state tables
- [[Identity System - Overview]] - How identity is determined
- [[Session Quick Reference]] - Single-page cheat sheet
- [[Family Rules]] - Session rules (mandatory)
- [[Session User Stories]] - Traced examples

---

**Version**: 2.2 (Background maintenance scheduler section; sync_project.py self-heal note)
**Created**: 2025-12-26
**Updated**: 2026-03-15
**Location**: knowledge-vault/40-Procedures/Session Lifecycle - Overview.md
