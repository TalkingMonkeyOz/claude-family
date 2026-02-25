---
tags:
  - project/Project-Metis
  - scope/system
  - level/0
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-02-24
revised: 2026-02-24
synced: false
---

# AI Development Lifecycle Platform — Level 0 Map

## Scope: Three Layers

This project has three distinct layers. The System is what we're building. nimbus and Monash are customers of it.

| Layer | What It Is | Documentation |
|-------|-----------|--------------|
| **1. The System** | Full lifecycle AI development platform for development houses | [[system-product-definition\|Product Definition]] (this vault) |
| **2. nimbus / time2work** | First external customer deployment | Docs 1, 3, 4, 5, 6 (Claude.ai project) |
| **3. Monash POC** | First client engagement within nimbus deployment | Doc 2 (Claude.ai project) |

**The System** is the product. Claude Family building itself is the POC (dog-fooding). nimbus is customer #1. Monash is the first engagement within nimbus.

> See [[system-product-definition]] for the full generic product definition.
> See [[stocktake-2026-02-23]] for the scope reframe analysis and document inventory.

## What The System Does

An AI platform that sits alongside a development house's existing product and toolstack. It ingests everything the organisation knows — product APIs, configuration options, implementation patterns, support resolutions, compliance rules — and makes that knowledge available to every person and process.

It handles design, configuration, documentation, testing, and deployment — with humans guiding at validation checkpoints. The knowledge compounds with every engagement.

## Status

- **Phase:** DESIGN COMPLETE — ready for build
- **All 9 areas:** BRAINSTORM-COMPLETE as of Feb 24, 2026
- **Gap review:** COMPLETE as of Feb 26 — 10 resolved, 9 deferred (clear targets), 1 parked (Claude Code building)
- **Decisions:** 70+ identified, all resolved or explicitly deferred. 7 needing management.
- **Feature catalogue:** 10 features defined with nimbus/Monash examples (Feb 26)
- **Plan of attack:** Phase 0-3 defined. MVP at ~3 months. Full platform ~4-5 months. (Feb 26)
- **Project code:** METIS (in project-tools DB). Vault folder: `Project-Metis/`
- **Key docs:** Product Definition, Feature Catalogue, Plan of Attack, Gap Resolution Summary (vault), Docs 1-6 (Claude.ai project)
- **Developer:** John de Vere (human) + Claude Family (AI)
- **Next step:** Management decisions (Monash go-ahead, Azure, API access), then Phase 0 build

## Level 0 Architecture

```
                    ┌─────────────────────┐
                    │   Project           │
                    │   Governance        │
                    │   (Area 6)          │
                    └────────┬────────────┘
                             │
┌──────────────┐    ┌────────┴────────────┐    ┌──────────────────┐
│  Knowledge   │    │                     │    │  Support &       │
│  Engine      ├────┤   ORCHESTRATION     ├────┤  Defect Intel    │
│  (Area 1)    │    │   & INFRASTRUCTURE  │    │  (Area 5)        │
└──────────────┘    │   (Centre)          │    └──────────────────┘
                    │                     │
┌──────────────┐    │   Agent coord,      │    ┌──────────────────┐
│  Integration ├────┤   shared state,     ├────┤  Quality &       │
│  Hub         │    │   sessions, DB,     │    │  Compliance      │
│  (Area 2)    │    │   auth, envs        │    │  (Area 4)        │
└──────────────┘    └────────┬────────────┘    └──────────────────┘
                             │
                    ┌────────┴────────────┐
                    │   Delivery          │
                    │   Accelerator       │
                    │   (Area 3)          │
                    └─────────────────────┘
```

## Areas (Level 1 Branches)

Each area is a platform capability. Described generically (system-level), then configured per customer.

| Area | Folder | What It Does | Priority | Status |
|------|--------|-------------|----------|--------|
| Area 1 | [[knowledge-engine/README\|Knowledge Engine]] | Ingests, stores, retrieves all domain knowledge | CRITICAL — Phase 1 | ✓ BRAINSTORM-COMPLETE |
| Area 2 | [[integration-hub/README\|Integration Hub]] | Standardised connectors to product APIs and external tools | CRITICAL — Phase 1 | ✓ BRAINSTORM-COMPLETE |
| Area 3 | [[ps-accelerator/README\|Delivery Accelerator]] | Requirements → config → test → release → living docs pipeline | HIGH — Phase 2 | ✓ BRAINSTORM-COMPLETE |
| Area 4 | [[quality-compliance/README\|Quality & Compliance]] | Automated testing, scenario generation, outcome validation, regression | MEDIUM — Phase 2-3 | ✓ BRAINSTORM-COMPLETE |
| Area 5 | [[support-defect-intel/README\|Support & Defect Intelligence]] | AI triage, duplicate detection, pattern recognition, defect lifecycle | MEDIUM — Phase 3 | ✓ BRAINSTORM-COMPLETE |
| Area 6 | [[project-governance/README\|Project Governance]] | Dashboards, status reports, health scoring, feature lifecycle | LOW dash / HIGH PM — Phase 3+ | ✓ BRAINSTORM-COMPLETE |
| Area 7 | [[orchestration-infra/README\|Orchestration & Infrastructure]] | Agent coordination, sessions, DB, auth, environments, CI/CD | CRITICAL — Phase 0-1 | ✓ BRAINSTORM-COMPLETE |
| Area 8 | [[commercial/README\|Commercial Model]] | Pricing, contracts, customer onboarding | PRE-BUILD | ✓ BRAINSTORM-COMPLETE |
| Area 9 | [[bpmn-sop-enforcement/README\|Design Validation & Enforcement]] | Five-layer validation stack: DDD → BPMN → DMN → Ontology → Event Sourcing | HIGH — Cross-cutting | ✓ BRAINSTORM-COMPLETE |

## Key Architecture Decisions (System-Level)

| Decision | Outcome | Status |
|----------|---------|--------|
| Embedding model | Voyage AI (best-in-class, already working) | ✓ DECIDED |
| RAG framework | Custom (already working). LlamaIndex as upgrade path. | ✓ DECIDED |
| Data store | PostgreSQL + pgvector. Hybrid: DB for structured, vault for docs. | ✓ DECIDED |
| Constrained deployment | Four-layer architecture: system prompt + cached knowledge + classifier + tool restriction | ✓ DECIDED |
| Validation approach | Five-layer stack: DDD → BPMN → DMN → Ontology → Event Sourcing | ✓ DECIDED |
| Knowledge validation | Tiered: Tier 1 auto → Tier 2 human → Tier 3 confidence-flagged → Tier 4 never auto-trust | ✓ DECIDED |
| Auth model | JWT + swappable middleware. Simple RBAC now, SSO/OIDC later. | ✓ DECIDED |
| Infrastructure platform | Linux primary. Infrastructure-agnostic at system level. | ✓ DECIDED (review pending) |
| LLM provider | Claude API (provider-agnostic architecture, can swap) | ✓ DECIDED |

## Build Phases (High Level)

| Phase | Focus | Notes |
|-------|-------|-------|
| Phase 0 | Project setup, git, database, agent teams, conventions | System-level |
| Phase 1 | Knowledge Engine + Integration Layer | System-level |
| Phase 2 | First customer deployment (nimbus) + first engagement (Monash) | Customer-level |
| Phase 3 | Platform hardening, multi-tenant, security | System-level |
| Future | Scale to additional customers | System + customer |

## Source Documents

### System-Level (Vault)
- **[[system-product-definition\|Product Definition]]** — What The System is, who it's for, core architecture, capabilities
- **[[stocktake-2026-02-23\|Stocktake]]** — Document inventory, generics analysis, gaps, recommended approach
- **Area READMEs** — Detailed brainstorm per capability area

### Customer-Level: nimbus (Claude.ai Project)
- **Doc 1 — Strategic Vision:** Why nimbus needs AI, market context, competitive analysis
- **Doc 2 — Monash POC:** First engagement scope, 8-10 week timeline, success criteria
- **Doc 3 — Revenue Model:** Subscription pricing, build costs, scale projections
- **Doc 4 — Platform Brainstorm:** Detailed workstreams, schema, agent design, conventions
- **Doc 5 — Knowledge Engine Architecture:** RAG system, existing assets, build approach
- **Doc 6 — Constrained Deployment:** Four-layer constraint architecture, deployment scenarios
- **Master Tracker** — Consolidated status of all decisions and next steps

## Focused Chat Plan

Each area gets its own focused chat to manage context. The vault is the merge layer.

| # | Chat Topic | Area(s) | Status | Date |
|---|-----------|---------|--------|------|
| — | Stocktake & Scope Reframe | All | ✓ COMPLETE | Feb 23 |
| 1 | BPMN / SOP & Enforcement | Area 9 | ✓ COMPLETE | Feb 23 |
| 2 | Knowledge Engine Deep Dive | Area 1 | ✓ COMPLETE | Feb 23 |
| 3 | Constrained Deployment Implementation | Area 1+7 | ⊗ SUPERSEDED — covered sufficiently in Doc 6 + Area 7 sub-files | |
| 4 | Integration Hub Connectors | Area 2 | ⊗ SUPERSEDED — covered in Area 2-5 sweep. "Plumbing, not a design problem." | |
| 5 | Delivery Accelerator + First Customer Technical | Area 3 | ⊗ SUPERSEDED — covered in Area 2-5 sweep (5 decisions resolved) | |
| 6 | Quality & Compliance Design | Area 4 | ⊗ SUPERSEDED — covered in Area 2-5 sweep (8 decisions resolved) | |
| 7 | Commercial & Management Prep | Area 8 | ⊗ SUPERSEDED — business model, not build dependency. Revisit when meeting scheduled. | |
| 8 | Orchestration Build Specs | Area 7 | ✓ COMPLETE (revisited Feb 24 — 4 brainstorm files added) | Feb 23, 24 |
| 8a | Session Memory & Context Persistence | Area 7+1 | ⚠ PARTIAL — brainstorm file exists but UNVALIDATED by John. Setup doc ready for redo. | Feb 24 |
| 8b | Context Assembly & Prompt Engineering | Area 1+7 | ○ NOT STARTED — setup doc ready | |
| 9 | Project Mgmt & Feature Lifecycle | Area 6+7 | ✓ COMPLETE | Feb 24 |
| — | Area 2-5 Sweep | Areas 2,3,4,5 | ✓ COMPLETE (all at first pass) | Feb 24 |
| 10 | Consolidation & Cross-Area Alignment | All | ◐ IN PROGRESS — all 9 areas confirmed brainstorm-complete, vault cleanup underway | Feb 24 |
| 11 | BPMN Validation (Claude Code Console) | All | ○ NOT STARTED — needs consolidation + second-pass review first | |

## How To Use This

1. Start here at Level 0 to understand the big picture
2. Read [[system-product-definition]] for the generic platform description
3. Click into an area to see brainstorm content for that capability
4. Every file has a `scope` tag: `system` (generic) or `customer` (nimbus-specific) or `engagement` (Monash-specific)
5. Any Claude Family member can read this and get oriented

---
*Created: 2026-02-19 | Updated: 2026-02-24 — Scope reframe (Feb 23), numbering + header conventions (Feb 24), vault cleanup: status column added, chat plan corrected, METIS project code noted (Feb 24)*
