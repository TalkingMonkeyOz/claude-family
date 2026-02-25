---
tags:
  - project/Project-Metis
  - area/project-governance
  - scope/system
  - level/2
  - type/brainstorm
projects:
  - Project-Metis
created: 2026-02-24
updated: 2026-02-24
synced: false
---

# Project Management & Feature Lifecycle — Brainstorm

> **Scope:** system (generic platform capability — every deployment needs work tracking, lifecycle management, and project visibility)
>
> **Design Principles:**
> - Platform owns its own work tracking — no external dependency for core operations
> - Integrate with customer's existing PM/git tools through connectors, don't replace them
> - BPMN enforcement at lifecycle gates — mechanical, not agent willpower
> - Work items live in database for agent-fast queries; artifacts live in git for version control

**Source:** Chat #9 (Feb 24, 2026) — brainstorm IN PROGRESS
**Parent:** [[project-governance/README|Project Governance]]

---

## 1. Lifecycle Model — NOT Two Separate Lifecycles

A spectrum of work types hitting different lifecycle stages depending on what they are. Some work exits after a KMS answer. Some goes all the way through to code deployment.

### Three Rigidity Tiers

| Tier | Name | What Goes Here | Gates | Example |
|------|------|---------------|-------|---------|
| **Tier 1** | Free-flowing | Knowledge queries, consultant questions, internal lookups | None beyond "is answer good" | "What rule types support shift allowances?" |
| **Tier 2** | Structured with sign-off | Customer deliverables, requirements analysis, sign-off docs | Client approval IS the gate. Sign-off doc is what you invoice against. | Requirements document, configuration specification |
| **Tier 3** | Rigid pipeline | Code and deployment | Five-layer validation stack applies. No skipping tests or deploying without review. | New API endpoint, Award rule configuration change |

**Key decisions:**
- Tier 2 **escalates to Tier 3** if signed-off work requires code changes (e.g., custom feature needs new API endpoint)
- **Commercial call** determines paid vs included work. Platform doesn't make that call but needs to know outcome — affects lifecycle routing and traceability
- Platform should be **source of truth for documentation**, generate/maintain docs from system state (living documentation), optionally push to Confluence as integration

## 2. Work Breakdown Hierarchy

Three levels in database:

| Level | Name | What It Is |
|-------|------|-----------|
| **Top** | Initiative | High-level goal or project chunk |
| **Middle** | Feature | Deliverable chunk within an initiative |
| **Bottom** | Task | Actual work item an agent picks up |

- Each level has status tracking
- Parent status rolls up from children
- Lives in database, not chat context
- **Tasks must be detailed** — agents forget context and build the wrong thing otherwise

## 3. Custom-Built Project Management

**Decision: Build our own.** NOT GitHub Projects, NOT Azure Boards, NOT Jira.

**Rationale:**
- Platform needs BPMN enforcement at lifecycle gates — no external tool does this
- Fast local DB queries for agents — no API latency to external service
- No dependency on external service availability
- Full control over data model
- Can integrate with customer's existing tools as connectors through Integration Hub

The platform integrates with whatever the customer already uses (Azure DevOps, GitHub, GitLab, Jira) — it doesn't force them to switch.

## 4. Git Integration — Hybrid Approach

| What | Where | Why |
|------|-------|-----|
| Work tracking metadata (status, assignment, priority, dependencies) | Database | Agent-fast queries, BPMN enforcement |
| Artifacts (specs, design docs, ADRs, code) | Git | Version control, diff history, collaboration |

Work item in DB points to git path for spec file. Bidirectional linking.

### Git Provider — Agnostic

Platform integrates with whatever customer uses:
- Azure DevOps (nimbus already uses this)
- GitHub
- GitLab
- Self-hosted (Gitea/Forgejo could be embedded as default for standalone deployments)

**Pricing research completed:**
- Azure DevOps: 5 free users, $6/user after
- GitHub Team: $4/user/month
- GitHub Enterprise: $21/user/month
- Gitea: Free self-hosted, ~200-300MB RAM, MIT licence
- Forgejo: Gitea fork, community-governed, same footprint
- GitLab CE: Free self-hosted but 8-16GB RAM (heavy)

## 5. Work Types

Eight default work types. List is **configurable/expandable** per deployment — not hardcoded. Each type has a default tier mapping but can be overridden.

| Work Type | Description | Default Tier | Exits At |
|-----------|-------------|-------------|----------|
| **Knowledge query** | Someone asks a question, KMS answers | Tier 1 | Answer delivered |
| **Bug / defect** | Something's broken | Tier 2 or 3 (depends if code fix needed) | Fix verified |
| **Feature request** | New capability | Tier 3 | Deployed + tested |
| **Configuration change** | Customer config adjustment | Tier 2 (escalates to 3 if code needed) | Validated + signed off |
| **Documentation** | Create or update docs | Tier 1 or 2 (depends if client-facing) | Published |
| **Client onboarding** | New customer setup | Tier 2 (composite — spawns child work) | Handover complete |
| **Knowledge ingestion** | Feed new knowledge into the engine | Tier 1 or 2 (depends on knowledge tier) | Validated + searchable |
| **Investigation** | Research or spike — answer unknown | Tier 1 | Findings documented |

## 6. Decisions-as-Objects

Every significant decision is a **first-class object** in the database.

**Two use cases:**
- **Operational:** Day-to-day "why did we do this?" — linked to work items, features, clients. Decays over time as decisions get superseded.
- **Compliance/Legal:** Audit trail for regulated work. If someone sues over a payroll miscalculation from an Award config, you need the chain: who requested → what AI recommended → who approved → what was tested.

**Decision record fields:** what (title + description), who (made by human/agent, approved by), why (rationale, options considered), when, scope (linked work item/feature/client), status (proposed → approved → superseded), source (chat/meeting/ticket/AI recommendation), confidence (if AI-proposed).

**Configurable retention/decay:**

| Age | What Happens | Compliance-flagged? |
|-----|-------------|-------------------|
| Short-term (configurable) | Full detail, full conversations | Retained as-is |
| Medium-term (configurable) | Conversations summarised, decisions retained | Retained as-is |
| Long-term (configurable) | Superseded decisions archived, summaries only | **Still retained as-is** |

All retention periods configurable per deployment. Compliance-flagged decisions and their source chain retained indefinitely.

## 7. Dashboard & Interface

**Dashboard content:**
- Decisions pending / needs attention — **essential**. Including actionable notifications (e.g., "Sharon, John sent a document for review and approval")
- Work items status — where things are at, what's left
- Recent activity — **not needed** (noise)

**Interface model: Chat + Dashboard**
- **Chat is a major interface** — conversational interaction backed by system DB and enforcement. User says "I need this bug fixed" → system captures it, routes it through the correct process, hits the right BPMN gates.
- **Dashboard provides visual at-a-glance** — complement to chat, not replacement.
- Chat interface IS the constrained deployment pattern: Claude API underneath, system prompt + tools + BPMN gates enforce the process.

**Advanced vision (Year 2+):** Morning briefing app, pre-programmed action buttons ("tell me where we're at with this"), voice interface, proactive notifications.

## 8. CCPM — Parked

Critical Chain Project Management parked — it's a human concern, not directly applicable to AI agents. Sandbagging is a human behaviour, agents don't do it.

**What IS relevant:** Token consumption estimation and tracking per task. Agents are bad at estimating complexity, especially on complex GUI work (multi-pass failures). Need actual-vs-estimated tracking at task level for cost management.

Cost offset argument: productivity increase + fewer complaints + increased sales justifies token spend. Track and prove ROI.

## 9. Cross-Area Integration

**Every area is both a producer and consumer of work items.** Project governance owns the tracking and lifecycle (the registry), not the work itself.

| Area | Produces | Consumes |
|------|----------|----------|
| Knowledge Engine | Knowledge gaps → ingestion work items | Knowledge queries from any area |
| Support & Defect Intel | Tickets → bug/investigation work items | Resolution knowledge from KMS |
| Quality & Compliance | Test failures → defect work items | Test scenarios from delivery |
| Delivery Accelerator | Client onboarding → composite initiatives | Configs from KMS, validated by Quality |
| Integration Hub | Connection failures → investigation items | Config from work items |
| BPMN/SOP | Gate rejections → "fix before proceeding" items | Work item status for gate checks |
| Project Governance | Tracking, lifecycle, audit trail | Work items from all areas |

**Concrete example:** Sharon at Monash requests a new weekend casual allowance → KMS searches (partial match) → Governance creates Tier 2 work item → Delivery breaks into tasks → Quality generates pay scenarios → Integration Hub talks to time2work API → BPMN gates enforce sign-off before production → KMS learns the pattern for next time. One request, all areas, one audit trail.

---
*Source: Chat #9 sessions (Feb 24, 2026) | Session handoff: [[session-handoffs/2026-02-24-project-mgmt-lifecycle.md]]*
