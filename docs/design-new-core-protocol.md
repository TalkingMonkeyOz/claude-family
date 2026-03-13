---
projects:
- claude-family
- project-metis
tags:
- design
- storage
- unified
- core-protocol
synced: false
---

# New Core Protocol Design — Index

**Status**: Draft for review
**Parent**: [design-unified-storage.md](design-unified-storage.md)
**Current**: v11 (8 rules) | **Proposed**: v12 (7 rules)
**Detail**: [design-core-protocol-detail.md](../knowledge-vault/10-Projects/claude-family/design-core-protocol-detail.md)

## Change Summary

| Current Rule | Change | Reason |
|--------------|--------|--------|
| 1. DECOMPOSE | Keep (tightened) | Works. Core discipline. |
| 2. Verify | Keep (unchanged) | Works. |
| 3. NOTEPAD | **Expand** with dossier | Multi-session notepad. |
| 4. MEMORY | **Simplify** to recall() | One tool, all sources. |
| 5. DELEGATE | Keep (trimmed) | Works, less verbose. |
| 6. OFFLOAD | **Remove** | Absorbed into rule 3 via dossier. |
| 7. BPMN-FIRST | Keep | Works. |
| 8. Check MCP | Keep, add closure gate | Session-end task review. |

## Proposed v12 Protocol Text

```
STOP. READ ALL of the user's message before acting.

1. DECOMPOSE: Count every request, question, directive. TaskCreate for
   EACH before acting on ANY. TRAP: Don't latch onto first request.

2. VERIFY: Read files, query DB, research. Never guess.

3. NOTEPAD: Three memory levels — use the right one:
   - store_session_fact() — this session (credentials, configs, decisions)
   - dossier(topic, note) — multi-session topic work (open, jot, file)
   - remember(content) — permanent facts/patterns for future sessions
   dossier(action="list") shows open topics. recall(query) before complex work.

4. RECALL: recall(query) searches all sources (vault, knowledge, dossiers).
   Don't remember() junk: acks, handoffs, progress, < 80 chars.

5. DELEGATE: 3+ files = spawn agent. Results to files/dossiers, 1-line
   summaries only. Never let agent output flood context.

6. BPMN-FIRST: Process/system changes — model first, test, then code.

7. TOOLS: MCP first (40+ tools). advance_status/start_work/complete_work
   for state changes. Session-end: review open tasks, disposition each.
```

## Key Design Decisions

1. **3-level memory in one rule** — session fact / dossier / remember. Explicit table replaces scattered references across old rules 3, 4, 6.
2. **recall() replaces recall_memories()** — simpler name, broader scope (vault + knowledge + dossiers).
3. **Session-end closure gate** — rule 7 reminds Claude to review open tasks. Advisory, not blocking.
4. **OFFLOAD removed** — `store_session_notes()` replaced by `dossier("session-progress", findings)`.

## Deployment

Update `scripts/core_protocol.txt`, increment to v12 in DB, update CLAUDE.md tool index. No code changes to injection mechanism (`rag_query_hook.py` reads the file as-is).

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\design-new-core-protocol.md
