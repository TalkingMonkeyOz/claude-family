---
tags:
  - project/Project-Metis
  - scope/system
  - type/handoff-brief
created: 2026-03-08
purpose: Validated brief for plan-of-attack.md rewrite
supersedes: plan-of-attack.md (2026-02-26, UNVALIDATED)
---

# Plan of Attack — Rewrite Brief

This document captures the validated decisions from the 2026-03-08 walkthrough of `plan-of-attack.md`. The original plan was written 2026-02-26, pre-Gate Zero, and was never validated. This brief should be used by the doc consolidator to produce the rewritten plan.

---

## Validated Decisions

### 1. Build from zero
METIS is purpose-built from the ground up. NOT a fork of Claude Family. Claude Family is knowledge gained — lessons, patterns, what works and what doesn't — but METIS is a clean build. Claude Family contains prototype/test code; some things work well, some don't, some were pie-in-the-sky. Use it as reference, not as codebase.

### 2. Use area-level features (F119-F128) as structure
The old F1-F10 numbering is retired. The rewritten plan should use area-level features registered in the DB as the organising structure, with deliverables broken down within each area.

| DB Feature | Area |
|---|---|
| F119 | Area 1: Knowledge Engine |
| F120 | Area 2: Integration Hub |
| F121 | Area 3: Delivery Accelerator |
| F122 | Area 4: Quality & Compliance |
| F123 | Area 5: Support & Defect Intelligence |
| F124 | Area 6: Project Governance |
| F125 | Area 7: Orchestration & Infrastructure |
| F126 | Area 8: Commercial |
| F127 | Area 9: BPMN / SOP & Enforcement |
| F128 | Constrained Deployment Pattern |

### 3. Augmentation Layer is core Phase 1
The Augmentation Layer (context assembly, cognitive memory, skills framework, RAG orchestration, session management) must be in Phase 1. These are core concepts and tools that allow the system to be useful and hopefully help build itself. Dog-fooding principle: if these tools can't help build METIS, they can't help build anything else.

### 4. Phase 2 is streams, not monolith
Phase 2 is NOT "build all nimbus features at once." Instead: build core system + AI tools (Phase 1), then build out ONE stream end-to-end. Example stream: assisted defect tracking with Jira, ingesting nimbus knowledge from Confluence/Jira/parts of the codebase. Prove that stream works, connect to other systems (e.g. VS Code), add value, improve, identify next stream, build it out. Incremental value delivery, not big-bang.

### 5. Generic framing with nimbus as lead example
Consistent with the system-product-definition scope reframe. The plan should describe phases generically ("first customer stream") with nimbus/Monash as the concrete example, not the only possible path.

### 6. Infrastructure is platform-agnostic
No Azure specificity in the plan. The system runs on any Linux environment with PostgreSQL + pgvector. Infrastructure provider is a customer-specific choice. Remove "Azure Australia East" and all Azure-specific references.

### 7. MVP = one stream working end-to-end
The old MVP definition was: "config generation + validation + documentation for Monash." The new MVP is: one complete stream working end-to-end — e.g. an AI that knows your product/domain, assists your team through a complete workflow (like defect tracking), and gets smarter with each interaction. Simpler and more honest.

### 8. Separate system blockers from customer blockers
The old plan mixed management decisions (Monash go-ahead, Azure access, API access) with system-level work. The rewritten plan should clearly separate system blockers (things that gate the platform regardless of customer) from customer-specific blockers (things that gate a particular deployment).

---

## Proposed Phase Structure

The old plan had 4 phases. The validated structure:

### Phase 0: Foundation
Clean build. PostgreSQL + pgvector, core schema (designed fresh, informed by Claude Family learnings), git repo, auth layer, agent conventions, project structure. No Azure specifics.

### Phase 1: Core Platform
- **Knowledge Engine** (F119): Ingestion, search, embeddings — the brain
- **Augmentation Layer** (cross-cutting): Context assembly, cognitive memory, skills framework, RAG orchestration, session management — the crux
- **Intelligence Layer**: /ask, constrained deployment v1 (F128), prompt construction — sits on top of Augmentation Layer
- **Integration Hub basics** (F120): First connectors
- **Eval framework**: Measure whether it works
- **Basic UI**: Chat interface for /ask
- **Audit logging**: Everything adds value, including observability

Dog-food it — the system should help build itself from this point.

### Phase 2: First Customer Stream
- Ingest customer knowledge (Confluence, Jira, parts of codebase)
- Build ONE end-to-end workflow (e.g. assisted defect tracking)
- Connect to customer systems (Jira, etc.)
- Prove value on a real engagement
- Generic framing; nimbus/Monash is the lead example

### Phase 3+: Expand
- Next stream, next customer system integration
- Harden core based on what Phase 2 revealed
- Each stream builds out more of the Application Services (F121-F124)
- Not a distinct phase — ongoing cycle of stream → prove → expand

---

## What to Reference During Rewrite

| Document | Location | Purpose |
|---|---|---|
| Original plan-of-attack | `plan-of-attack.md` | Structure reference (what existed) |
| System product definition | `system-product-definition.md` (v0.3) | Scope, areas, architecture |
| Design lifecycle | `design-lifecycle.md` | Gate framework, current progress |
| Gate Zero system map | `gate-zero/system-map.md` | C4 L1/L2, 9 logical groups |
| Augmentation Layer research | `research/augmentation-layer-research.md` | CoALA, context engineering patterns |
| Feature catalogue | `feature-catalogue.md` | Feature definitions |
| Ethos | `ethos.md` | Design principles |

---

## Timeline Notes

The old plan estimated "4-5 months total, MVP at 3 months." With clean build + Augmentation Layer added + streams approach, timeline needs fresh estimation in the rewrite. Don't carry over old numbers — re-estimate based on the new structure.

---
*Brief created: 2026-03-08 | Source: Validated walkthrough with John de Vere*
