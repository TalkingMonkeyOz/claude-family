---
projects:
- claude-family
- project-metis
tags:
- audit
- storage
- cognitive-memory
- data-model
synced: false
---

# Storage Mechanisms Audit — Part 1: Facts, Knowledge, Workfiles

**Index**: [storage-audit index](../../../docs/audit-storage-mechanisms.md) (relative path: `docs/audit-storage-mechanisms.md`)
**Part 2**: [vault, todos, WCC, misc](storage-audit-part2.md)
**Audit date**: 2026-03-12

---

## 1. Session Facts (SHORT Tier)

| Attribute | Value |
|-----------|-------|
| Table | `claude.session_facts` |
| Row count | ~676 (2026-03-12); 394 at 2026-02-28 |
| Growth rate | ~23 new facts/day across all projects |
| Status | Active, healthy |

**What it stores**: Session-scoped notepad: credentials, config values, endpoints, decisions, notes, data references. UPSERT on `(session_id, fact_key)` — one value per key per session. 7 `fact_type` values; in practice note/decision/config dominate.

**When triggered**: Explicit `store_session_fact()` calls. Core Protocol Rule 3 mandates this for credentials, decisions, findings. Also written by `remember()` short-path when type is credential/config/endpoint.

**Retrieval**: `recall_memories()` allocates 20% of the 1,000-token default to SHORT tier, ordered by type priority (decision first, credentials last). `recall_previous_session_facts()` scans back exactly 3 sessions.

**Design flaw**: Cross-session recovery is session-count dependent, not time-based. A project running 20 sessions/day loses day-1 decisions by day 2. Projects with fewer sessions retain them longer — inconsistent and unpredictable.

**Overlap**: `note`/`decision` types overlap with MID-tier knowledge. Facts worth keeping beyond 3 sessions should be in `knowledge` but auto-promotion only fires for closed sessions (Gap in `consolidate_memories()` Phase 1). WCC assembly queries session_facts as one of 6 sources, consuming 10% of WCC budget.

---

## 2. Knowledge — MID Tier

| Attribute | Value |
|-----------|-------|
| Table | `claude.knowledge` (tier='mid') |
| Row count | ~930 (2026-03-12); ~987 per 2026-03-11 session notes |
| Status | Active but polluted |

**What it stores**: Working knowledge — learned facts, decisions, notes, data references. Intended destination for anything worth keeping beyond the current session that is not yet a proven pattern.

**When triggered**: `remember()` default tier, `store_knowledge()` legacy tool, `end_session()` learnings, `extract_insights()` from JSONL conversation logs.

**Retrieval**: `recall_memories()` mid-tier query using pgvector cosine similarity >= 0.4. Composite score: similarity × 0.4 + recency × 0.3 + access_freq × 0.2 + confidence × 0.1. Recency decays over 90 days.

**Data quality issues**:
- Junk entries: `agent1_complete`, `agent2_complete` — session artifact strings stored as knowledge
- Confidence=65 for all session-promoted facts (fixed default, not earned)
- Cross-project bleed: Nimbus payroll data alongside CF infrastructure patterns
- Duplicate clusters across agents, timeouts, and config variants

**Overlap**: Heavily overlaps with vault_embeddings — many entries derived from vault docs with no provenance link back (Gap G2). Overlaps with session_facts for short-lived decisions that never get promoted. Overlaps with session notes files for progress tracking content.

---

## 3. Knowledge — LONG Tier

| Attribute | Value |
|-----------|-------|
| Table | `claude.knowledge` (tier='long') |
| Row count | ~127 (2026-03-12); 12% of total knowledge |
| Status | Active, promotion pipeline broken |

**What it stores**: Proven patterns, gotchas, preferences, procedures — knowledge validated through repeated use. `remember()` with type=pattern/procedure/gotcha/preference routes directly here.

**Promotion problem**: `consolidate_memories()` Phase 2 promotes MID→LONG when `access_count >= 5 AND age >= 7d`. The promotion criteria are duplicated in `server.py:2102` and `session_startup_hook_enhanced.py:289` — these can diverge if one is updated without the other. As of 2026-03-11, 96% (987 of 1,026) entries are stuck at MID despite the system running for months. The fix (retrieval-frequency-based promotion replacing broken `times_applied >= 3`) was identified 2026-03-11 but not yet deployed.

**Retrieval**: Same pgvector query as MID but threshold 0.35 (not 0.40) and a 1-hop graph walk via `knowledge_relations` for connected entries (fixed score of 0.3 for graph-discovered entries — always ranked below direct matches).

**Overlap**: 127 LONG entries are the authoritative patterns, but vault docs in `30-Patterns/` and `40-Procedures/` contain much of the same content, already embedded in `vault_embeddings`. MEMORY.md also duplicates top-tier patterns.

---

## 4. Knowledge Relations (Graph Layer)

| Attribute | Value |
|-----------|-------|
| Table | `claude.knowledge_relations` |
| Row count | 67 (2026-02-28) |
| Edge:node ratio | 9.3% (67 edges / 717 nodes) |
| Status | Active, practically ineffective |

**What it stores**: Directed typed edges between knowledge entries. Auto-created `relates_to` links when `remember()` finds cosine similarity 0.50–0.85 with existing entries. Manual types (extends, contradicts, supports, supersedes, requires, example_of) have never been used.

**Graph usage**: 1-hop walk in `recall_memories()` long-tier retrieval returns graph-discovered entries at a fixed score of 0.3, ranking them below all direct matches. Maximum 5 graph entries per retrieval call.

**Dead weight assessment**: 67 edges across 717+ nodes implies only ~22-23 `remember()` calls triggered auto-linking. The graph adds code complexity (2 SQL queries per `recall_memories()` call) without meaningful retrieval benefit at current scale. The 6 non-auto edge types have never been instantiated.

---

## 5. Project Workfiles

| Attribute | Value |
|-----------|-------|
| Table | `claude.project_workfiles` |
| Row count | ~3 (2026-03-12 session notes) |
| Table created | 2026-03-09 |
| Status | Built, not adopted |

**What it stores**: Cross-session component-scoped working context. Filing cabinet metaphor: project = cabinet, component = drawer, title = file. UPSERT on `(project_id, component, title)`. Supports append mode (concatenates with `\n---\n` separator). 16 columns, Voyage AI embeddings, 7 indexes.

**When triggered**: Explicit `stash()` calls only. Core Protocol (8 rules injected every prompt) does not mention `stash()` — only `remember()` and `store_session_fact()` appear by name. Without explicit protocol prompting, Claude defaults to those tools.

**Design strengths**: Cleanest table in the schema. No deprecated columns, clear semantics, BPMN coverage, partial index on `is_pinned`. `linked_sessions` array tracks which sessions contributed to each workfile.

**Adoption problem**: 3 entries across 24 active projects after 3 days. WCC draws 25% of its 1,500-token budget from workfiles as source #1 — but with only 3 rows, this budget is always wasted. Pinned workfiles are injected at precompact P3.5 priority (component name and title only, not content).

**Overlap**: Direct functional overlap with session notes files (same use case: persistent cross-session context). Also overlaps with session_facts (decisions) and knowledge MID (findings).

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/Project-Metis/audits/storage-audit-part1.md
