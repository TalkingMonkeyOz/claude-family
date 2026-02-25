---
tags:
  - project/Project-Metis
  - area/orchestration-infra
  - scope/system
  - level/1
  - phase/0
  - phase/1
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-02-24
synced: false
---

# Orchestration & Infrastructure

> **Scope:** system (core platform infrastructure — everything else depends on this)
>
> **Design Principles:**
> - No-code for the human operator — direct through natural language, review outcomes
> - Agent patterns rebuilt fresh, not migrated — concepts carry forward, implementations don't
> - Security is a feature, not a phase — encryption, audit trails, isolation from day one
> - Modular and replaceable — no component should be irreplaceable

> The plumbing everything else runs on. Agent coordination, shared state, database, authentication, environments.

**Priority:** CRITICAL — Phase 0-1
**Status:** ✓ BRAINSTORM-COMPLETE (Chat #8 + revisit + 14 sub-files. Session memory brainstorm exists but UNVALIDATED.)
**Parent:** [[Project-Metis/README|Level 0 Map]]

## What This Area Covers

Everything that isn't a specific business capability but is needed for any of them to work. The foundation layer.

## Brainstorm Items

### Core Operating Principle: No-Code for John

John directs, Claude builds. John is the architect and decision maker. All code is written by Claude Code (single agent or agent teams). This is a no-code operation from John's perspective. The platform, the tools, the conventions — all designed so John can direct work through natural language, review outputs, and make decisions without writing code.

Claude Family patterns (session management, crash recovery, memory, logging, Jira integration, Playwright) are proven concepts that get rebuilt fresh by Claude Code in the new platform. Nothing is literally ported from the existing Claude Family environment.

### Agent Orchestration (from Doc 4 WS3)

- **Agent Roles:** Define specialist agents — Knowledge Agent, Config Agent, Testing Agent, Documentation Agent, Orchestrator
- **Task Queue:** Shared task list that agents claim and work on. Priority-based assignment
- **Inter-Agent Messaging:** Direct communication between agents (leveraging Claude Code Agent Teams)
- **Shared State:** Central database that all agents read/write. Current project status, decisions, blockers
- **Session Management:** Build on existing Claude Family session start/end/resume pattern. Make it production-grade
- **Error Recovery:** Build on existing crash recovery. Agents that fail should resume gracefully
- **Audit Trail:** Every agent action logged. Who did what, when, why. Full traceability
- **Human-in-the-Loop:** Defined checkpoints where human review is required before proceeding

### Database Architecture (from Doc 4 §4.1)

Recommended: PostgreSQL + pgvector (single database, simpler ops, good enough vector search for our scale)

Proposed tables:
- `clients` — Client records (Monash, etc)
- `knowledge_items` — Domain knowledge entries with embeddings
- `configurations` — time2work config snapshots
- `sessions` — Agent session records
- `tasks` — Task queue for agents
- `agent_messages` — Inter-agent communication log
- `audit_log` — Every action taken
- `test_scenarios` — Award test scenarios
- `documents` — Generated documentation
- `credentials` — Encrypted API credentials
- `user_access` — Multi-user access control

### Security Architecture (from Doc 4 §4.2)

- **Authentication:** Multi-user login with role-based access. Start with JWT, design for SSO later
- **Credential Storage:** AES-256 encryption at rest for all API credentials
- **Data Isolation:** Client data strictly separated. Monash data never visible to other clients
- **Audit Trail:** Every read/write logged with user, agent, timestamp, detail
- **Environment Separation:** UAT and Production as separate trust zones
- **API Key Management:** Anthropic keys stored securely. Rate limiting and cost caps
- **Data Residency:** All data hosted in Azure Australia East. No data leaves Australia

### Environment Strategy (from Doc 4 §4.3)

| Environment | Purpose | Hosted | Access |
|-------------|---------|--------|--------|
| Local Dev | John + Claude Code | John's PC | John only |
| Dev/Test | Integration testing | Azure (nimbus) | Dev team |
| Monash POC | Isolated client env | Azure (isolated) | John + Monash |
| Production | Live service | Azure (nimbus) | Authorised users |

### Pro Max → API Transition (from Doc 4 §2)

**Recommended:** Hybrid approach
- Keep Claude Desktop on Pro Max for planning, docs, conversation (this is what I'm doing now)
- Use API keys for Claude Code agent teams to do the actual building
- Best of both worlds without losing what already works

API unlocks: Agent Teams, inter-agent communication, autonomous operation, parallel execution, 1M token context (Opus 4.6), batch processing (50% discount), prompt caching (70-80% savings)

### Conventions & Standards (from Doc 4 §5)

- Database tables: snake_case, plural
- API endpoints: kebab-case, REST
- TypeScript for platform services, Python for data science/scripting
- All dates ISO 8601, UTC in storage
- UUIDs for internal records
- Soft delete (deleted_at) not hard delete
- UTF-8 everywhere
- Git branches: type/description (e.g. feature/knowledge-engine)
- Agent names: PascalCase with role (e.g. KnowledgeAgent)

### Agent Team Design (from Doc 4 §8)

| Agent Role | Model | Scope |
|-----------|-------|-------|
| Lead/Orchestrator | Opus 4.6 | All (read), orchestration (write) |
| API Agent | Sonnet 4.5 | src/connectors/, src/api/ |
| Knowledge Agent | Sonnet 4.5 | src/knowledge/, src/search/ |
| Testing Agent | Sonnet 4.5 | src/tests/, src/playwright/ |
| Review Agent | Opus 4.6 | All (read-only) |

Cost management: Sonnet for 80% of work, Opus for Lead and Review only. Cache system prompts. Keep tasks focused. Batch non-urgent work for 50% discount.

### Storage Architecture (from Doc 4 §9)

**Recommended:** Hybrid — Database + Vault
- Database is source of truth for operational data (configs, sessions, tasks, test results)
- Vault (git-managed markdown) is source of truth for architecture decisions, documentation templates, knowledge that benefits from version control and human readability

## What Already Exists (from Doc 4 §1.2)

- Session management (start/end/resume) — works well
- Crash recovery system — works reliably
- MCP custom systems — functional, needs improvement
- Memory systems (knowledge graph + PostgreSQL) — partially working, connectivity issues
- Logging systems — functional
- Orchestration systems — basic task coordination
- Jira integration (MCP) — connected to both Monash and Nimbus instances

## Known Gaps (from Doc 4 §1.3)

- MCP connectivity issues (filesystem, PostgreSQL, Py-Notes-Server)
- Claude Code ↔ Claude Desktop have no shared context
- Cross-session memory not automatic
- Task tracking not reliable enough for production
- Pro Max can't do inter-agent communication or autonomous agent teams

## Open Decisions

- [ ] #decision API key provisioning — personal account or nimbus org? Budget cap? → [[decisions/README]]
- [ ] #decision Azure environment — request now or wait for approval? VM/DB tier? → [[decisions/README]]
- [ ] #decision Git repo — GitHub (personal) or Azure DevOps (nimbus)? → [[decisions/README]]
- [ ] #decision Agent Teams — from day one or single-agent first? → [[decisions/README]]
- [ ] #decision Authentication model — JWT first, design for SSO swap later? → [[decisions/README]]
- [ ] #decision What to carry forward from Pro Max vs rebuild? → [[decisions/README]]

## Phase 0 Deliverables

- [ ] Git repository with branch strategy
- [ ] Anthropic API key provisioned and secured
- [ ] Agent Teams enabled
- [ ] PostgreSQL + pgvector deployed
- [ ] Base schema deployed
- [ ] Project directory structure with conventions
- [ ] CI/CD pipeline (basic)
- [ ] ADR template and initial decisions recorded
- [ ] MCP servers verified and functional

## Sub-Topics

### Infrastructure & Environment
- [[orchestration-infra/infra-decisions-api-git-auth|Infrastructure Decisions]] — API keys, Git repo, authentication model
- [[orchestration-infra/azure-infrastructure-recommendation|Azure Infrastructure]] — VM sizing, PostgreSQL, cost estimates
- [[orchestration-infra/claude-data-privacy-reference|Claude Data Privacy]] — API data handling, retention, AU residency

### Development Process
- [[orchestration-infra/dev-decisions-agents-workflow-handoff|Dev Decisions]] — Agent Teams, carry-forward, workflow, Desktop↔Code handoff
- [[orchestration-infra/phase-0-task-list|Phase 0 Task List]] — ordered tasks for Claude Code to stand up the project foundation
- [[orchestration-infra/claude-md-template|CLAUDE.md Template]] — conventions file template for the repo
- [[orchestration-infra/cicd-pipeline-spec|CI/CD Pipeline]] — automated quality checks, stages, quality gates
- [[orchestration-infra/agent-conventions|Agent Conventions]] — 8 enforceable rules, measurability, enforcement layers

### Agent Compliance
- [[orchestration-infra/agent-compliance-drift-management|Agent Compliance & Drift Management]] — five-layer enforcement architecture, compliance metrics, protocol anti-compression. STATUS: EXPERIMENTAL

### Session Memory & Context
- [[orchestration-infra/session-memory-context-persistence|Session Memory & Context Persistence]] — scratchpad design, context assembly order, two-tier knowledge model, compaction survival, cross-session handoff. STATUS: BRAINSTORM

### Operations
- [[orchestration-infra/autonomous-operations|Autonomous Operations]] — what runs without a human, hosting model, guardrails, cost management
- [[orchestration-infra/day-1-readiness|Day 1 Readiness Plan]] — what must work before the platform is in use
- [[orchestration-infra/user-experience|User Experience & Productivity Target]] — BHAG 20%+ productivity, interface strategy
- [[orchestration-infra/monitoring-alerting-design|Monitoring & Alerting]] — what we watch, how we get notified, phased approach

## Related Areas

- [[knowledge-engine/README|Knowledge Engine]] — depends on this database and search infrastructure
- [[integration-hub/README|Integration Hub]] — depends on auth, credential storage, connector patterns
- All other areas depend on orchestration being solid

---
*Source: Doc 4 §2, §3.2 WS3, §4, §5, §8, §9 | Created: 2026-02-19 | Updated: 2026-02-24 — sub-topics reorganised, new files linked*
