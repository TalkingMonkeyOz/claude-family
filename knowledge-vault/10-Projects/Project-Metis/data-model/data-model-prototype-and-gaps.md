---
tags:
  - project/Project-Metis
  - type/handoff
  - domain/data-model
  - from/claude-family
created: 2026-03-11
synced: false
---

# Data Model — Prototype Report, Enterprise Gaps, Dead Weight

Back to: [[handoff-data-model-response]]

---

## 3-Tier Memory Prototype — Honest Report

### What works:
- **Concept is correct.** Short/mid/long maps to session→working→institutional. METIS four-layer architecture is a better framing of the same idea.
- **`remember()` auto-routing** by type works. Credentials → session_facts, patterns → knowledge. Zero friction.
- **Dedup/merge** at >85% cosine similarity prevents exact duplicates.

### What doesn't:
- **Promotion is broken.** 96% stuck at mid because `times_applied >= 3` is never reached. Nobody calls `mark_knowledge_applied()`. Event-driven promotion (retrieve + task success) would work better.
- **Decay doesn't decay.** Uses `created_at` not `last_accessed_at`. New knowledge decays faster than old.
- **Three retrieval paths for same data.** `recall_memories()` (MCP), `query_knowledge_graph()` (RAG hook), `query_knowledge()` (RAG hook fallback). Different thresholds, scoring, formatting. No dedup between them.
- **Duplicate consolidation logic** in `server.py:2098` AND `session_startup_hook:283`. Identical thresholds that can silently diverge.

### Performance reality:
- **Latency**: 300-600ms per question prompt (3-5 DB connections, 1-2 Voyage API calls)
- **Token injection**: 400-1900 tokens/prompt (not "85% reduction" — that claim compares vs hypothetical full-vault load)
- **DB connections**: 4 per prompt, each opened/closed separately (no pooling)

### For METIS:
1. One retrieval path, not three. Single entry point, scoring, dedup.
2. Connection pooling — one connection per hook invocation.
3. `token_count` on every stored item for budget-capped retrieval.
4. Event-driven promotion — don't require explicit API calls.

---

## Enterprise Gaps

### Multi-Tenancy
**Current**: Single-tenant. No `tenant_id` anywhere. `project_id` is closest scoping.

**Recommendation**: `tenant_id UUID NOT NULL` on every data table. PostgreSQL RLS for hard isolation. Shared tables (Product Domain, API Reference) use `tenant_id = NULL`. RLS policies check `current_setting('app.current_tenant')`.

**Why RLS**: Schema-per-tenant is operationally expensive (migrations run N times). RLS gives same isolation, one schema, one migration path.

### Event-Driven Freshness
**Current**: Time-based only (`updated_at`, 90-day archive).

**METIS needs**: `freshness_score` (0-1) from: source file age, last verified, change events, retrieval feedback. When vault doc re-embedded → mark derived knowledge as "potentially stale". Freshness as retrieval signal — boost fresh, demote stale.

### Chunking Strategy
**Current**: Fixed 1000-char, 200-char overlap. No content-type awareness.

**METIS needs**: Content-aware chunking — markdown headers as boundaries, code blocks kept whole, tables kept whole. Type-specific: API spec → by endpoint, OData → by entity, process → by step. Metadata per chunk: `content_type`, `token_count`, `source_section`.

### Co-Access Tracking
**Current**: Does not exist. Biggest gap vs library science principles.

**METIS needs**: Log chunks retrieved together per prompt. Build co-retrieval scores over time. Use as retrieval signal: "when X retrieved, Y is also useful." More valuable than pre-computed graph edges.

---

## Dead Weight (Don't Carry Forward)

| Table | Rows | Reason |
|-------|------|--------|
| `books` / `book_references` | 0 | Never adopted |
| `compliance_audits` | 0 | Never used |
| `conversations` | 0 | Extractor exists, nobody runs it |
| `workflow_state` | 0 | State machine uses `workflow_transitions` only |
| `process_data_map` | 0 | Never populated |
| `rag_query_patterns` | 0 | Never populated |
| `*_versions` (3 tables) | 0 each | Version tracking never written to |
| `rag_feedback` | 0 | Write-only, never affects retrieval |
| `rag_doc_quality` | 0 | Write-only, never affects retrieval |
| `enforcement_log` | ~0 | Zombie writes, never queried |
| `knowledge_routes` | 0 | WCC routing — never used |
| `activities` | 0 | WCC activity detection — never used |

**Also needs redesign**: `documents` (over-engineered), `knowledge_relations` (sparse), `knowledge_retrieval_log` (barely used), `todos` (structural limitation).

**Works well**: `session_facts`, `knowledge` (fix tiers), `vault_embeddings` (add metadata), `sessions`, `feedback`/`features`/`build_tasks`, `audit_log`, `project_workfiles`.

---

## METIS Knowledge Type Mapping

| # | METIS Type | CF Equivalent | Key Gaps to Close |
|---|-----------|---------------|-------------------|
| 1 | Product Domain | `vault_embeddings` + `documents` | `token_count`, `content_type`, `freshness_score`, content-aware chunking |
| 2 | API/Integration | `vault_embeddings` (API docs) | Endpoint-aware chunking, schema version tracking |
| 3 | Client Config | No equivalent | Build from scratch. KV pattern + `tenant_id` (hard isolated) |
| 4 | Process/Procedural | `knowledge` + `project_workfiles` | `tenant_id` (shared with variants). Workfile "component" maps to process scoping |
| 5 | Project/Delivery | No equivalent | External sync (Jira/Confluence), cached not owned. Needs TTL/refresh |
| 6 | Learned/Cognitive | `knowledge` (3-tier) + `session_facts` | Fix promotion, `token_count`, `tenant_id` (hard isolated). Two tiers not three |

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/data-model-prototype-and-gaps.md
