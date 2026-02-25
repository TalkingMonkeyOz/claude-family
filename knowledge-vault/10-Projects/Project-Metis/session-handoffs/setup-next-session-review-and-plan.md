---
tags:
  - project/Project-Metis
  - session-handoff
  - scope/system
  - type/session-prep
created: 2026-02-24
session: pending-review-and-plan
---

# Session Prep: Gap Review, Features & Examples, Plan of Attack

**Objective:** Three deliverables from this session:
1. Address all known gaps (close what we can, flag what needs input)
2. Second-pass review with concrete features and real examples
3. Build plan — what gets built first, dependencies, minimum viable platform

**Read first:** Level 0 README, this document, then work through sections in order.

---

## PART 1: GAP CATALOGUE

Every open question from every brainstorm file, categorised by severity.

### 🔴 CRITICAL GAPS (block build or significantly affect architecture)

**GAP-1: Knowledge Graph / Explicit Relationships (Area 1)**
- Source: KE deep dive §9, flagged by John as CRITICAL
- Decision D-ARCH-14 says "start with relations table" but the DESIGN is missing
- Need: relationship types, creation mechanism (manual/AI/automatic), query interface, how /ask uses relationships alongside vector search
- Why critical: without this, cross-referencing across knowledge sources is vector-similarity only — won't capture causal/structural chains

**GAP-2: Integration Hub has NO design (Area 2)**
- Source: integration-hub/README.md — connector list only, no design
- Chat #4 was SUPERSEDED ("plumbing, not a design problem")
- But: connector pattern, auth handling, error strategy, data flow mapping, two-way sync design are all missing
- Why critical: Phase 1 deliverable. Can't connect to time2work without this.
- Note: the README lists what each connector does but not HOW. The standardised connector interface needs specifying.

**GAP-3: Session Memory file is UNVALIDATED (Area 7)**
- Source: session-memory-context-persistence.md — comprehensive but Claude monologue
- Content actually covers most of Chat #8b (Context Assembly) gaps too
- The context assembly sequence, token budgets, RAG vs cache interaction, overflow strategy — all there
- Why critical: John hasn't reviewed. Contains major architectural decisions (scratchpad design, context assembly order, two-tier model) that need validation before build
- Action: John reviews this file. If he agrees, Chat #8b is effectively DONE and this file becomes the authoritative design.

**GAP-4: Evaluation Framework (Area 1)**
- Source: KE deep dive §9
- No test questions defined, no retrieval accuracy baseline, no evaluation methodology
- Why critical: Research says 73% of RAG deployments fail. Evaluation from day one is the primary mitigation.
- Need: 50+ test questions with known-correct answers, scoring methodology, baseline targets

### 🟡 IMPORTANT GAPS (need resolving but don't block Phase 0-1)

**GAP-5: Chunking Strategy (Area 1)**
- How to break long documents into knowledge items
- Current thinking: natural boundaries > fixed token counts
- Need: specific approach per knowledge category (one endpoint per chunk for APIs, one pattern per chunk for implementation knowledge, etc.)
- Can resolve during Phase 1 build

**GAP-6: Knowledge Expiry/Staleness (Area 1)**
- How does knowledge age? Review cycles? Freshness indicators?
- Need: staleness detection, review triggers, confidence decay model
- Can resolve during Phase 2

**GAP-7: BPMN Process Count for MVP (Area 9)**
- How many BPMN processes does the minimum viable platform actually need?
- Current list has 9+ process candidates across 3 tiers
- Need: which 3-5 are essential for Phase 1-2
- Can resolve during plan of attack discussion

**GAP-8: Two-Way Sync Conflict Resolution (Area 5)**
- When a defect is updated in both The System and external tracker simultaneously
- Need: conflict resolution strategy (last-write-wins? merge? alert?)
- Can resolve during Phase 2-3 when support integration is built

**GAP-9: Background Agent Job Scheduling (Area 4 + Area 7)**
- Area 4 describes background agent jobs (regression analysis, pattern detection, test coverage reviews)
- Area 7 doesn't describe the scheduling/triggering infrastructure for these
- Need: job queue, scheduling mechanism, result handling
- Can resolve during Phase 2

**GAP-10: External Rule Change Discovery (Area 4)**
- How does the platform know when external rules change (legislation, product updates)?
- Need: ingestion trigger design, notification mechanism
- Can resolve during Phase 2-3

**GAP-11: Commercial Model for The System (Area 8 + Product Definition)**
- nimbus pricing exists (Doc 3). System-level pricing doesn't.
- SaaS? Per-seat? Licensing? Self-hosted vs managed?
- Need: at least a direction before approaching second customer
- Not blocking for nimbus deployment

### 🟢 NICE-TO-HAVE / DEFERRED GAPS

**GAP-12: Multi-product customers** — Can defer to Year 2
**GAP-13: Customer Scenario Replication (Area 4)** — Explicitly deferred, nice-to-have
**GAP-14: Generic integration catalogue** — Emerges from first few customers
**GAP-15: Dog-fooding loop formalization** — Conceptual, not blocking build
**GAP-16: Client-facing self-service portal** — Future phase

### CROSS-AREA ALIGNMENT ISSUES

**CROSS-1: Area 9 (BPMN) is dependency for Area 4 (Quality) test generation**
- Area 4 says "BPMN process maps are the primary source for test generation"
- Area 9 has process definitions but no design for how Area 4 queries them
- Need: interface between BPMN process registry and test generation engine

**CROSS-2: Area 5 two-way sync is an Area 2 connector concern**
- Support talks about two-way defect sync with external trackers
- Integration Hub should own the sync mechanism
- Need: Area 2 connector spec for bidirectional issue tracker sync

**CROSS-3: Orchestration (Area 7) needs job scheduling for Area 4 background agents**
- Quality describes scheduled/triggered AI analysis jobs
- Orchestration doesn't describe how to schedule non-interactive agent work
- Need: job queue / scheduler design in Area 7

**CROSS-4: Knowledge Engine categories (Area 1) and BPMN validation workflows (Area 9)**
- KE has 6 configurable categories with different validation tiers
- BPMN has 3-tier enforcement
- How does "Category B knowledge requires Tier 2 validation" map to a BPMN workflow?
- Need: explicit mapping of knowledge category → validation BPMN process

---

## PART 2: FEATURES & EXAMPLES

The brainstorms describe systems and data flows. This section describes what users actually DO with the platform, with concrete examples.

### Feature Catalogue (What a User Sees)

**To be built during session** — structure below, content discussed live:

1. Ask the Knowledge Engine a question (support, delivery, management)
2. Ingest new knowledge (API spec, implementation pattern, compliance rule)
3. Create a client engagement and configure the delivery pipeline
4. Generate configuration from requirements
5. Run validation tests and review results
6. Capture and triage a defect
7. Generate documentation from system state
8. Review project health dashboard
9. Promote knowledge from client to product level
10. Configure a constrained deployment for a specific role

Each feature needs: who uses it, what they see, what happens behind the scenes, nimbus/Monash example.

---

## PART 3: PLAN OF ATTACK

### What Builds First (Dependency Chain)

```
Phase 0: Foundation
├── PostgreSQL + pgvector (everything depends on this)
├── Git repo + CI/CD pipeline
├── Core schema (organisations, products, clients, knowledge_items, sessions, work_items, audit_log)
├── Authentication (JWT + basic RBAC)
└── Agent conventions (CLAUDE.md, core protocol)

Phase 1: Knowledge Engine + Integration Layer
├── Embedding provider interface + Voyage AI implementation
├── Knowledge ingestion pipeline (/ingest, /ingest/batch)
├── Knowledge search (/search — semantic retrieval)
├── Knowledge ask (/ask — LLM-synthesised answers)
├── time2work API connector (auth, CRUD, rate limiting)
├── time2work OData connector
├── First knowledge load (time2work API docs, known patterns)
├── Evaluation framework (50+ test questions, scoring)
├── Scratchpad / session memory
└── Basic audit logging

Phase 2: First Customer Deployment (nimbus)
├── Monash-specific knowledge ingestion (EAs, configs)
├── Constrained deployment (system prompt + cached knowledge + classifier)
├── Delivery pipeline (requirements → config → test → deploy → docs)
├── Jira integration (enhanced — automated defect creation, sync)
├── Configuration generation from requirements
├── Pay scenario validation (expected vs actual)
├── Living documentation generation
├── BPMN gates for critical workflows (3-5 processes)
└── Support triage (basic)

Phase 3: Platform Hardening
├── Multi-client isolation
├── Full RBAC
├── Background agent jobs (scheduled analysis)
├── Compliance dashboard
├── Knowledge promotion workflow
├── Two-way defect sync with external trackers
└── Performance and resilience testing
```

### Minimum Viable Platform (What Proves Value)

To discuss: what's the absolute minimum that proves the concept to nimbus management and Monash?

Candidates:
- Knowledge Engine that answers time2work questions correctly
- One constrained deployment (nimbus support assistant)
- One delivery pipeline stage working (config generation OR pay scenario testing)
- Documentation generated from actual system state

### Timeline Estimate

To discuss based on Phase 0-1 scope.

---

## SESSION PLAN

Suggested order of work:

1. **John reviews session-memory-context-persistence.md** — if validated, Chat #8b is effectively done (15 min)
2. **Address GAP-1 (Knowledge Graph)** — design relationship types, creation, querying (30 min)
3. **Address GAP-2 (Integration Hub connector interface)** — standardised pattern, enough to build time2work connector (20 min)
4. **Walk through Feature Catalogue** — concrete user stories with nimbus/Monash examples (30 min)
5. **Plan of Attack** — sequence, dependencies, minimum viable platform, timeline (30 min)
6. **Address remaining yellow gaps** as time permits

---
## PRE-SESSION TASK — ✅ COMPLETE

**Vault folder renamed:** `nimbus-ai-platform/` → `Project-Metis/` — **DONE**
- 48 markdown files updated, 52 files total across 11 subdirectories
- Wiki-links, frontmatter tags, inline references, workspace.json all updated
- 0 remaining references to old name in vault
- Ready for commit

**Vault path is now:** `C:/Projects/claude-family/knowledge-vault/10-Projects/Project-Metis/`

---
*Prep document created 2026-02-24 for next session*
