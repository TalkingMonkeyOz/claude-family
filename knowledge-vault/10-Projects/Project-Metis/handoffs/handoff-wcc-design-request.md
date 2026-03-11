---
tags:
  - project/Project-Metis
  - type/handoff
  - domain/work-context-container
  - domain/augmentation-layer
  - domain/architecture
  - target/claude-family
created: 2026-03-10
from: claude-desktop (METIS project)
to: claude-family
status: pending
priority: high
depends-on: handoff-data-model-request.md
---

# METIS Work Context Container — Full Design Handoff to Claude Family

## What This Is

John says to stop trying to design this from the outside and give you the full context instead. You've researched it, built the prototype, modelled it in BPMN. We need to formalise the Work Context Container (Option C — Smart Context Assembly) as the core mechanism of the METIS Augmentation Layer. This is the biggest remaining design piece.

This document gives you EVERYTHING we've decided in the design sessions so you can come back with the complete WCC design. Not piecemeal questions — a proper handoff.

---

## DECISIONS MADE (all confirmed by John)

### Option C Chosen
- Target is Option C (Smart Context Assembly), not B
- C encompasses B and adds significantly
- Overhead needs solving but destination is clear
- You're building Option B (~80% done) in CF infra NOW — Option C additions come once B works
- This serves METIS AND all other projects

### Where It Lives in the Architecture
- Work Context Container IS the Augmentation Layer's core mechanism — not a new box
- Decomposes at C4 Level 3 as a sub-component of the Augmentation Layer
- John delegated C4 mapping to Claude Desktop, accepted all recommendations

### All 7 Library Science Principles Accepted
1. Multi-dimensional tagging — don't force knowledge into one box, tag on all dimensions
2. Canonical naming — one name per thing, aliases map to it (authority control)
3. Multi-level abstraction — same idea exists as decision, design doc, code, test (FRBR)
4. Optimise for use, not storage — Ranganathan's First Law
5. Proactive surfacing — knowledge should find you, not the other way around
6. Co-access tracking — items retrieved together are related, even if embeddings disagree
7. Lifecycle management — automate promotion/decay or drown in stale knowledge

### Four-Layer Context Management Architecture (decided this session)
This is the KEY framing. John corrected my initial approach of fixed token budgets. The design is:

1. **Core Protocols** — always present, tiny (~500-1K tokens). Instructs model to break down every user input into tasks. Multiple requests get decomposed. This is a system prompt concern.

2. **Session Notebook** — session facts, write things down as you go so they survive compaction. This is WHY Claude Code handles compaction better than Desktop. External DB persistence + re-injection on demand.

3. **Knowledge Retrieval (The Librarian)** — chunked, embedded, indexed. Retrieve relevant chunks, NOT whole documents. The librarian retrieves by the chunk, not the book. Real proof point: loading full OData metadata kills context instantly. Retrieving relevant entities costs a fraction.

4. **Persistent Knowledge** — patterns, gotchas, decisions that matter across sessions. Stored in knowledge graph, recalled by semantic search when relevant. The "you shouldn't have to rediscover this" layer.

**NOT a fixed token budget. Dynamic priority system.** The elephant analogy: one bite at a time.

### Retrieval Priority Order (8 levels, decided in KE session)
Token-budgeted, each level fires only if budget remaining:
1. Session facts (always, small, critical)
2. Work context container scope (narrows everything else)
3. Cognitive memory/learned (gotchas, patterns)
4. Knowledge graph relations (2-hop walk)
5. Product domain docs (vector similarity)
6. API/Integration reference (only if integration work)
7. Client config (only if specific client)
8. Project/Delivery (Jira/Confluence, lowest — most transient)

### RBAC (confirmed this session)
- Tenant-level hard isolation: Client Config + Learned/Cognitive
- Shared across tenants: Product Domain, API Reference
- Shared with tenant variants: Process/Procedural
- Tenant-scoped: Project/Delivery
- Roles: Platform Builder (all tenants), Enterprise Admin (their tenant), Enterprise Staff (work-context scoped)

### 6 Knowledge Types (with ingestion models)
1. Product Domain — bulk import, release-event triggered
2. API/Integration Reference — semi-automated from OData/OpenAPI + manual
3. Client Configuration — manual at project setup, human-validated, tenant-scoped
4. Process/Procedural — iterative capture through work (work IS the documentation)
5. Project/Delivery — live sync from Jira/Confluence, cached not owned
6. Learned/Cognitive — auto-captured via remember(), 3-tier promotion

### Decay/Promotion/Freshness
- Cognitive: Short→Mid (referenced/acted on), Mid→Long (3+ uses across contexts), Long→Archived (contradicted by change event)
- Document freshness scoring: last verified, change events, retrieval feedback
- Event-driven staleness, NOT time-driven

---

## WHAT'S STILL OPEN (for you to design)

### 1. Activity Space Entity Design
How does the system know what you're currently working on? What defines an "activity"? Is it a task, a session, a feature, a user request? This is the scoping mechanism that makes Level 2 in the retrieval priority work.

### 2. Multi-Signal Ranking
How does the librarian decide WHICH chunks to retrieve? Vector similarity alone isn't enough. What signals combine? Recency, co-access, freshness score, task relevance, retrieval feedback — how do these weight against each other?

### 3. Agentic Routing (Option C's distinguishing feature)
The system doesn't just assemble context passively — it proactively routes knowledge. When does it decide to go fetch something vs wait to be asked? This is what separates C from B.

### 4. Feedback Loops
How does retrieval quality get measured and fed back? Implicit feedback (rephrasing, "that's wrong"), explicit feedback, A/B retrieval comparison. This overlaps with retrieval quality metrics.

### 5. Data Model
Covered in the separate `handoff-data-model-request.md`. The WCC design needs to work with whatever schema we land on.

### 6. Mechanics of the Four Layers
The principles are set. The mechanics of "load this, release that, persist this through compaction" need working through. How do the four layers interact in practice during a real work session?

---

## WHAT YOU HAVE THAT I DON'T

- The actual working prototype you just built
- BPMN models of the retrieval/assembly process
- Real performance data from the 3-tier memory system
- Knowledge of what works and what's dead weight in the current CF schema
- The 5 research documents you produced (which we reviewed and accepted)
- Your instinct for what's buildable vs theoretical

---

## WHAT WE EXPECT BACK

A complete WCC design document that covers:
1. The Activity Space entity and how scoping works
2. Multi-signal ranking algorithm (or at least the design)
3. Agentic routing triggers and rules
4. Feedback loop design
5. How it maps to the four-layer context management architecture
6. How it maps to the 8-level retrieval priority
7. How it interacts with the data model (once you've responded to that request too)
8. What you've learned from building the prototype that changes any of the above

Write it to vault: `knowledge-vault/10-Projects/Project-Metis/work-context-container-design.md`

If any of the decisions above need challenging based on what you've learned building the prototype, say so. John's principle: if we need to build something better from scratch, that's what happens. No sentimentality.

---

## KEY PRINCIPLE (from John, non-negotiable)

**Humans produce artifacts; AI accelerates.** The Augmentation Layer is not the headline — it's the engine that makes everything else work. If it doesn't work well with non-technical people in a contained sandbox, nothing else matters.

---
*From: Claude Desktop (METIS session 2026-03-10) | Depends on: handoff-data-model-request.md response*
