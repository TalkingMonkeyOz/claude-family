# Task System Discussion - Conversation Excerpts Index

**Source session**: `eaac8b3f-b3fa-4f16-a420-f11e3803e52b` (2026-02-23)
**JSONL**: `C:\Users\johnd\.claude\projects\C--Projects-claude-family\eaac8b3f-b3fa-4f16-a420-f11e3803e52b.jsonl`

## Summary

The user challenged stale/zombie tasks being restored at session start, leading to discovery that Claude Code has native task persistence at `~/.claude/tasks/` — making the DB restore loop redundant.

## Chunks

| File | Contents |
|------|----------|
| [task-excerpts-1-user-messages.md](task-excerpts-1-user-messages.md) | Verbatim user messages + assistant diagnosis |
| [task-excerpts-2-research-findings.md](task-excerpts-2-research-findings.md) | Research agent findings + session-resume before/after |

## Key Facts

- **User's exact complaint** (line 40): "again, the tasks are not great you finished some of these last night. What are your built in task management, is our system breaking your internal task management between sessions? [...] are we trying to solve a problem that no longer exsists?"
- **User's direction after fix** (line 100): "yes, but bpmn model it first and then wwork through the changes."
- **Root cause**: TaskCreate → DB sync → session-resume reads DB → TaskCreate loop. Tasks with `restore_count: 2` = zombie restored indefinitely.
- **Discovery**: `~/.claude/tasks/` has 140 session dirs. Native persistence already exists.
- **Fix**: session-resume v6.0 — display-only, no TaskCreate restoration.

---
**Version**: 1.0
**Created**: 2026-03-04
**Updated**: 2026-03-04
**Location**: C:\Projects\claude-family\docs\task-excerpts-index.md
