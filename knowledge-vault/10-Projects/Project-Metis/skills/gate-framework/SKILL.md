---
name: gate-framework
description: "Formalise any design project through structured gate-based quality checkpoints. Use this skill whenever starting a new design project, resuming design work that spans multiple sessions, when the user says 'gate review', 'are we ready for the next gate', 'what gate are we at', 'check gate readiness', or references gates, deliverables, or design checkpoints. Also trigger when taking a loose collection of design conversations and formalising them into structured deliverables, when the user wants to assess design maturity or completeness, or when progressing a long design effort across multiple chat sessions. This skill works with project-session-manager for multi-session continuity — gate-framework defines WHAT you're working toward, session-manager defines HOW you persist progress across sessions."
---

# Gate Framework — Design Quality Checkpoints

## Why This Skill Exists

Design projects done through AI chat tend to accumulate decisions, ideas, and half-formed designs across many sessions without structure. Nobody tracks what's been decided vs what's still open. Nobody checks whether the design is complete enough to build from. Work starts before the problem is understood.

This skill provides a universal gate framework — five quality checkpoints that a design must pass through before it's ready to build and release. Each gate has defined deliverables. Progress is measurable.

**Core principle:** Gates exist to catch what humans skip through experience and AI skips through lack of judgment. Humans may skip a gate with documented justification. AI agents cannot skip gates — they need the structure because they lack the judgment to know when shortcuts are safe.

## Companion Skill

**This skill pairs with `project-session-manager`.** Gate-framework defines the *design methodology* — what you're working toward, what deliverables exist, how to assess readiness. Session-manager defines *session discipline* — how to start/end sessions, store decisions incrementally, checkpoint progress, and hand off between chats.

Use both together on any design project spanning multiple sessions:
- Gate-framework tells you *what gate you're at* and *what deliverables remain*
- Session-manager tells you *how to persist progress* so nothing is lost between chats

If you're using gate-framework without session-manager, you'll lose track of progress across sessions. If you're using session-manager without gate-framework, you'll have continuity but no design structure.

## The Five Gates

### Gate Zero — "Do we understand the problem?"

Must exist before any design, BPMN, DB design, or coding starts. This gate prevents the most common failure: building before understanding.

| # | Deliverable | What it answers |
|---|---|---|
| 1 | Problem Statement (incl. Scope) | What is the question? What is NOT in scope? |
| 2 | Assumptions & Constraints | Real hard limits — NOT technology choices |
| 3 | Stakeholders & Decision Rights | Who decides what? Escalation paths |
| 4 | System Map (C4 L1/L2) | What exists, what connects |
| 5 | Design Principles / Ethos | Rules before anyone builds |

**Gate Zero check:** Can you explain the problem to a new team member in 5 minutes without referencing the solution?

### Gate 1 — "Do we understand the domain?"

Must exist before starting detailed design (process modelling, domain modelling, data modelling).

| # | Deliverable | What it answers |
|---|---|---|
| 1 | Process Inventory | All major workflows — identification, not detail |
| 2 | Actor Map | Who/what interacts: humans, agents, external systems |
| 3 | Data Entity Map | Key data objects — inventory, not full model |
| 4 | Business Rules Inventory | Domain rules governing behaviour |
| 5 | Integration Points | External systems and patterns (inbound + outbound) |

**Gate 1 check:** Can you list every process, actor, and data entity without discovering new ones?

### Gate 2 — "Have we designed the solution?"

Must exist before anyone builds databases or writes production code. This is where the bulk of design thinking happens.

| # | Deliverable | What it answers |
|---|---|---|
| 1 | Detailed Process Models (BPMN) | Step-by-step process designs |
| 2 | C4 Level 3 Component Diagrams | Internal architecture of each container |
| 3 | Domain Model (DDD) | Bounded contexts, aggregates, ownership |
| 4 | Decision Models (DMN) | Formalised business rules — testable |
| 5 | Data Model | Tables, relationships, indexes |
| 6 | Tech Stack Decisions | Technology choices formally captured |
| 7 | API / Interface Design | Contracts, data flows |
| 8 | Security & Access Model | Auth, roles, access control |
| 9 | Test Strategy | Levels, coverage, agent vs human testing |
| 10 | User/Actor Journey Maps | How each actor type interacts |
| 11 | Deployment Architecture | Hosting, environments, topology |
| 12 | Monitoring & Observability Design | Logs, transcripts, error tracking, change impact |

**Gate 2 check:** Can a developer build from these documents without asking design questions?

### Gate 3 — "Are we ready to build?"

Practical readiness before production coding starts.

| # | Deliverable | What it answers |
|---|---|---|
| 1 | Development Standards / Coding Conventions | Naming, structure, style, commits |
| 2 | Environment Setup / Infrastructure | Dev, staging, production, CI/CD |
| 3 | Build Plan / Sprint Backlog | Prioritised build sequence |
| 4 | Definition of Done | What "finished" means per deliverable type |
| 5 | Agent Protocols / Constraints & Skills | How agents operate: context, escalation, autonomy |
| 6 | Documentation Standards | Format, RAG-readability requirements |
| 7 | Risk Register | Known risks and mitigations |
| 8 | Project Delivery Framework | Timelines, commercial, human iteration cycles |

**Gate 3 check:** Could a new developer (or agent) start building tomorrow with only these documents?

### Gate 4 — "Are we ready to release?"

Single checklist document covering: UAT results, documentation updated (incl. BPMN), PVT, client sign-off, support readiness, training materials, performance testing, rollback plan.

**Gate 4 check:** If this release causes problems, can we detect, diagnose, and roll back?

## Customising the Gate Framework

The five gates and their questions are universal. The specific deliverables are a default template drawn from software/AI platform development. Projects should adapt:

**To customise deliverables:**
1. Keep the five gate questions unchanged — they're universal quality checks
2. Add, remove, or rename deliverables within each gate to match your domain
3. Document customisations in your project's design lifecycle file
4. The gate readiness checks (the questions) still apply regardless of deliverable list

**What stays fixed:**
- Five gates, in order
- The principle that AI cannot skip gates
- The iterative methodology (below)
- The gate readiness questions

**What's flexible:**
- Specific deliverables per gate
- Level of formality per deliverable (a startup's "Problem Statement" might be 3 paragraphs; an enterprise's might be 10 pages)
- Whether Gate 4 is a checklist or a formal document set

## The Iterative Methodology

Design does not flow linearly through gates. The real process is iterative within and across gates:

```
Brainstorm 1 (capture ideas at high level)
    → Consolidate (reorganise, find gaps)
        → Brainstorm 2 (go deeper on gaps)
            → Consolidate (tighten)
                → Review with human (validate decisions)
                    → Gate deliverable complete
```

### Key Rules

**Consolidation before second-pass.** After a first brainstorm, consolidate what you have before going deeper. Consolidation reveals what actually needs deepening — don't iterate before you consolidate.

**Anti-monologue (HARD RULE).** In brainstorm/design sessions, present ONE topic at a time. Get the human's input. Capture the decision. Move to the next topic. Never dump a complete design and ask for feedback afterward. Unvalidated output is NOT decided output — it must be stepped through conversationally before it counts.

**Decisions are stored immediately.** When a decision is made, store it as a session fact right then (via project-session-manager's `store_session_fact`). Don't batch to end of session. Compaction will eat unstored decisions.

**Cross-gate iteration is normal.** Gate 2 work may reveal gaps in Gate 1 understanding. Gate 3 readiness checks may expose missing Gate 2 deliverables. Going backward is expected and healthy — the gates just tell you *where* the gap is.

### Multi-Session Progression

Long design projects span many chat sessions. Each session should:

1. **Start:** Load gate progress (which gate, which deliverables done/outstanding)
2. **Focus:** Work on deliverables within one gate per session where possible
3. **Track:** Store every decision as a session fact immediately when made
4. **Checkpoint:** Save progress after completing each deliverable or section
5. **Handoff:** Write a session handoff noting gate progress and next deliverables

For full multi-session discipline, use the **project-session-manager** skill alongside this one. It defines the session lifecycle (orient → work → close) that ensures continuity.

## Assessing Gate Readiness

To check whether a gate is ready to pass:

### Step 1: List deliverables for the gate
Review the deliverable table. For each, assess status:
- ✅ **Complete** — written, validated with human, stored in vault/system
- ◐ **Partial** — started but incomplete, or exists scattered across sessions
- ○ **Not started** — no deliverable exists

### Step 2: Apply the gate question
Ask the gate's readiness question honestly. If the answer is "mostly" or "with caveats," the gate isn't passed.

### Step 3: Identify blockers
For each incomplete deliverable, note:
- What's missing
- What's blocking it (dependency on another deliverable? Needs human input? Needs research?)
- Suggested next action

### Step 4: Report to human
Present the assessment. The human decides whether to:
- Complete the remaining deliverables
- Skip the gate with documented justification (humans only — agents cannot skip)
- Defer specific deliverables with noted risk

**Never auto-pass a gate.** Gate passage is always a human decision, presented with evidence.

## The Dual-Lens Principle

For platform projects (systems that will enforce process on others), the gate framework applies twice:

1. **Building the platform** — the platform itself must pass through all gates
2. **What the platform enforces** — the platform should enforce gate-like quality checks on its users' work

This means the platform team must eat their own cooking. You can't enforce Gate Zero on clients if you haven't written your own Problem Statement.

## Progress Tracking

Each project using this framework should maintain a progress tracker showing status per gate per deliverable. The recommended format:

```markdown
## Gate Zero — STATUS

| # | Deliverable | Status | Notes |
|---|---|---|---|
| 1 | Problem Statement | ◐ Scattered | Discussed, never consolidated |
| 2 | Assumptions & Constraints | ○ Not started | |
| 3 | Stakeholders & Decision Rights | ○ Not started | |
| 4 | System Map | ◐ Partial | Areas listed, no C4 diagram |
| 5 | Design Principles / Ethos | ✅ Done | ethos.md |
```

Track this in the project's design lifecycle document (alongside the methodology, not separately).

## Quick Reference

| Gate | Question | Deliverables | Blocks |
|------|----------|-------------|--------|
| 0 | Do we understand the problem? | 5 | Any design work |
| 1 | Do we understand the domain? | 5 | Detailed design (BPMN, DDD, data model) |
| 2 | Have we designed the solution? | 12 | Building databases, writing production code |
| 3 | Are we ready to build? | 8 | Production development starts |
| 4 | Are we ready to release? | 1 checklist | Go-live |

**Total: 31 deliverables across 5 gates.**

---

*Companion skill: project-session-manager — for multi-session continuity discipline*
*Created from METIS project methodology, 2026-03-07*
