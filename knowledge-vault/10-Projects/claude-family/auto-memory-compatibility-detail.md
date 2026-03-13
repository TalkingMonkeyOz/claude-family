---
projects:
- claude-family
tags:
- memory
- auto-memory
- architecture
synced: false
---

# Auto-Memory Compatibility — Detail

Detailed analysis backing [docs/auto-memory-compatibility-review.md](../../../docs/auto-memory-compatibility-review.md).

---

## Conflict Analysis by Dimension

### Dimension 1: Write Conflicts

| System | What writes | Where | Trigger |
|--------|-------------|-------|---------|
| Native auto-memory | Terse session notes | `~/.claude/.../memory/MEMORY.md` | Claude decides autonomously |
| `remember()` | Structured knowledge (MID/LONG tier) | `claude.knowledge` table | Explicit tool call or Core Protocol rule 4 |
| `store_session_fact()` | Session-scoped key-value pairs | `claude.session_facts` table | Explicit tool call |
| `stash()` | Component working context | `claude.project_workfiles` table | Explicit tool call |
| RAG hook | Nothing — read-only | N/A | Every prompt |

No write collision exists — different storage media (file vs PostgreSQL). However, if auto-memory is active it can write to MEMORY.md at any time, overwriting or appending curated content and pushing it past the 200-line injection limit.

### Dimension 2: Injection Duplication

| Source | Mechanism | Token cost |
|--------|-----------|------------|
| MEMORY.md (native) | Auto-injected first 200 lines | ~1,400 tokens |
| Core Protocol (custom) | `rag_query_hook.py` every prompt | ~30 tokens |
| RAG vault results | `rag_query_hook.py` semantic query | Variable |
| WCC assembly | `rag_query_hook.py` when activity detected | Variable |
| Pinned workfiles | `precompact_hook.py` at compaction | Variable |

MEMORY.md currently contains the Cognitive Memory System description, the Workfiles description, and the Hook Scripts table — all of which also appear in CLAUDE.md and are available via RAG. This is approximately 1,400 tokens of duplication per session.

### Dimension 3: The 200-Line Hard Cap

MEMORY.md is currently 233 lines. Claude Code silently drops lines 201–233. The dropped content is the BPMN Process Architecture section and the Schema Governance section — both high-value technical references that Claude never sees at session start.

This is an active reliability problem independent of the auto-memory question.

### Dimension 4: Quality Degradation Risk

If auto-memory is active, Claude will add notes during sessions. Because MEMORY.md is hand-curated and already over the 200-line limit:
- Auto-written notes push existing content further past the limit
- Low-value transient notes mix with permanent architecture knowledge
- The `standards_validator.py` hook does not cover writes to `~/.claude/` (outside the project directory)

### Dimension 5: `autoMemoryEnabled` Setting Status

Not found in any settings file:
- `C:\Projects\claude-family\.claude\settings.local.json`
- `C:\Users\johnd\.claude\settings.json`
- `C:\Users\johnd\.claude\settings.local.json`

`CLAUDE_CODE_DISABLE_AUTO_MEMORY` environment variable is also not set. Auto-memory is running at its default state: **enabled**.

---

## Why `remember()` Supersedes Auto-Memory

| Capability | Native auto-memory | `remember()` |
|------------|-------------------|--------------|
| Quality gate | None | Rejects < 80 chars, junk patterns |
| Deduplication | None | Similarity threshold 0.75 |
| Searchability | File grep only | Voyage AI embeddings + pgvector |
| Lifecycle | Accumulates indefinitely | Promote, decay, archive |
| Structured retrieval | First 200 lines only | 3-tier budget-capped recall |
| Cross-project | No (per working tree) | Yes (project-scoped query) |
| Audit trail | None | DB timestamps + access counts |

---

## Implementation Steps

### 1. Disable auto-memory

The settings.local.json is generated from the database. Do not manually edit it.

```sql
UPDATE claude.workspaces
SET startup_config = startup_config || '{"autoMemoryEnabled": false}'::jsonb
WHERE name = 'claude-family';
```

Then regenerate: `python scripts/generate_project_settings.py claude-family`

Alternatively, add `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` to the project launcher `.bat` and `.env`.

### 2. Trim MEMORY.md to under 200 lines

Move lines 201–233 (BPMN Process Architecture and Schema Governance) to topic files:
- `~/.claude/projects/C--Projects-claude-family/memory/bpmn-architecture.md`
- `~/.claude/projects/C--Projects-claude-family/memory/schema-governance.md`

Add one-line index entries in MEMORY.md pointing to each. Claude reads topic files on demand.

### 3. Add protection comment to MEMORY.md

```markdown
<!-- MANUALLY MAINTAINED. Auto-memory is disabled for this project.
     Use remember() MCP tool for learned patterns instead. -->
```

---

## Ownership Boundary Reference

| System | Owns | Does NOT own |
|--------|------|--------------|
| MEMORY.md | Stable reference injected every session with no tool overhead | Transient facts, task context, anything already in DB |
| `remember()` | Patterns, gotchas, decisions — searchable, tiered, embeddable | Static reference content every session needs unconditionally |
| `store_session_fact()` | Within-session state surviving compaction | Cross-session persistence |
| `stash()` | Component working context bridging sessions | Global architecture knowledge |
| RAG vault | Full docs, SOPs, domain knowledge on demand | Per-session guaranteed injection |
| Auto-memory | Disabled — superseded by `remember()` | — |

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: knowledge-vault/10-Projects/claude-family/auto-memory-compatibility-detail.md
