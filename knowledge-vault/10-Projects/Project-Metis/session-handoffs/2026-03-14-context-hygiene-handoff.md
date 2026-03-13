---
projects:
  - Project-Metis
tags:
  - session-handoff
created: 2026-03-14
status: active
supersedes: 2026-03-13-self-audit-handoff.md
---

# Session Handoff — 2026-03-14 — Context Hygiene

## Session Starter

```
Read this handoff first: C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\session-handoffs\2026-03-14-context-hygiene-handoff.md

Then call start_session(project="metis") and recall_memories(query="METIS current state", budget=1000, project_name="metis").

DO NOT call recall_previous_session_facts, check_inbox with include_read=true, conversation_search, or recent_chats during orient. The handoff has everything you need.
```

---

## Current State

- **Gate 0:** CLOSED
- **Gate 1:** ALL DECISIONS RESOLVED. 5 docs draft-complete by CF.
- **Gate 2/3:** Material indexed (READMEs with completeness %), not formally started.
- **All CF delegated tasks:** COMPLETE (consolidation, data model, WCC design).
- **Memory edits:** All 17 cleared — auto-generated userMemories covers everything.
- **System map HTML:** Already saved at `gates/gate-zero/system-map.html` (March 8). Removed from project files.

## Priority Actions

### 1. Send plan-of-attack rewrite brief to CF (OVERDUE)
The brief is ready at `plan-of-attack-rewrite-brief.md`. 13 validated decisions. Just needs `send_message` to claude-family as task_request. This has been the #1 action for 3 sessions and keeps not getting done.

### 2. Gate 2/3 awareness scan
Not blocking but useful orientation. CF created `gates/gate-two/README.md` and `gates/gate-three/README.md` with material indexes.

### 3. FB174 status check
Gate-based design methodology skill already written and loaded. Feedback item may still be open in DB — check and resolve.

---

## CONTEXT DISCIPLINE — READ THIS EVERY SESSION

These are hard-won lessons from sessions that burned context and delivered nothing.

### Orient Phase: Be Lean

**DO:**
- Call `start_session()` — it returns everything: project state, previous focus, todos, features, pending messages
- Call `recall_memories()` with budget=1000 — one call, all 3 tiers, budget-capped
- Read THIS handoff file (one file)
- Confirm with John what to work on

**DO NOT:**
- Call `check_inbox(include_read=true)` — this pulls ALL historical messages. Use default (pending only).
- Call `conversation_search` — chat history snippets are huge context cost for marginal value. The handoff has what you need.
- Call `recent_chats` — same problem. Don't load 5 chat summaries when you have a handoff.
- Call `recall_previous_session_facts` — legacy tool, use `recall_memories` instead.
- Call `list_session_facts` — dumps ALL facts into context. Use targeted `recall_session_fact(key)` if needed.
- Load web search results during orient — that's work phase, not orient phase.
- Read multiple vault files "just in case" — read ONE file when you need it for the current topic.

### Work Phase: Stay Focused

**DO:**
- Store decisions immediately with `remember()` or `store_session_fact()`
- `save_checkpoint()` after completing discrete work
- Write vault files when a section is done
- One topic at a time with John

**DO NOT:**
- Pull back full message history with `get_message_history` unless specifically asked
- Do web searches mid-conversation unless John asks for research
- Load tool definitions via `tool_search` more than necessary — each load adds to context
- Monologue — present one topic, get input, capture, move on

### End Phase: Close Clean

**DO:**
- Write a handoff file (like this one)
- Call `end_session()` with meaningful summary
- Give John a copy-paste session starter

**DO NOT:**
- Skip `end_session()` — this is the #1 failure mode. No end = no trace for next session.
- Batch all writes to session end — compaction kills batched work.

### Known Context Traps

1. **`check_inbox(include_read=true)`** — returned 20 messages including a 2000-word ATO tax agent reply. Massive context waste.
2. **`conversation_search`** — returns full chat excerpts, not summaries. 5 results = potentially 10K+ tokens of old conversation loaded for no reason.
3. **`recent_chats`** — similar problem. Each chat summary can be 500+ words.
4. **Web search results** — each search adds ~3-5K tokens of source material. Don't search during orient.
5. **`tool_search`** — each call loads 5 tool definitions. Plan which tools you need and batch the loads.
6. **Project files** — anything attached to the Claude.ai project loads into EVERY conversation. Keep project files minimal. The system map HTML was removed for this reason.
7. **userMemories block** — auto-generated, ~3500 words, loads every chat. Can't control directly but manual memory edits add on top. Keep edits to zero unless truly needed.

### The Golden Rule

If you finish orient and haven't confirmed with John what to work on yet, you've used too much context on orient. Orient should be: start_session + recall_memories + read handoff + ask John. Four steps, minimal context.

---

## Key Architecture Decisions (Reference Only — Don't Load Unless Needed)

All confirmed decisions are in the vault files and in the `remember()` memory system. Don't reproduce them here — that's just more context to load. If you need a specific decision, use `recall_memories(query="decision about X")`.

---

## Session Starter for Next Chat

```
Read this handoff first: C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\session-handoffs\2026-03-14-context-hygiene-handoff.md

Then call start_session(project="metis") and recall_memories(query="METIS current state", budget=1000, project_name="metis").

DO NOT call recall_previous_session_facts, check_inbox with include_read=true, conversation_search, or recent_chats during orient. The handoff has everything you need.

Priority: Send plan-of-attack rewrite brief to CF (overdue 3 sessions).
```

---
*Session: 2026-03-14 | Completed: Memory edits cleanup (17 removed), context discipline documented. System map HTML confirmed already in vault.*
