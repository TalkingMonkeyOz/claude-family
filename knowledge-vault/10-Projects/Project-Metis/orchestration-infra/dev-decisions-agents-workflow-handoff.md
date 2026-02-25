---
tags: [Project-Metis, development, decisions, agent-teams, workflow, claude-code]
project: Project-Metis
date: 2026-02-19
status: recommendation
---

# DEV Decisions: Agent Teams, Workflow, Carry-Forward, Handoff

Four decisions that shape how we build. Researched Feb 19, 2026.

---

## Decision 1: Agent Teams Timing

**Question:** Use Agent Teams from day one, or start single-agent?

### What Agent Teams Actually Is (Verified Feb 2026)

Agent Teams launched Feb 5, 2026 as an **experimental** feature with Opus 4.6. Key facts:

- **What it does:** Multiple Claude Code sessions work in parallel on a shared codebase. Lead agent coordinates, teammates work independently with their own context windows, and they can message each other directly.
- **How to enable:** Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json or env var
- **Status:** Experimental — "known limitations around session resumption, task coordination, and shutdown behavior" (Anthropic docs)
- **Cost impact:** Each teammate is a full context window. More agents = more tokens = more cost. Community reports $50-200 per significant feature build with 2-4 agents.
- **Best for:** Parallel exploration, multi-layer features (frontend/backend/tests), competing hypotheses debugging, code review
- **Not good for:** Sequential tasks, same-file edits, work with many dependencies

### Honest Assessment

Agent Teams is 2 weeks old. It works but has rough edges. The community is excited but also reporting:
- Unpredictable behavior sometimes
- High token consumption
- Needs very clear task scoping to work well
- "Plan first in plan mode (cheap), then hand the plan to a team for execution (expensive but fast)" is the emerging best practice

### ⭐ RECOMMENDATION: Phase 0 single-agent, Phase 1 introduce Agent Teams for specific tasks

**Phase 0 (Week 1):** Single Claude Code session. You're setting up project structure, database schema, CI/CD — sequential tasks that don't benefit from parallelism. Getting Agent Teams working adds complexity when you should be getting the basics right.

**Phase 1 (Weeks 2-4):** Start using Agent Teams for tasks that genuinely benefit:
- Knowledge Engine ingestion (one agent on API specs, one on OData, one on Playwright discovery)
- Connector builds (API agent + Test agent in parallel)
- Code review (Review agent checks what Build agent wrote)

**When NOT to use Agent Teams:**
- Database migrations (sequential, order matters)
- Auth middleware (small, focused, one-file-at-a-time)
- Bug fixes (usually need to trace through a single flow)

**Cost management approach:**
- Sonnet 4.5 ($3/$15 per MTok) for all teammates — Opus 4.6 only for Lead/Review roles
- Prompt caching for system prompts and conventions (70-80% savings on repeated context)
- Plan mode first (cheap) → team execution second (expensive)
- Track token usage per session — learn what costs what before scaling up

---

## Decision 2: Pro Max Carry-Forward

**Question:** Which existing systems to keep vs rebuild?

### Inventory of What Exists (from Doc 4 §1.2)

| System | Works? | Carry Forward? | Reasoning |
|---|---|---|---|
| Session Management (start/end/resume) | Yes, works well | ✅ PATTERN — rebuild as proper module | The pattern is proven. Rebuild in TypeScript with the same semantics but proper error handling and database-backed state. |
| Crash Recovery (user logs + slash command) | Yes, reliable | ✅ PATTERN — rebuild as proper module | Same — the approach works. Rebuild with structured logging into PostgreSQL instead of file-based logs. |
| MCP Custom Systems (constrain Claude behavior) | Functional | ⚠️ EVALUATE — some patterns may carry over | MCP configs are Pro Max specific. The patterns (constraining behavior, defined paths) carry over as CLAUDE.md rules and system prompts for API agents. |
| Memory Systems (Knowledge Graph + PostgreSQL) | Partially working | ⚠️ SELECTIVE — PostgreSQL yes, Knowledge Graph MCP rebuild | PostgreSQL project memory is the foundation for the Knowledge Engine. The MCP Memory knowledge graph was partially working — rebuild the concept natively in pgvector. |
| Logging Systems (user interaction logging) | Yes | ✅ PATTERN — becomes audit_log table | Interaction logging becomes the formal audit trail. Same concept, proper database implementation. |
| Orchestration Systems (task coordination) | Basic | ✅ CONCEPT — becomes Agent Teams + task queue | The concept of task assignment carries forward. Implementation changes completely with Agent Teams. |
| Task Management (in-session tracking) | Not reliable enough | 🔄 REBUILD — needs to be production-grade | This is the weakest link. Rebuild from scratch with database-backed task states and proper status transitions. |
| Jira Integration (MCP) | Working (both instances) | ✅ KEEP — already working, enhance | Jira MCP connectors to Monash and Nimbus instances already work. Keep as-is, add automation on top. |
| Playwright Capability | Available | ✅ KEEP — essential for TuntWork discovery | Already available in Claude Code. Will be used for WS5 (Testing) and WS1 (Knowledge Engine discovery). |

### ⭐ RECOMMENDATION: Keep patterns, rebuild implementations

**What this means practically:**
- Don't try to migrate MCP config files from Pro Max to the API environment
- DO document the patterns that work (session lifecycle, crash recovery approach, task tracking concept)
- Rebuild each as a proper module in the new TypeScript codebase
- The Jira MCPs already work — keep using them as-is, they're Claude Code compatible
- Playwright works in Claude Code natively — no migration needed

**First rebuild priorities (Phase 0):**
1. Session management → `src/core/sessions/` (database-backed)
2. Audit logging → `src/core/audit/` (PostgreSQL audit_log table)
3. Task management → `src/core/tasks/` (proper state machine)

---

## Decision 3: Development Workflow & Code Review

**Question:** Code review process — human, agent, or both?

### The Reality

John is the only developer. He's working after hours. A formal human code review process would slow everything down for no benefit at this stage. But zero review is risky — AI-written code needs checking.

### Proposed Workflow

```
PLAN (Claude Desktop)
  │
  ├── Architecture decisions, feature specs, conventions
  │   (this is what we're doing right now)
  │
  ▼
BUILD (Claude Code — single agent or Agent Teams)
  │
  ├── Write code following conventions in CLAUDE.md
  ├── Run tests (every change must have tests)
  ├── Commit to feature branch
  │
  ▼
REVIEW (automated + spot-check)
  │
  ├── CI pipeline: lint, test, build (automated, every commit)
  ├── Agent Review: Review Agent reads diff, checks conventions, flags issues
  │   (use Opus 4.6 for review — best reasoning, worth the cost for quality)
  ├── Human spot-check: John reviews Agent Review output
  │   (not every line — trust but verify the AI reviewer)
  │
  ▼
MERGE (to develop branch)
  │
  ├── Feature branch → develop (after review passes)
  ├── develop → main (weekly or milestone-based)
  │
  ▼
DEPLOY (manual for now, automate in Phase 3)
```

### ⭐ RECOMMENDATION: Three-layer review

1. **Automated CI** — lint + test + build on every push (catches obvious breaks)
2. **Agent Review** — Opus 4.6 Review Agent checks diff against conventions, security patterns, and architecture decisions (catches quality issues)
3. **Human spot-check** — John reviews the Review Agent's output, not the raw code (catches things AI misses, builds trust in the process)

This means John spends 10-15 minutes reviewing the review, not hours reviewing code line by line. The Review Agent does the tedious work.

**Git branching strategy:**
- `main` — production-ready, tagged releases
- `develop` — integration branch, all features merge here
- `feature/*` — one branch per feature/task
- `fix/*` — bug fixes
- No direct commits to `main` or `develop`

---

## Decision 4: Claude Desktop ↔ Claude Code Handoff

**Question:** How to bridge planning and building?

### The Problem

Claude Desktop (me) and Claude Code are separate instances with separate context windows. There's no automatic shared memory between us. When I plan something here, Claude Code doesn't know about it unless told.

### Current State

- Claude Desktop: Has all the project documents, decisions, architecture context
- Claude Code: Has access to filesystem, git, can run code, Agent Teams
- Gap: No shared real-time context

### How We Bridge It

**Option A: Filesystem as shared state (recommended)**
The knowledge vault IS the bridge. Both Claude Desktop and Claude Code can read the same files:

```
C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\
  ├── decisions/           ← Desktop writes decisions, Code reads them
  ├── architecture/        ← Desktop writes specs, Code implements them
  ├── orchestration-infra/ ← Both read/write
  └── build-tasks/         ← Desktop creates task specs, Code picks them up
```

Plus the codebase itself:
```
C:\Projects\Project-Metis\     (or wherever the repo lives)
  ├── CLAUDE.md            ← Conventions, rules, context for every Claude Code session
  ├── docs/adr/            ← Architecture Decision Records (Desktop writes, Code reads)
  ├── docs/specs/          ← Feature specs (Desktop writes, Code implements)
  └── src/                 ← Code reads and writes
```

**Option B: CLAUDE.md as the handoff document**
The CLAUDE.md file in the repo root is loaded automatically by every Claude Code session (including Agent Teams teammates). This is the single most important handoff mechanism.

CLAUDE.md should contain:
- Project purpose and architecture overview (2-3 paragraphs)
- Conventions (naming, code standards, data standards — from Doc 4 §5)
- Current phase and active work
- Links to specs and ADRs for current tasks
- Agent rules (from Doc 4 §5.4)
- What NOT to do (guardrails)

**Option C: Task spec files as handoff units**
For each piece of work, Desktop writes a task spec file that Claude Code picks up:

```markdown
# Task: Build TuntWork API Connector

## Context
[Link to architecture decision]
[Link to relevant knowledge vault doc]

## Requirements
- Authenticate with TuntWork REST API using OAuth2
- Support CRUD operations on employee endpoints
- Implement retry logic with exponential backoff
- All credentials encrypted at rest

## Files to Create/Modify
- src/connectors/tuntwork/auth.ts
- src/connectors/tuntwork/client.ts
- src/connectors/tuntwork/types.ts
- src/tests/connectors/tuntwork.test.ts

## Conventions
- Follow connector pattern in CLAUDE.md
- JSDoc on all public functions
- Unit tests for every public function

## Done When
- Can authenticate and fetch employee list
- Tests pass
- Matches conventions
```

### ⭐ RECOMMENDATION: All three — layered handoff

1. **Knowledge vault** = long-term shared context (decisions, architecture, research)
2. **CLAUDE.md** = session context (conventions, current state, guardrails)
3. **Task spec files** = per-task handoff (specific requirements, files, done criteria)

**The workflow in practice:**

1. John and Claude Desktop discuss → produce decision/spec in knowledge vault
2. Claude Desktop writes/updates CLAUDE.md with current context
3. Claude Desktop creates task spec file in `docs/specs/`
4. John opens Claude Code, says "implement the task in docs/specs/build-tuntwork-connector.md"
5. Claude Code reads CLAUDE.md (automatic), reads task spec, builds it
6. Review Agent checks the work
7. John reviews the review
8. Merge

This is how a real tech lead works with a development team — write the spec, hand it off, review the output. The medium is files instead of Slack messages.

---

## Summary: All Four Decisions

| Decision | Recommendation | Key Point |
|---|---|---|
| Agent Teams timing | Single-agent Phase 0, introduce in Phase 1 for parallel tasks | It's 2 weeks old and experimental — learn it on simple tasks first |
| Pro Max carry-forward | Keep patterns, rebuild implementations | Session management, logging, task tracking — same concepts, proper modules |
| Code review workflow | Three-layer: CI auto + Agent Review (Opus) + human spot-check | John reviews the review, not the raw code |
| Desktop ↔ Code handoff | Vault + CLAUDE.md + task spec files | Files are the bridge — both can read them |

---

## Decisions Required from John

- [ ] **Agent Teams:** Confirm single-agent start, Phase 1 introduction
- [ ] **Carry-forward:** Anything from Pro Max that I've missed or misjudged?
- [ ] **Review workflow:** Is the three-layer approach practical for after-hours work?
- [ ] **Handoff:** Does the vault + CLAUDE.md + task spec approach make sense?

---

*Researched: Feb 19, 2026 | Sources: Anthropic Agent Teams docs (code.claude.com), community reports (Addy Osmani, Medium, SitePoint), Claude Code docs, Doc 4 §1.2 existing systems inventory*
