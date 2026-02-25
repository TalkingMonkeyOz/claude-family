---
tags:
  - session/handoff
  - project/Project-Metis
created: 2026-02-23
---

# Session Handoff: Knowledge Engine Deep Dive (Chat #2)

**Date:** 2026-02-23
**Chat:** Focused Chat #2 — Knowledge Engine Deep Dive
**Status:** COMPLETE

## What We Did

Completed the Knowledge Engine deep dive — stack validation, domain structure, knowledge taxonomy, ingestion pipelines, full API contract, and build sequence.

**Key reframe during session:** The System is built from scratch. Claude Family provides lessons and concepts only — no schema migration, no inherited tables. Prior work is the source of "what works and what doesn't", not a codebase to evolve.

**New convention established:** All System design docs get a header block with scope + design principles. Claude Family lessons captured inline where relevant (not separate sections).

## Vault File Produced

`knowledge-engine/brainstorm-knowledge-engine-deep-dive.md` — comprehensive brainstorm capture covering:
- Stack validation (Voyage AI, pgvector, custom RAG, LLM abstraction)
- Four-level scope hierarchy (Org → Product → Client → Engagement)
- Knowledge promotion mechanism (up with anonymisation + approval)
- Six configurable knowledge categories (A-F, including new Category D: Customer Context)
- Eight ingestion pipeline patterns
- 10+ API endpoints with request/response shapes
- Build sequence (6 steps)
- Open questions

## Key Decisions This Session

| Decision | Outcome |
|----------|---------|
| Build approach | Clean slate. No migration from Claude Family schemas. |
| Document headers | Scope + design principles block on every System design doc |
| Lessons capture | Inline where relevant, not separate section |
| Scope hierarchy | Org → Product → Client → Engagement (locked) |
| Knowledge categories | Six defaults (A-F), configurable per organisation |
| Category D | NEW: Customer Context — org structure, people, tech landscape, business context |
| Embedding provider | Pluggable interface. Voyage AI first, alternatives designed in. |
| API design | /ask (LLM) vs /search (retrieval) separated. 10+ endpoints. |
| Promotion | First-class operation with anonymisation workflow |

## What's Next (Per Master Tracker)

Remaining focused chats — all NOT STARTED:
1. ~~BPMN / SOP & Enforcement~~ ✓ Done (Chat #1)
2. ~~Knowledge Engine Deep Dive~~ ✓ Done (Chat #2)
3. Constrained Deployment Implementation
4. Integration Hub Connectors
5. PS Accelerator + Monash Technical
6. Quality & Compliance Design
7. Commercial & Management Prep
8. Orchestration Build Specs
9. Project Mgmt & Lifecycle
10. Merge & PID

## Open Questions Carried Forward

- Chunking strategy for long documents
- BPMN workflow mapping per knowledge category
- Knowledge graph endpoint (/knowledge/graph?)
- Knowledge staleness/expiry model
- Evaluation framework (test questions, metrics)
- Multi-product cross-boundary knowledge sharing
- Bulk historical ingestion strategy for new customer onboarding
