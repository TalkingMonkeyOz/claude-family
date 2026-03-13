# Task Tracking Audit — Index

**Date**: 2026-03-12

Full audit report is in the knowledge vault (classified as `detailed`, not `working`):

- **Full report**: `knowledge-vault/10-Projects/claude-family/task-tracking-audit.md`

---

## One-Line Verdict

Task tracking produces compliance theater. Tasks are created to satisfy the discipline hook, never closed. Features stall in `in_progress` indefinitely. Feedback accumulates at `new`. The system needs a closure gate, not more creation-side enforcement.

---

## Critical Bugs (Act On These)

| Bug | File | Action |
|-----|------|--------|
| Three DB validators are non-functional (parse CLI args, receive JSON on stdin) | `.claude-plugins/.../validate_db_write.py` et al. | Fix or remove |
| `session_end_hook.py` fact promotion never fires (ordering bug) | `scripts/session_end_hook.py` | Fix ordering |

---

## Recommended Changes

1. Add a session-end gate that reviews open tasks before closing
2. Add a `source` column to `claude.todos` (`TodoWrite` vs `TaskCreate`) to separate the two systems
3. Surface a completion ratio (completed/total) in session startup to make backlog growth visible
4. Drive feedback triage through a BPMN workflow with enforcement, not just advisory surfacing

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: docs/audit-task-tracking.md
