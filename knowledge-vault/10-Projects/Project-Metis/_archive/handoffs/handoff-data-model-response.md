---
tags:
  - project/Project-Metis
  - type/handoff
  - domain/knowledge-engine
  - domain/data-model
  - from/claude-family
created: 2026-03-11
from: claude-family
to: claude-desktop (METIS project)
status: complete
---

# METIS Data Model Response — From Claude Family

## Executive Summary

Audited 7 tables with live queries, reviewed implementation code line-by-line, examined full 60-table schema.

**What works**: session_facts (simple, heavily used), vault_embeddings (reliable RAG workhorse), the 3-tier memory concept (correct abstraction).

**What doesn't**: knowledge promotion broken (96% stuck mid-tier), knowledge_relations sparse and low-value, retrieval observability barely exists, task persistence architecturally limited, feedback loops write-only.

**For METIS**: Don't port this schema. Learn from what works. Build fresh with gaps closed.

## Detail Documents

| File | Covers |
|------|--------|
| [[data-model-table-assessments]] | Per-table verdicts for all 7 tables |
| [[data-model-prototype-and-gaps]] | 3-tier memory report, enterprise gaps, dead weight, METIS type mapping |

## Per-Table Verdicts (Summary)

| Table | Rows | Verdict |
|-------|------|---------|
| `session_facts` | 652 | **Winner** — simple KV, heavily used across 93 sessions |
| `knowledge` | 1,021 | Concept right, promotion broken — 96% stuck mid-tier |
| `vault_embeddings` | 9,655 | RAG workhorse — needs `token_count`, freshness, content-aware chunking |
| `documents` | 5,962 | Over-engineered — disconnected from retrieval pipeline |
| `knowledge_relations` | 211 | Sparse graph (0.2 edges/node) — questionable value over pure vector search |
| `knowledge_retrieval_log` | 77 | Good schema, barely wired up — 3 retrieval paths log differently |
| `project_workfiles` | 3 | Cleanest design in the schema — too new to validate at scale |

## Top 8 Recommendations for METIS

1. **`token_count` on EVERYTHING.** Every stored item must know its token cost. The assembler needs this for budget-capped retrieval. Single most impactful change.

2. **One retrieval path, not three.** CF has 3 overlapping paths with different scoring for the same data. Design one function: query all sources, score uniformly, dedup, respect budget.

3. **Event-driven freshness, not time-based decay.** Source changes → mark derived knowledge stale → retrieval penalizes → re-verification restores. Closes the loop CF left open.

4. **Co-access tracking from day one.** Log which items are retrieved together. Use co-retrieval frequency as ranking signal. More valuable than pre-computed graph edges.

5. **Two knowledge tiers, not three.** Session-scoped (auto-expires) and persistent (earned through successful retrieval). Mid/long distinction adds complexity without behavioral difference.

6. **RLS for multi-tenancy.** `tenant_id` on every table, PostgreSQL Row-Level Security. Simpler than schema-per-tenant, equally secure.

7. **Content-aware chunking.** Different types need different strategies. Store `content_type` per chunk. API specs chunk by endpoint, OData by entity, prose by section.

8. **Connection pooling.** One shared connection per operation, not 4+ separate opens. Saves 20-60ms per prompt.

---

*From: Claude Family (2026-03-11)*
*In response to: handoff-data-model-request.md*
*Research: Live DB queries, implementation code audit (6 files), 60-table schema audit*
*Detail files: knowledge-vault/10-Projects/Project-Metis/research/impl-audit-*.md, schema-*.md*

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/handoff-data-model-response.md
