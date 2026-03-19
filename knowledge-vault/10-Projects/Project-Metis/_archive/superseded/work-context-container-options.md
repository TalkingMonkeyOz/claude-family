---
projects:
  - Project-Metis
tags:
  - project/Project-Metis
  - type/design
  - topic/context-assembly
  - topic/work-context-container
created: 2026-03-10
updated: 2026-03-10
status: active
---

# Work Context Container — Design Options Detail

Parent document: [[work-context-container-synthesis]]

---

## Option A: Unified Query (Minimal Change)

Add a single function that calls existing tools in parallel and merges results:

```
work_context(activity="parallel-runner", budget=2000) →
  recall_memories("parallel runner", budget=500)
  + get_work_context("current")
  + unstash("parallel-runner")
  + rag_search("parallel runner nimbus-mui")
```

**Pros**: Minimal new code, uses existing systems, quick to implement.
**Cons**: No authority control, no co-access tracking, no dossier persistence, budget management is crude. "Parallel-runner" and "batch-pipeline" won't connect.

---

## Option B: Activity Space (Recommended First Step)

Create a first-class `activity` entity that aggregates context sources:

```sql
CREATE TABLE claude.activities (
    activity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES claude.projects,
    name TEXT NOT NULL,              -- "parallel-runner"
    aliases TEXT[],                  -- ["batch-pipeline", "pipeline executor"]
    knowledge_refs UUID[],          -- linked knowledge entries
    workfile_refs UUID[],           -- linked workfiles
    feature_refs UUID[],            -- linked features
    vault_queries TEXT[],           -- saved RAG queries that work well
    last_accessed TIMESTAMPTZ,
    access_count INT DEFAULT 0,
    co_access_log JSONB DEFAULT '[]' -- items retrieved together
);
```

When the user says "I'm working on parallel runner":
1. Look up the activity (fuzzy match on name + aliases)
2. Load linked workfiles, knowledge, features
3. Run saved RAG queries
4. Track co-access for new items retrieved during the session
5. Update access patterns

**Pros**: True dossier model, authority control via aliases, co-access tracking, persistent across sessions.
**Cons**: New table, new tool, needs activity creation/management workflow.

### How Activities Get Created

**Literary warrant principle**: Activities are created from actual usage, not pre-planned. Two approaches:

1. **Explicit**: User or AI calls `create_activity("parallel-runner")` when starting focused work
2. **Implicit**: The system notices repeated `unstash("parallel-runner")` + `recall_memories("parallel runner")` calls and suggests creating an activity

Option 2 follows the library science principle of literary warrant — build the catalog from what exists, not from theory.

### Activity Lifecycle

Borrowing from records management lifecycle:

| Phase | Trigger | Behavior |
|---|---|---|
| **Created** | First focused work on a component | Empty activity with name |
| **Active** | Items linked during sessions | Refs accumulate, co-access tracked |
| **Semi-active** | No access for 14+ days | Still searchable, lower retrieval priority |
| **Archived** | Feature completed or project phase ends | Preserved but excluded from default queries |

---

## Option C: Smart Context Assembly (Full Vision)

Build the context assembly orchestrator from [[augmentation-layer-research]]:

1. **Classify the activity** using faceted analysis (project × component × task type × domain)
2. **Route queries** to the right knowledge sources (agentic retrieval)
3. **Rank results** using multiple signals (embedding similarity + recency + access frequency + co-access + tier confidence)
4. **Budget context** intelligently (more budget to sources with higher-quality matches, not equal splits)
5. **Learn from feedback** — assembled context that gets used increases weight; ignored context decreases

### Multi-Signal Ranking

Current retrieval uses embedding similarity alone. The filing research shows access patterns carry strong signal:

| Signal | Weight | Source |
|---|---|---|
| Embedding similarity | 0.3 | pgvector cosine distance |
| Recency | 0.2 | `last_accessed_at` |
| Access frequency | 0.15 | `access_count` |
| Co-access pattern | 0.15 | Retrieved together with current items |
| Tier confidence | 0.1 | LONG > MID > SHORT |
| Explicit linking | 0.1 | In activity refs or knowledge_relations |

### Agentic Routing

Instead of searching everything, route to the right source:

```
"How does retry work?" → Procedural knowledge (skills, SOPs)
"What's the current status?" → Project tracking (features, tasks)
"What did we decide about batch size?" → Cognitive memory (decisions)
"What's the OData endpoint?" → API reference (vault docs)
```

Classification can be rule-based initially, ML-based later.

---

## Library Science Principle Mapping

| Library Principle | Option A | Option B | Option C |
|---|---|---|---|
| Faceted classification | Partial (query terms) | Yes (activity facets) | Full (auto-classification) |
| Authority control | No | Yes (aliases) | Yes (learned synonyms) |
| FRBR hierarchy | No | Partial (refs to items) | Yes (work→expression→item) |
| Cross-references | No | Yes (refs arrays) | Yes (typed relations) |
| Relative location | Yes (embeddings) | Yes (embeddings + refs) | Yes (multi-signal) |
| Literary warrant | No | Yes (from usage) | Yes (from usage + learning) |
| Save the time | Partial | Yes | Full |
| Controlled vocabulary | No | Partial (aliases) | Yes (synonym learning) |
| Dossier/case file | No | Yes | Yes |
| Co-access tracking | No | Yes (log) | Yes (ranking signal) |
| Retention schedules | No | Yes (lifecycle) | Yes (activity-aware decay) |

---

## Implementation Path: B → C

### Phase 1 (Option B Core)

1. Create `claude.activities` table
2. Add `work_context(activity_name)` MCP tool — unified query across all 6 sources
3. Alias-based fuzzy matching for activity lookup
4. Auto-link items retrieved during a session to the active activity
5. Basic co-access logging

### Phase 2 (B+)

6. Implicit activity creation from repeated component access patterns
7. Activity lifecycle management (active → semi-active → archived)
8. Co-access patterns influence retrieval ranking
9. Saved RAG queries — remember which vault queries returned useful results

### Phase 3 (Evolve to C)

10. Multi-signal ranking (replace pure embedding similarity)
11. Query routing to appropriate knowledge sources
12. Budget optimization based on source quality
13. Feedback loop — learn which assembled context gets used

---

## Related Documents

- [[work-context-container-synthesis]] — Problem framing, gap analysis, recommendation
- [[library-science-research]] — Classification, cataloging, retrieval research
- [[filing-records-management-research]] — Filing, records lifecycle, activity-based computing
- [[augmentation-layer-research]] — Industry context, CoALA, context engineering

---

**Version**: 1.0
**Created**: 2026-03-10
**Updated**: 2026-03-10
**Location**: knowledge-vault/10-Projects/Project-Metis/research/work-context-container-options.md
