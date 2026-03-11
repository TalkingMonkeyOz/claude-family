---
projects:
- project-metis
- claude-family
tags:
- research
- data-model
- schema
synced: false
---

# Schema Detail: `claude.knowledge_relations`

Back to [[schema-index]]

**Row count (audit 2026-02-28)**: 67
**Purpose**: Directed, typed edges in the knowledge graph. Created automatically by `remember()` (auto-link when new entry has 0.50–0.85 cosine similarity with existing entries) and manually via `link_knowledge()`.

---

## Columns

| # | Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | `relation_id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| 2 | `from_knowledge_id` | `uuid` | NO | — | Source knowledge entry (FK) |
| 3 | `to_knowledge_id` | `uuid` | NO | — | Target knowledge entry (FK) |
| 4 | `relation_type` | `varchar` | NO | — | Edge type (see enum below) |
| 5 | `strength` | `float` | YES | NULL | Cosine similarity at link creation (0.0–1.0) |
| 6 | `notes` | `text` | YES | NULL | Manual annotation |
| 7 | `created_at` | `timestamptz` | YES | `NOW()` | Creation timestamp |

Source: INSERT statements in `server.py` lines 1979–1983 (auto-link) and 2198–2205 (manual link).

---

## relation_type Enum

| Value | Created By | Description |
| --- | --- | --- |
| `relates_to` | Auto-link in `remember()` | Semantic similarity (only type auto-created) |
| `extends` | Manual `link_knowledge()` | Builds upon or elaborates |
| `contradicts` | Manual | Conflicting information |
| `supports` | Manual | Corroborating evidence |
| `supersedes` | Manual | Replaces older entry |
| `requires` | Manual | Dependency relationship |
| `example_of` | Manual | Concrete example of abstract concept |

The auto-link path exclusively creates `relates_to`. All other types require explicit `link_knowledge()` calls. In practice, only `relates_to` edges are likely represented in the 67 rows.

---

## Unique Constraint

```sql
ON CONFLICT (from_knowledge_id, to_knowledge_id, relation_type)
DO UPDATE SET strength = EXCLUDED.strength, notes = EXCLUDED.notes
```

At most one relation of each type between any ordered pair. The graph is **directed** — A→B is distinct from B→A.

---

## Indexes

| Index | Type | Columns | Purpose |
| --- | --- | --- | --- |
| `knowledge_relations_pkey` | btree (PK) | `relation_id` | PK |
| Unique constraint index | btree | `(from_knowledge_id, to_knowledge_id, relation_type)` | Dedup |
| `idx_kr_from` | btree | `from_knowledge_id` | Outgoing edge lookup |
| `idx_kr_to` | btree | `to_knowledge_id` | Incoming edge lookup |
| `idx_kr_type` | btree | `relation_type` | Type filtering |

---

## Foreign Keys

| Column | References | On Delete |
| --- | --- | --- |
| `from_knowledge_id` | `claude.knowledge.knowledge_id` | CASCADE |
| `to_knowledge_id` | `claude.knowledge.knowledge_id` | CASCADE |

---

## Graph Traversal in `recall_memories()`

The long-tier retrieval does a 1-hop walk (both directions) from LONG-tier seed entries:

```sql
SELECT DISTINCT k.knowledge_id, k.title, k.description, k.knowledge_type,
    k.confidence_level, kr.relation_type
FROM claude.knowledge_relations kr
JOIN claude.knowledge k ON (
    (kr.to_knowledge_id = k.knowledge_id AND kr.from_knowledge_id = ANY(%s::uuid[]))
    OR
    (kr.from_knowledge_id = k.knowledge_id AND kr.to_knowledge_id = ANY(%s::uuid[]))
)
WHERE k.tier IN ('mid', 'long') AND kr.strength >= 0.3
LIMIT 5
```

Minimum retrieval strength: 0.3. Seeds: up to 8 LONG-tier entries. Max graph-discovered additions: 5 per call.

---

## Density Assessment

- 717 knowledge entries, 67 edges → edge:node ratio = 0.093
- Each `remember()` auto-link creates up to 3 `relates_to` edges for similar existing entries
- 67 edges implies roughly 22–23 `remember()` calls triggered auto-linking
- The graph is very sparse — most entries have no outgoing or incoming edges
- The 1-hop walk rarely finds useful additional context in practice

---

## METIS Assessment Notes

**Gap**: No provenance metadata on edges. The table does not record which session created the relation, which code path triggered it, or when. This makes graph curation and quality auditing difficult.

**Gap**: The similarity window for auto-link (0.50–0.85) was chosen to avoid trivially similar pairs (>0.85 → merge instead of link) and dissimilar pairs (<0.50 → unrelated). This heuristic has not been validated against actual knowledge quality in the current corpus.

**Opportunity**: The `strength` column enables weighted graph traversal. METIS could use edge weights in ranking rather than the current binary include/exclude at threshold 0.3.

---

## Source Code References

- `mcp-servers/project-tools/server.py` lines 1963–1984 (auto-link in `tool_remember`)
- `mcp-servers/project-tools/server.py` lines 2178–2218 (`link_knowledge` manual)
- `mcp-servers/project-tools/server.py` lines 1719–1734 (graph walk in `recall_memories`)
- `mcp-servers/project-tools/server_v2.py` lines 3524–3530 (`graph_search` docstring)

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-knowledge-relations.md
