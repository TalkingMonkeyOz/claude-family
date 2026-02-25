---
tags:
  - project/Project-Metis
  - stocktake
  - scope-reframe
  - level/0
projects:
  - Project-Metis
created: 2026-02-23
synced: false
---

# Platform Stocktake — Scope Reframe & Consolidation

> Before going deeper into any area, take stock of everything produced, check it's generic enough for the new scope, identify gaps, and consolidate.

**Date:** 2026-02-23
**Trigger:** John clarified the three-layer scope: The System > nimbus deployment > Monash POC

---

## 1. The Three Layers (New Scope Definition)

| Layer | What It Is | Status |
|-------|-----------|--------|
| **1. The System** | A full system lifecycle platform for development houses. The product. | NOT YET DOCUMENTED as standalone |
| **2. nimbus / time2work** | First external customer deployment of The System | Extensively documented (Docs 1-6) |
| **3. Monash POC** | First engagement within the nimbus deployment, proving The System works | Documented (Doc 2) |

**Key insight:** The System is what we're designing and building. The POC for building it is the Claude Family itself — we build it with itself, it maintains itself, then it gets deployed to customers like nimbus.

**What this means:** All system requirements need to be captured generically. nimbus/Monash become "customer configuration" on top of the generic platform.

---

## 2. Complete Document Inventory

### 2.1 Project Documents (Claude.ai Project — 7 files)

| Doc | Title | Layer | Generic? | Needs Update? |
|-----|-------|-------|----------|---------------|
| Doc 1 | Strategic Vision & Plan | nimbus-specific | ❌ Written entirely for nimbus management pitch | YES — needs "The System" framing added |
| Doc 2 | Monash POC Proposal | Monash-specific | ❌ Client engagement doc | NO — correct as a customer doc |
| Doc 3 | Revenue Model & Commercial | nimbus-specific | ❌ nimbus commercial terms | NO — correct as a customer doc |
| Doc 4 | Build Brainstorm & Platform Planning | Mixed | ◐ Architecture is generic, examples nimbus-specific | YES — extract generic system requirements |
| Doc 5 | Knowledge Engine Architecture | Mixed | ◐ RAG architecture generic, nimbus examples throughout | YES — separate generic engine from nimbus knowledge |
| Doc 6 | Constrained Deployment Architecture | Mostly generic | ✅ Pattern is generic, only examples are nimbus | MINOR — relabel as system pattern, nimbus as example |
| — | Master Tracker | Coordination | ◐ Tracks both system and nimbus items mixed together | YES — separate system decisions from nimbus decisions |

### 2.2 Vault Files (10-Projects/Project-Metis/)

| File | Area | Layer | Generic? |
|------|------|-------|----------|
| README.md (Level 0) | Overview | Mixed | ◐ Architecture diagram is generic, framing is nimbus |
| knowledge-engine/README.md | Area 1 | Mixed | ◐ Engine concept generic, all examples are time2work |
| integration-hub/README.md | Area 2 | nimbus-specific | ❌ All connectors are nimbus tools (Jira, Salesforce, time2work) |
| ps-accelerator/README.md | Area 3 | nimbus-specific | ❌ Monash POC, time2work config, Award rules |
| quality-compliance/README.md | Area 4 | Mixed | ◐ Testing engine concept generic, Award/Playwright detail nimbus |
| support-defect-intel/README.md | Area 5 | nimbus-specific | ❌ nimbus support workflow, Jira instances |
| project-governance/README.md | Area 6 | Mixed | ◐ Dashboard concept generic, Salesforce/Jira detail nimbus |
| orchestration-infra/README.md | Area 7 | Mostly generic | ✅ Agent orchestration, sessions, DB, auth are platform-level |
| commercial/README.md | Area 8 | nimbus-specific | ❌ nimbus commercial terms |
| bpmn-sop-enforcement/README.md | Area 9 | Generic | ✅ Five-layer validation stack is entirely platform-level |
| orchestration-infra/day-1-readiness.md | Sub-topic | nimbus-specific | ❌ References nimbus Day 1 users |
| orchestration-infra/user-experience.md | Sub-topic | Mixed | ◐ BHAG concept generic, nimbus PS team specific |
| orchestration-infra/azure-infrastructure-recommendation.md | Sub-topic | nimbus-specific | ❌ nimbus Azure environment |
| orchestration-infra/claude-data-privacy-reference.md | Sub-topic | Generic | ✅ Claude API privacy is platform-level |
| orchestration-infra/dev-decisions-agents-workflow-handoff.md | Sub-topic | Generic | ✅ Agent Teams, workflow, handoff are platform-level |
| orchestration-infra/infra-decisions-api-git-auth.md | Sub-topic | Mixed | ◐ API keys generic, Azure DevOps nimbus-specific |
| orchestration-infra/autonomous-operations.md | Sub-topic | Generic | ✅ Agent autonomy concepts are platform-level |
| decisions/README.md | Decisions | Mixed | ◐ Mix of system and nimbus decisions |
| session-handoffs/2026-02-23-design-systems.md | Session | Meta | N/A — session record |
| bpmn-sop-enforcement/session-2026-02-23-design-validation.md | Session | Meta | N/A — session record |

---

## 3. What IS Already Generic (system-level requirements)

These capabilities are already described and apply to ANY development house deploying The System, not just nimbus:

### 3.1 Core Architecture
- ✅ Three-layer architecture: Knowledge Store (PostgreSQL+pgvector), Retrieval System (Voyage AI embeddings), Intelligence Layer (Claude API)
- ✅ Constrained deployment pattern: system prompt + cached knowledge (200K) + input classifier (Haiku) + tool restriction
- ✅ Five-layer validation stack: DDD → BPMN → DMN → Ontology → Event Sourcing
- ✅ Modular, provider-agnostic design (swap LLM, swap embeddings, swap vector DB)

### 3.2 Platform Capabilities (generic)
- ✅ Knowledge ingestion pipelines (API specs, product docs, procedures, support resolutions)
- ✅ Eight knowledge types with tiered validation (Tier 1-4: auto → human → confidence-flagged → AI-generated)
- ✅ Semantic search (vector + keyword hybrid)
- ✅ Agent orchestration (task queues, shared state, session management, crash recovery)
- ✅ Human-in-the-loop checkpoints at critical decision points
- ✅ Audit trail / event sourcing for all actions
- ✅ Multi-user auth with RBAC (simple now, SSO/OIDC later)
- ✅ Client data isolation
- ✅ Living documentation generated from system state
- ✅ Integration connector pattern (retry, rate limit, circuit breaker, abstraction)
- ✅ API contract: /ask, /search, /ingest, /validate, /clients/{id}/knowledge, /health

### 3.3 Development Approach (generic)
- ✅ AI-assisted development: Claude does the building, humans guide
- ✅ No-code for the human operator
- ✅ Git-based version control
- ✅ CLAUDE.md as persistent context for Claude Code
- ✅ Vault as merge layer between planning and building
- ✅ Phase 0 → 1 → 2 → 3 build sequence

### 3.4 Conventions & Standards (generic)
- ✅ Naming conventions (DB, API, files, agents)
- ✅ Code standards (TypeScript primary, Python for data/ML)
- ✅ Data standards (ISO 8601, UUIDs, UTF-8, soft delete)
- ✅ Agent conventions (identify self, check state, update state, flag uncertainty)

---

## 4. What Is Inherently Customer-Specific (nimbus layer)

These should be separated out as "nimbus deployment configuration," not system requirements:

- time2work API integration specifics (REST endpoints, OData, Swagger specs)
- Australian Award / Enterprise Agreement rules and compliance
- Monash University engagement scope, timeline, success criteria
- nimbus tool stack (Jira instances, Salesforce, Confluence, Granola, Slack)
- Playwright discovery of time2work screens
- Revenue model, pricing, commercial structure (nimbus deal)
- Management pitch and talking points
- Deputy competitive analysis
- Azure Australia East hosting requirement

---

## 5. Gaps in Generic System Requirements

Things The System needs that aren't yet captured generically:

| Gap | Current State | What's Needed |
|-----|--------------|---------------|
| **System-level product description** | Only nimbus-framed docs exist | A standalone "what is The System" document — product vision for dev houses |
| **Generic customer onboarding model** | Only Monash POC exists | How does ANY customer deploy The System? What's the generic pipeline? |
| **Customer configuration framework** | nimbus-specific knowledge hardcoded | How does a customer define their product, APIs, domain knowledge, tools? |
| **Multi-tenant architecture** | Client isolation mentioned but designed for nimbus clients | System-level multi-tenancy: multiple organisations, each with their own clients |
| **Self-hosting / deployment model** | All hosted on nimbus Azure | How does a customer organisation host their instance? SaaS vs self-hosted? |
| **Pricing model for The System** | Only nimbus rev share exists | What does a dev house pay for The System? Subscription? Per-seat? |
| **Domain-agnostic knowledge types** | 8 types defined but some are Award-specific | Generalise: "compliance rules" not "Award rules", "product API" not "time2work API" |
| **Generic integration catalogue** | All connectors nimbus-specific | What's the standard set of integrations? (PM tools, CRM, docs, comms, product APIs) |
| **Self-maintaining capability** | Referenced but not designed | How does The System manage its own lifecycle? The dog-fooding loop. |
| **Feature lifecycle management** | Flagged as partial in Master Tracker | idea → design → code → test → deploy → maintain — not yet designed |
| **Project dashboard / status view** | Flagged as partial | At-a-glance view of where the platform build is at |

---

## 6. What's Well-Covered vs Thin

| Area | Depth | Assessment |
|------|-------|-----------|
| Knowledge Engine (Area 1) | DEEP | Architecture, taxonomy, build phases, risk analysis all solid. Needs generic relabelling. |
| Integration Hub (Area 2) | MODERATE | Connector pattern generic. Specific connectors all nimbus. Needs generic catalogue. |
| PS Accelerator (Area 3) | DEEP | Pipeline well-designed. Heavily nimbus/Monash. Needs "generic implementation accelerator" framing. |
| Quality & Compliance (Area 4) | MODERATE | Concepts solid. Playwright and Award specifics are nimbus. Needs generic testing framework. |
| Support & Defect Intel (Area 5) | MODERATE | Triage and pattern detection generic. Jira-specific detail is nimbus. |
| Project Governance (Area 6) | THIN | Mostly a wish list. Needs real design work. |
| Orchestration & Infra (Area 7) | DEEP | Agent teams, sessions, auth, conventions all well-covered and mostly generic already. |
| Commercial (Area 8) | MODERATE for nimbus | Missing: commercial model for The System itself. |
| BPMN/Validation (Area 9) | MODERATE | Five-layer stack well-defined. Open questions not yet addressed. Already generic. |

---

## 7. Recommended Approach

### Step 1: Create "The System" product definition (NEW)
A single document that describes what The System is, who it's for (development houses), what it does generically, and how it differs from alternatives. This is the missing anchor document.

### Step 2: Extract generic requirements from existing docs
Go through Docs 4, 5, 6 and vault READMEs. Pull out generic platform requirements into a consolidated system requirements document. Leave nimbus-specific content where it is — it becomes the reference implementation.

### Step 3: Relabel the vault structure
Add a clear distinction in the vault between:
- `system/` — generic platform requirements and architecture
- `customers/nimbus/` — nimbus-specific deployment docs
- `customers/nimbus/monash/` — Monash engagement docs

OR (simpler): add a `layer: system | customer | engagement` tag to every vault file's frontmatter.

### Step 4: Continue area deep-dives with generic framing
When doing focused sessions on each area, frame them as "what does The System need" first, then "how does nimbus configure it" second.

---

## 8. Planning Approach — Research Findings

### Claude Desktop vs Claude Code for This Phase

**Claude Desktop (what we're using now) is better for:**
- Brainstorming, architecture, strategy
- Document creation and iteration
- Conversational decision-making
- Multi-document cross-referencing
- Writing specs that Claude Code will build from

**Claude Code would be better for:**
- Reading and analysing actual codebases
- Plan Mode (Opus for planning, Sonnet for execution)
- Building the actual system
- Context priming across large file sets

**Recommendation:** Stay in Claude Desktop for the stocktake, system definition, and area deep-dives. Move to Claude Code when we have specs to build from.

### Context Management Best Practices (from research)

Industry consensus for large-scale planning with AI:

1. **Separate storage from presentation** — keep the vault as persistent truth, use the conversation as working memory
2. **One topic per session** — our "focused chat per area" approach is correct
3. **CLAUDE.md as anchor** — when we move to Claude Code, this file is the persistent context
4. **Session summaries** — write them at the end of every session (we're already doing this)
5. **Treat prompts as code** — version control system prompts, conventions, and knowledge payloads
6. **Context compaction** — accept that long sessions lose detail; design for it with checkpoint docs

**Our current approach (vault as merge layer + focused chats + session handoffs) aligns with industry best practice.** The main improvement would be ensuring every session produces a vault update, not just some.

---

## 9. Immediate Actions

1. [ ] **John reviews this stocktake** — does the three-layer framing feel right? Any gaps I missed?
2. [ ] **Create "The System" product definition** — standalone document, generic, aimed at dev houses
3. [ ] **Add `layer` tags to vault frontmatter** — system vs customer vs engagement
4. [ ] **Decide vault restructure** — subfolder approach vs tagging approach
5. [ ] **Continue focused sessions** — but frame them "system first, nimbus second"

---
*Created: 2026-02-23 | Session: Stocktake & Scope Reframe*
