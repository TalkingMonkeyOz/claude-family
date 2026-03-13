---
projects:
  - Project-Metis
tags:
  - session-handoff
created: 2026-03-12
status: superseded-by-2026-03-13
---

# Session Handoff — 2026-03-12 — Data Model + WCC Review

## Session Starter
```
Read this handoff first: C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\session-handoffs\2026-03-12-data-model-wcc-review.md

Then call start_session(project="metis") and recall_previous_session_facts(project_name="metis", n_sessions=3).
```

---

## What Was Accomplished

### Gate 0 — CLOSED (2/2 gaps)
- SPD updated with four-layer architecture (Augmentation Layer as THE CRUX)
- Division of labour added to stakeholders-decision-rights.md

### Gate 1 — ALL GENUINE DECISIONS RESOLVED (7/7)
- 5 deferred as nimbus-specific (not platform design gaps)
- BPMN-to-test-case ownership: Area 4 owns generation, Area 9 provides models
- User Loader v2: nimbus-specific, removed from platform scope
- Git provider: deferred to Gate 3, architecture already provider-agnostic
- consolidation-gaps.md updated with all resolutions

### Data Model Assessment — COMPLETE (8/8 CF recommendations reviewed)
1. token_count on everything + max chunk size + no data loss on split + linked retrieval (part_of/sequence relations)
2. Single retrieval path — one entry point, one scoring, one log
3. Event-driven freshness (not time-based decay)
4. Co-access tracking from day one
5. Two knowledge tiers (session-scoped + persistent), event-driven promotion
6. Separate DB per customer, NO RLS — Org to Product to Client to Engagement four-tier scope hierarchy within an instance
7. Content-aware chunking — different strategies per content type, with escape hatch for super-large items
8. Connection pooling — implementation detail, no decision needed

### WCC Design Review — COMPLETE (5 docs reviewed)
- Activity Space concept: CONFIRMED, plus four-level detection hierarchy:
  1. Explicit user/session override (user brings the dossier)
  2. AI asks when ambiguous (not confident enough to auto-detect)
  3. Embedding-based auto-detect (0.6+ threshold)
  4. Classifier/reviewer service checks assignments over time
- Single ranking pipeline with 6 signals: CONFIRMED
- Agentic routing: YES, but NO keyword/rule-based classifier. John's experience: keyword matching consistently poor, RAG/embeddings far better. Routing classifier must use embedding-based detection from start. CF rule-based Phase 1 overridden.
- RLS references in WCC docs partially updated (main overview + activity entity). Remaining docs may still reference tenant_id/RLS — needs sweep.

---

## Doc Updates Made This Session
- system-product-definition.md — four-layer architecture (Gate 0 gap 1)
- gates/gate-zero/stakeholders-decision-rights.md — division of labour (Gate 0 gap 2)
- gates/consolidation-gaps.md — all resolutions marked
- ps-accelerator/README.md — User Loader v2 reference removed
- wcc/work-context-container-design.md — RLS replaced with separate-DB + 4-tier scope
- wcc/wcc-activity-space-design.md — tenant_id replaced with scope_org_id

---

## Still Open

### Immediate Next
1. WCC doc sweep — remaining RLS/tenant_id references in ranking-design, mechanics-feedback-design, ranking-agentic-routing docs
2. Agentic routing redesign — CF needs to rethink routing mechanism using embeddings/RAG instead of keyword/regex. Send message to CF with this decision.
3. Plan-of-attack rewrite brief — update with ALL confirmed decisions from this session + prior, then hand off to CF

### Deferred
4. FB174: Gate-based design methodology skill (high priority, capture while process is fresh)
5. Follow up on msg 67d8af18 (vault sync to claude-family)
6. Gate 2/3 gaps awareness scan
7. Granola MCP integration for meeting transcripts

---

## Key Principle Reinforced This Session
No keyword matching anywhere in the retrieval pipeline. RAG/embeddings have been consistently superior by a large margin. This applies to activity detection (already decided) AND agentic routing (decided this session). The entire retrieval system should be embedding-first.
