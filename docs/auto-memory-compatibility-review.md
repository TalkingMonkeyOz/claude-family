---
projects:
- claude-family
tags:
- memory
- auto-memory
- architecture
- compatibility
synced: false
---

# Auto-Memory Compatibility Review

Analysis of whether Claude Code's native auto-memory conflicts with our custom memory systems.

**Full details**: See [knowledge-vault/10-Projects/claude-family/auto-memory-compatibility-detail.md](../knowledge-vault/10-Projects/claude-family/auto-memory-compatibility-detail.md)

---

## What Native Auto-Memory Does

- Writes to `~/.claude/projects/C--Projects-claude-family/memory/MEMORY.md` and topic files
- First 200 lines of MEMORY.md injected into every session automatically
- On by default (v2.1.59+); controlled via `autoMemoryEnabled` setting or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`
- Topic files are NOT loaded at session start — read on demand

---

## Current State

| Question | Answer |
|----------|--------|
| Write collision between native and custom systems? | No — different storage media (file vs PostgreSQL) |
| Content duplication in context injection? | Yes — MEMORY.md repeats content already in CLAUDE.md and RAG |
| Auto-memory writing organically to MEMORY.md? | Not detectably — content is clearly manual |
| `autoMemoryEnabled` explicitly set? | No — running at default (enabled) |
| 200-line limit respected? | No — file is 233 lines, last 33 silently truncated |
| Auto-memory poses future risk? | Yes — will degrade curated content over time if left enabled |

---

## Recommendations

1. **Disable auto-memory for this project** — our `remember()` / `recall_memories()` system is strictly superior (quality gate, dedup, embeddings, lifecycle). Add `"autoMemoryEnabled": false` to `workspaces.startup_config` in DB, then regenerate settings.

2. **Trim MEMORY.md to under 200 lines** — move the BPMN and Schema Governance sections (currently truncated at line 201+) into topic files: `memory/bpmn-architecture.md` and `memory/schema-governance.md`.

3. **Establish a clear ownership boundary** — see detail doc for the full boundary table.

4. **Add a warning comment to MEMORY.md** to signal manual-only intent.

---

## Ideal Boundary (One Line Each)

| System | Owns |
|--------|------|
| MEMORY.md (manual) | Stable reference injected every session with zero tool-call overhead |
| `remember()` / `recall_memories()` | Learned patterns, gotchas, decisions — queryable, tiered, embeddable |
| `store_session_fact()` | In-session state that must survive compaction |
| `stash()` / `unstash()` | Working context bridging sessions within a component |
| RAG vault | Full docs, SOPs, domain knowledge — semantic search on demand |
| Auto-memory | **Disabled** — replaced by `remember()` |

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: C:\Projects\claude-family\docs\auto-memory-compatibility-review.md
