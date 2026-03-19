---
projects:
  - Project-Metis
tags:
  - project/Project-Metis
  - type/design
  - topic/context-assembly
  - topic/work-context-container
  - topic/knowledge-management
created: 2026-03-10
updated: 2026-03-10
status: active
---

# Work Context Container — Synthesis & Design Direction

## What Problem Are We Solving?

An AI assistant working on a project needs context to be useful. Today, that context is assembled **ad-hoc** — the user provides it manually, hooks inject fragments, and tools return pieces. There is no unified mechanism that says: "I'm working on X, assemble everything I need."

**The core problem**: Context is scattered across 6+ knowledge sources, and no system exists to scope and assemble it based on what the user is actually doing.

### How It Manifests

Consider a single nimbus-mui session: SQL optimization, then deidentification, then parallel runner. Each activity needs completely different context. Today the AI starts each sub-task nearly blind, relying on what's in the conversation window. The user compensates by re-explaining. This is the problem activity-based computing research identified (Gonzalez & Mark, CHI 2004): **context switching cost is dominated by context reconstruction, not task complexity**.

### What "Solved" Looks Like

The user says "I'm working on the parallel runner." The system assembles:

| Knowledge Type | What Gets Pulled | Source |
|---|---|---|
| **Product Domain** | What nimbus-mui does, its data model, business rules | Vault docs, knowledge store |
| **API Reference** | OData endpoints, MUI component API, database schema | Vault docs, embedded references |
| **Client Config** | Nimbus-specific settings, environment details | Session facts, project config |
| **Process/Procedural** | How to build pipelines, testing patterns | Skills, BPMN models, vault SOPs |
| **Project/Delivery** | Current features, build tasks, what's blocked | Work tracking (features/tasks) |
| **Learned/Cognitive** | Previous decisions, gotchas, patterns learned | Memory tiers (short/mid/long) |

This is the **Work Context Container**: a scoped bundle of relevant context drawn from multiple sources, assembled on demand, budget-capped to fit the context window.

---

## What Already Exists (Gap Analysis)

| System | What It Does | Limitation |
|---|---|---|
| `recall_memories(query)` | 3-tier memory search, budget-capped | Single query, no activity scoping |
| `get_work_context(scope)` | Work tracking context (tasks, features) | Only delivery/tracking data |
| `search_workfiles(query)` | Semantic search across workfiles | Only workfile content |
| RAG hook | Auto-injects vault docs on questions | Reactive, not proactive |
| `unstash(component)` | Load component working context | Manual, single component |
| `start_work(task_code)` | Load task + feature plan_data | Only structured plan data |

**The gap**: Six separate retrieval systems with separate queries. No orchestrator assembles a unified context bundle for an activity.

---

## Key Insights from Library Science Research

Full research: [[library-science-research]]

| Library Concept | Application to Work Context Container |
|---|---|
| **Faceted classification** (Ranganathan) | Our 6 knowledge types ARE facets. Search across all simultaneously, not one category. |
| **Authority control** | Need canonical names for components. "Parallel runner" / "batch pipeline" / "pipeline executor" must map to one thing. |
| **FRBR hierarchy** (Work → Expression → Manifestation → Item) | A design decision is a "Work" with multiple expressions: the discussion, the handoff, the code, the test. Surface them all. |
| **Save the time of the reader** (5th Law) | Assembly must be automatic. 10 task switches × 30s manual context = 5 min wasted per session. |
| **KOS spectrum** (folksonomy → ontology) | We're at folksonomy level. Aim for thesaurus: synonym mappings without full ontology cost. |

---

## Key Insights from Filing & Records Research

Full research: [[filing-records-management-research]]

| Filing Concept | Application to Work Context Container |
|---|---|
| **Dossier system** | The Container IS a dossier — all documents related to one case, regardless of type or origin. |
| **Cross-reference cards** | Knowledge items need cross-refs to components, features, and each other. Pointers, not copies. |
| **Records lifecycle → memory tiers** | Already implemented. Filing research adds: retention should be activity-aware (used items get extended). |
| **Activity-based computing** (Bardram, CHI 2006) | Organizing by activity reduces switching overhead 50-75%. Each component could have a persistent activity space. |
| **Co-access patterns** | Items retrieved together are related, even if embeddings disagree. Track co-access. |

---

## Design Options & Recommendation

Three options analyzed in detail: [[work-context-container-options]]

| Option | Approach | Effort | Capability |
|---|---|---|---|
| **A: Unified Query** | Single function calling existing tools in parallel | Low | Limited — no authority control, no persistence |
| **B: Activity Space** | First-class `activity` entity with refs + aliases | Medium | Good — dossier model, authority control, co-access |
| **C: Smart Assembly** | Full context engineering orchestrator with learning | High | Full — agentic routing, multi-signal ranking, feedback loops |

**Recommendation**: **Option B first, evolve to C.** Option A doesn't solve the authority control or co-access problems that library science tells us are critical. Option C is the destination but too much at once. Option B gives us the dossier model, authority control, and a migration path.

---

## Metis Connection

The Work Context Container is the mechanism that makes the METIS Augmentation Layer ([[augmentation-layer-research]]) work as an integrated system rather than separate tools.

| Metis Knowledge Type | Claude Family Source | Assembly Method |
|---|---|---|
| Product Domain | Vault docs (10-Projects/) | RAG scoped to project |
| API Reference | Vault docs (20-Domains/) | RAG scoped to domain |
| Client Config | Session facts, workspaces | Direct lookup by project |
| Process/Procedural | Skills, BPMN, vault SOPs | Process search + skill lookup |
| Project/Delivery | Features, build_tasks, feedback | `get_work_context("feature")` |
| Learned/Cognitive | Memory tiers (short/mid/long) | `recall_memories(activity)` |

### Research Foundation (Share with Claude Desktop)

1. **[[library-science-research]]** — Classification, cataloging, retrieval, digital library systems (850 lines)
2. **[[filing-records-management-research]]** — Filing, records lifecycle, cross-referencing, activity-based computing (700 lines)
3. **[[augmentation-layer-research]]** — Industry context, CoALA, context engineering, competitive landscape
4. **[[work-context-container-options]]** — Detailed option analysis with library science principle mappings

---

## Next Steps

1. Decide on Option B scope — minimum viable activity entity
2. Prototype unified query — wire up all six sources in parallel
3. Test with real sessions — does activity-scoped retrieval improve quality?
4. Design co-access tracking — what data to capture and how to use it
5. Map to Metis C4 L3 — how does the Container appear in the Augmentation Layer?

---

**Version**: 1.0
**Created**: 2026-03-10
**Updated**: 2026-03-10
**Location**: knowledge-vault/10-Projects/Project-Metis/research/work-context-container-synthesis.md
