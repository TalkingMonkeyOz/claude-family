---
name: messaging
description: Inter-Claude messaging (inbox, broadcast, team status)
model: sonnet
allowed-tools:
  - mcp__project-tools__*
---

# Messaging Skill

**Status**: Active

---

## Overview

Inter-Claude communication: sending messages, checking inbox, broadcasting to all instances, and coordinating work.

**Detailed reference**: See [reference.md](./reference.md) for full examples, SQL queries, and patterns.

---

## When to Use

- Coordinating work across multiple Claude instances
- Handing off work to another Claude instance
- Broadcasting announcements to all instances
- Checking for messages from other instances
- Asynchronous agent completion notifications

---

## Quick Reference

### Commands

| Command | Purpose | Recipients |
|---------|---------|------------|
| `/check-messages` or `/inbox-check` | View pending messages | Current instance |
| `/broadcast` | Send to all active instances | All |
| `/team-status` | View active Claude instances | - |

### Tools

| Tool | Purpose |
|------|---------|
| `check_inbox(project_name=)` | Check pending messages (ALWAYS pass project_name) |
| `send_message(to_project=, message_type=, body=)` | Send to project or session |
| `broadcast(subject=, body=)` | Send to all instances |
| `reply_to(original_message_id=, body=)` | Reply (routes to sender's project) |
| `acknowledge(message_id=, action=)` | Mark read/acknowledged/actioned/deferred |
| `list_recipients()` | Discover valid recipients before sending |
| `get_active_sessions()` | See who's currently working |

### Recipient Discovery

**Before sending**, discover valid recipients: `list_recipients()`

### Threading

Messages support threading via `parent_message_id` and `thread_id`. `reply_to()` sets both automatically.

---

## Message Types

| Type | Purpose | Example |
|------|---------|---------|
| `task_request` | Request work | "Please review PR #123" |
| `status_update` | Share progress | "Completed user auth feature" |
| `question` | Ask for input | "Which approach for caching?" |
| `notification` | Inform about event | "Database migration completed" |
| `handoff` | Transfer work | "Taking over nimbus-import work" |
| `broadcast` | Announce to all | "New coding standard added" |

---

## Message Context (REQUIRED for Actionable Messages)

For `task_request`, `question`, or `handoff`, always include: **BACKGROUND**, **CURRENT STATE**, **SPECIFIC ASK**, **FILES**, **SUCCESS CRITERIA**. See [reference.md](./reference.md) for template and examples.

---

## Acknowledging Messages

| Action | When | Extra Params |
|--------|------|--------------|
| `read` | Informational messages | - |
| `acknowledged` | Seen, no action needed | - |
| `actioned` | Convert to todo | `project_id` (required) |
| `deferred` | Explicitly skip | `defer_reason` (required) |

---

## Priority Guidelines

| Priority | When to Use | Response Time |
|----------|-------------|---------------|
| **urgent** | Security issues, production down | <1 hour |
| **normal** | Regular work items, reviews | <1 day |
| **low** | FYI, announcements | When convenient |

---

## Related Skills

- `session-management` - Session-scoped messaging
- `agentic-orchestration` - Agent completion notifications
- `project-ops` - Project-targeted messages

---

**Version**: 5.0 (Progressive disclosure: split to SKILL.md overview + reference.md detail)
**Created**: 2025-12-26
**Updated**: 2026-03-29
**Location**: .claude/skills/messaging/SKILL.md
