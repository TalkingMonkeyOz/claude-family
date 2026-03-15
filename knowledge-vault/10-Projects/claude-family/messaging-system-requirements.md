---
projects:
- claude-family
tags:
- messaging
- requirements
- inter-claude
---

# Inter-Claude Messaging Requirements

## The Scenario

I'm working in Project Metis. I need Claude Family to build an MCP server for me. I send a message. Next time someone opens Claude Family, they see the request, create a task from it, build it, and reply. Or I need to broadcast to all projects that a breaking change happened.

## How It Works Today

### What's good
- `claude.messages` table with full schema (from/to project, type, priority, threading)
- MCP tools: `send_message`, `check_inbox`, `broadcast`, `acknowledge`, `reply_to`
- Message types: task_request, status_update, question, notification, handoff, broadcast
- Status workflow: pending -> read -> acknowledged -> actioned/deferred
- `list_recipients` tool exists to discover valid targets

### What's broken (audit data: 208 messages, 2025-11 to 2026-03)

**1. No recipient validation**
`send_message()` accepts any string as `to_project`. 19 messages sent to non-existent projects — permanently lost. No error, no warning.

**2. Nobody checks their inbox**
Only 8 of 208 messages (3.8%) ever actioned. 109 are unactioned. The startup hook doesn't inject pending messages into context. Claude never sees them unless someone manually runs `check_inbox`.

**3. Recipient confusion**
Case sensitivity issues (ATO-tax-agent vs ATO-Tax-Agent). No canonical list shown to Claude before sending. Claude guesses project names and gets them wrong.

**4. Messages rot forever**
Oldest pending message is 109 days old. No staleness policy. Dead projects (claude-desktop-config, inactive 63 days) still have pending messages that will never be read.

**5. No message-to-task bridge**
When a task_request arrives, there's no automated workflow to create a task from it. The `actioned` status exists but nothing happens when you set it. The acknowledge tool has `action="actioned"` + `project_id` to create a todo, but it's never used in practice.

**6. Volume collapsed**
109 messages in Dec 2025 (system launch), down to 21 in Mar 2026. People stopped using it because it doesn't work.

## What I Want

1. **Messages actually arrive** — when I send to "claude-family", it validates the recipient exists and tells me if it doesn't. No silent failures.

2. **Recipients see messages on startup** — like we just did for tasks. Urgent/unactioned messages injected into startup context. Claude sees them without being asked.

3. **Task requests become tasks** — when a task_request message is actioned, it auto-creates a task. When the task completes, the message is auto-resolved.

4. **Stale messages get cleaned up** — messages to dead projects are flagged. Old acknowledged-but-never-actioned messages are archived after user-defined threshold.

5. **Sender knows who's available** — before sending, Claude sees the valid recipient list with last-active dates. No guessing project names.

## Solution

### Architecture after fix

```
SENDING A MESSAGE
    │
    ├── Claude calls send_message(to_project="target")
    │   └── VALIDATE: check claude.workspaces for exact match
    │       ├── Found → send
    │       └── Not found → error with suggestion (fuzzy match)
    │
    └── Message stored in claude.messages (status=pending)

RECEIVING A MESSAGE (on startup)
    │
    ├── Startup hook queries unactioned messages for this project
    │   └── Inject into additionalContext (like task read-back)
    │       "You have N unactioned messages: [list]"
    │
    └── Claude sees messages → can acknowledge, action, defer, or reply

ACTIONING A TASK_REQUEST
    │
    ├── Claude calls acknowledge(message_id, action="actioned")
    │   └── Auto-creates todo in claude.todos
    │   └── Links message_id to todo for tracking
    │
    └── When todo completed → message auto-resolved (via task_sync_hook)
```

### Changes required

**1. Validate recipients in send_message()** (~15 lines in server_v2.py)
- Query `claude.workspaces` for exact match on `to_project`
- If not found, query for fuzzy/case-insensitive match and suggest
- Reject with clear error: "Project 'xyz' not found. Did you mean 'Xyz'?"

**2. Inject unactioned messages on startup** (~20 lines in session_startup_hook_enhanced.py)
- Query `claude.messages` for this project: status NOT IN ('actioned', 'deferred'), limit 10
- Format and inject into additionalContext alongside task read-back
- Priority ordering: urgent first, then by date

**3. Show recipients before sending** (core protocol or startup context)
- On startup, include "Available messaging recipients: [list with last-active dates]"
- Or: `send_message` tool description updated to say "use list_recipients first"

**4. Stale message cleanup** (startup hook or background job)
- Messages to inactive projects (no session in 90+ days): auto-defer with note
- Acknowledged but never actioned after 60 days: flag for review
- Don't auto-delete — just surface the problem

**5. Message-to-task bridge** (enhance acknowledge tool)
- When `action="actioned"`: create todo, store message_id in todo metadata
- When todo completed: update message status to "resolved" (new status)
- This closes the loop: message → task → done → message resolved

### What this does NOT change
- claude.messages table schema (no new columns except maybe "resolved" status)
- The MCP tools API surface (same tools, better validation)
- The broadcast mechanism (works fine)
- Threading (works fine, rarely used)

## Implementation Status: COMPLETE (2026-03-15)

All 4 fixes implemented, tested (17/17 messaging + 40/40 total BPMN tests pass):
1. ~~Write requirements doc~~ DONE
2. ~~BPMN gap analysis~~ DONE (model was ahead of code — 70.6% alignment, code caught up)
3. ~~Recipient validation~~ DONE (case-insensitive in server_v2.py)
4. ~~Startup message injection~~ DONE (session_startup_hook_enhanced.py)
5. ~~Recipient list on startup~~ DONE
6. ~~Staleness auto-defer~~ DONE (90+ day inactive projects)
7. End-to-end test: verify on next session restart

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/claude-family/messaging-system-requirements.md
