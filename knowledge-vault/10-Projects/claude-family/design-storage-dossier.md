---
projects:
- claude-family
- project-metis
tags:
- design
- storage
- unified
- dossier
synced: false
---

# Unified Storage Design — Dossier Pattern and Storage Simplification

**Parent**: [design-unified-storage.md](../../../docs/design-unified-storage.md)

---

## The Dossier Pattern

A dossier is a Zettelkasten "index note" adapted for AI agents. It solves the core problem: Claude works on something across 5 sessions, and by session 3 has forgotten what happened in session 1.

### Data model (on existing `project_workfiles` table)

```
project_workfiles row types:
  component = "WCC Design"   title = "_index"        → Dossier metadata (JSON)
  component = "WCC Design"   title = "2026-03-12T10:30"  → Entry 1
  component = "WCC Design"   title = "2026-03-12T14:15"  → Entry 2
  component = "WCC Design"   title = "2026-03-13T09:00"  → Entry 3
```

The `_index` row content is JSON:

```json
{
  "status": "open",
  "created": "2026-03-12",
  "entry_count": 3,
  "summary": "Designing activity-based context assembly for CF",
  "tags": ["wcc", "context", "retrieval"]
}
```

### Lifecycle

```
CREATE              JOT              JOT              FILE
  |                  |                |                 |
  v                  v                v                 v
[_index created] → [entry 1] → [entry 2] → ... → [status=filed]
                                                       |
                                                       v
                                              Still searchable via recall()
```

### What goes where

| Use dossier | Use remember() | Use store_session_fact() |
|-------------|----------------|--------------------------|
| Multi-session topic work | Single atomic fact | Within-session ephemeral |
| "WCC Design", "F130 Refactor" | "pgvector 0.8 fixes filtered HNSW" | "current DB password is X" |
| Accumulates entries over time | One entry, updated on conflict | Dies with session |
| Filed when done | Lives until archived by decay | Not cross-session |

### Activity detection replacement

Current WCC activity detection is broken (`wcc_assembly.py` absent, silently disabled). Dossiers replace it:

1. RAG hook queries open dossiers for current project
2. Prompt text matched against dossier `_index` summaries + tags (embedding similarity)
3. If match found (similarity > 0.6), inject dossier index + last 3 entries as context
4. No explicit activity table needed. The open dossier IS the activity context.

This is simpler, already has a working backing store, and requires no new tables.

### Core Protocol integration

Dossier gets added to Core Protocol rule 3 (NOTEPAD):

> **NOTEPAD**: `store_session_fact()` for credentials/decisions/progress (session-scoped). `dossier(topic, note)` for multi-session topic work. `dossier(action="list")` to see open topics.

This is the adoption fix. Workfiles failed because they were not in the protocol Claude reads every prompt.

---

## Storage Simplification

### Current state: 15 mechanisms

| Mechanism | Rows | Status |
|-----------|------|--------|
| `session_facts` | 676 | Healthy |
| `knowledge` MID | 930 | 96% stuck, polluted |
| `knowledge` LONG | 127 | Promotion broken |
| `knowledge_relations` | 67 | 9.3% edge:node, marginal |
| `project_workfiles` | 3 | Best design, zero adoption |
| `vault_embeddings` | 12,345 | Healthy reference |
| `todos` | 2,711 | Creation enforced, closure not |
| `activities` | 0 | Framework only |
| `messages` | 187 | Active, low-volume |
| `audit_log` | 254 | Active |
| `sessions` | 906 | Active |
| `mcp_usage` | 6,965 | Dead (synthetic) |
| `enforcement_log` | 1,333 | Dead (zombie) |
| Session notes files | 7 | Inconsistent |
| `MEMORY.md` | 1 | Highest quality |

### Future state: 7 mechanisms

| Mechanism | Role | Change |
|-----------|------|--------|
| `session_facts` | Session notepad | **KEEP** unchanged |
| `knowledge` | Facts, patterns, decisions | **MERGE** tiers. Confidence-ranked. |
| `project_workfiles` | Dossiers (topic notepads) | **PROMOTE** to primary tool |
| `vault_embeddings` | Reference documentation | **KEEP** unchanged |
| `todos` | Task tracking | **FIX** add source, closure gate |
| `MEMORY.md` | Always-loaded project memory | **KEEP** unchanged |
| `messages` | Inter-Claude communication | **KEEP** unchanged |

### What gets dropped

| Table | Rows | Reason | Action |
|-------|------|--------|--------|
| `mcp_usage` | 6,965 | 100% synthetic data, corrupts analysis | TRUNCATE + DROP |
| `enforcement_log` | 1,333 | Zombie writes, no consumers | TRUNCATE + DROP |
| `workflow_state` | ? | Dead table, never referenced | DROP |
| `knowledge_retrieval_log` | ? | Dead table | DROP |
| `activities` | 0 | Replaced by dossier detection | DROP |

### What gets frozen

| Mechanism | Action |
|-----------|--------|
| `knowledge_relations` | Stop using in retrieval. Keep table for historical reference. No new writes. |
| Session notes files | Stop creating. Existing ones left in place. Use `dossier("session-progress")` instead. |

### Knowledge table changes

```sql
-- Remove tier dependency from queries (keep column for migration)
-- Add confidence-only ranking
-- Backfill: MID entries get confidence 50, LONG entries get confidence 75

UPDATE claude.knowledge SET confidence = 50 WHERE tier = 'mid' AND confidence IS NULL;
UPDATE claude.knowledge SET confidence = 75 WHERE tier = 'long' AND confidence IS NULL;

-- New index for confidence-based retrieval
CREATE INDEX idx_knowledge_confidence ON claude.knowledge(confidence DESC)
  WHERE tier != 'archived';
```

The `tier` column stays in the schema for backward compatibility but is no longer used for routing or promotion. Only `confidence` and `last_accessed` drive ranking and lifecycle.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/claude-family/design-storage-dossier.md
