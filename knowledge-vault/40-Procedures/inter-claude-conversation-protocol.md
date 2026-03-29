---
projects:
- claude-family
tags:
- messaging
- coordination
- family-rules
- protocol
---

# Inter-Claude Conversation Protocol

## Purpose

Defines how Claude Family members conduct structured conversations via the messaging system. Every message that expects interaction MUST declare its mode so the receiver knows what's expected.

## Conversation Modes

| Mode | When to Use | Sender Expects | Thread Lifecycle |
|------|-------------|----------------|------------------|
| **fire-and-forget** | Notifications, status updates | Receiver acknowledges only | Single message, no reply needed |
| **question** | Single Q&A | One reply, then done | 2 messages total |
| **collaborative** | Joint investigation, design work | Multiple exchanges back and forth | Either party signals RESOLVED |
| **task-handoff** | "Do this and report back" | Receiver does work, sends completion report | Receiver signals DONE with results |
| **review-request** | "Look at this, give feedback" | One structured reply with findings | 2 messages total |

## Message Structure Rules

### Every message MUST include:
1. **Mode** — which conversation mode (from table above)
2. **Context** — why you're reaching out (brief background)
3. **What you need** — specific asks, numbered if multiple

### Additional requirements by mode:

| Mode | Also Include |
|------|-------------|
| **collaborative** | Ownership split (who develops, who deploys, who decides) |
| **task-handoff** | Done criteria (how does receiver know they're finished?) |
| **review-request** | What to review, what kind of feedback (blocking vs advisory) |

## Threading Rules

1. Use `reply_to(original_message_id)` for all responses — keeps the thread linked
2. Never start a new thread for an existing topic
3. Include thread context in replies (the receiver may have lost context to compaction)

## Closing a Thread

- Any party can signal **RESOLVED** to close a collaborative thread
- For task-handoff, receiver signals **DONE** with results summary
- For question/review-request, the reply itself closes the thread
- fire-and-forget has no thread to close

## Ownership in Collaborative Threads

When two projects collaborate, the opening message MUST declare:
- **Who develops** — which project writes the code/config
- **Who deploys** — which project deploys changes to their environment
- **Who decides** — who has final say on approach (usually the domain owner)

Example from the message:
> "You develop (CKG engine), I deploy (project-tools integration). Either can propose, domain owner decides."

## Priority Mapping

| Priority | Meaning | Expected Response Time |
|----------|---------|----------------------|
| urgent | Blocking work right now | Same session |
| normal | Important but not blocking | Next check_inbox cycle |
| low | FYI / when you get to it | No time pressure |

## Anti-Patterns

- Sending a task_request with no done criteria
- Starting a collaborative thread with no ownership declaration
- Replying to a RESOLVED thread without re-opening it explicitly
- Using broadcast for something that should be a targeted message
- Sending multi-paragraph context when a 3-line summary would do

---
**Version**: 1.0
**Created**: 2026-03-29
**Updated**: 2026-03-29
**Location**: knowledge-vault/40-Procedures/inter-claude-conversation-protocol.md
