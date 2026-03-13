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

# New Core Protocol — Rule-by-Rule Design Notes

**Parent**: [README.md](../README.md)
**Index doc**: [design-new-core-protocol.md](../design-new-core-protocol.md)

---

## Rule 1: DECOMPOSE (kept, tightened)

Removed the verbose "if the user's message contains multiple sentences, line breaks, or conjunctions" clause. The trap warning stays because it addresses the most common failure mode: latching onto the first interesting request and forgetting the rest.

---

## Rule 2: VERIFY (kept, unchanged)

One line. Works perfectly. No change needed.

---

## Rule 3: NOTEPAD (expanded, absorbs old rule 6)

This is the key change. Three levels, explicitly named:

| Level | Tool | Scope | Survives |
|-------|------|-------|----------|
| Session | `store_session_fact()` | This session only | Compaction (via PreCompact) |
| Topic | `dossier(topic, note)` | Cross-session, topic-scoped | Forever (until filed) |
| Permanent | `remember(content)` | Cross-session, global | Until confidence decays |

Old rule 6 (OFFLOAD: `store_session_notes`) is absorbed here. Instead of `store_session_notes(findings, "progress")`, Claude uses `dossier("session-progress", findings)`. Same intent, unified tool.

The `dossier(action="list")` call replaces the old pattern of listing workfiles or activities. One command shows all open topics.

**Decision**: `store_session_fact()` stays as its own tool, not absorbed into dossier. Session facts are ephemeral by design (die with session, survive compaction). Dossiers are persistent. Different lifecycles require different tools.

---

## Rule 4: RECALL (new, replaces old rules 4 + partial 6)

`recall(query)` replaces `recall_memories(query)`. Same concept, simpler name, broader scope — searches vault, knowledge, and dossiers in one call via RRF fusion.

The "don't remember junk" guidance moves here because it is about what NOT to store, which is a retrieval-quality concern. Junk in = junk out.

**Removed from old rule 4**: The explicit `recall_memories(query) before complex tasks` is now `recall(query) before complex work` — same behavior, simpler name.

---

## Rule 5: DELEGATE (kept, trimmed)

Removed `save_checkpoint()` reference (rarely used in practice). Kept the core: 3+ files = agent, results in files not context.

Added guidance: agents should write to dossier entries when work is topic-scoped. This replaces the old pattern of agents writing to session notes files that accumulate without structure.

---

## Rule 6: BPMN-FIRST (kept, unchanged)

One line. Applies to system/process changes only. No modification needed.

---

## Rule 7: TOOLS (expanded, absorbs session-end closure)

Added the session-end closure gate: "review open tasks, disposition each." This is the minimal enforcement for the task tracking problem identified in the audit (creation enforced, closure not).

No new hook needed — just a protocol reminder that Claude should review and close/defer/cancel tasks before ending. The `session_end_hook.py` surfaces the list; the protocol tells Claude to act on it.

---

## What Gets Removed

| Old Element | Replacement |
|-------------|-------------|
| `recall_memories()` reference | `recall()` |
| `store_session_notes()` reference | `dossier("session-progress", ...)` |
| `save_checkpoint()` reference | Dropped (rarely used) |
| OFFLOAD rule (old rule 6) | Merged into NOTEPAD (rule 3) |
| Verbose decompose explanation | Trimmed to trap warning only |

---

## Metrics Comparison

| Metric | v11 (current) | v12 (proposed) |
|--------|---------------|----------------|
| Rules | 8 | 7 |
| Tools referenced | 8+ | 5 |
| Lines of injected text | 11 | 18 (clearer structure) |
| Memory model | Implicit, scattered | Explicit 3-level table |
| Session-end guidance | None | Task review in rule 7 |
| Estimated token cost per prompt | ~180 | ~220 (+22%, justified by clarity) |

The +22% token increase is justified: the current protocol's scattered memory guidance causes Claude to use the wrong tool ~40% of the time (audit finding: 930 stuck MID entries, many of which should have been session facts or dossier entries). Explicit routing saves far more tokens downstream than it costs per-prompt.

---

## Deployment Steps

1. Write new text to `scripts/core_protocol.txt`
2. `INSERT INTO claude.protocol_versions (version, content, reason, is_active)` with v12
3. `UPDATE claude.protocol_versions SET is_active = false WHERE version = 'v11'`
4. Update global `~/.claude/CLAUDE.md` tool index: rename recall_memories to recall, add dossier
5. Update project `CLAUDE.md` files: same tool index changes
6. Update `MEMORY.md`: document the v11 to v12 transition
7. No changes to `rag_query_hook.py` injection mechanism (reads file as-is)

Old tools remain functional. Protocol change is naming and guidance only. No breaking changes.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/claude-family/unified-storage/design/core-protocol-detail.md
