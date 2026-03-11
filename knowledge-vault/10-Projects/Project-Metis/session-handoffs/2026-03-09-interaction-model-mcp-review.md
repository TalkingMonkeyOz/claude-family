---
tags:
  - project/Project-Metis
  - type/session-handoff
  - domain/interaction-model
  - domain/architecture
created: 2026-03-09
session: interaction-model-mcp-review
status: complete
supersedes: 2026-03-08-security-architecture.md
---

# Session Handoff: Human-AI Interaction Model + MCP Review

## Session Summary

Defined the human-AI interaction model for METIS (three constraint levels, dual interface architecture). Reviewed all Claude Family MCP servers and the RAG hook in detail. Established that METIS is a context enhancement platform for Claude. Separated Knowledge Engine from Cognitive Memory as distinct subsystems. Decided to design knowledge system from first principles rather than mapping Claude Family forward.

---

## WHAT WAS DONE

### Interaction Model — 3 Constraint Levels (DECIDED)

| Level | Name | Who Drives | Enforcement | Interface |
|---|---|---|---|---|
| L1 | Guided Workflow | METIS drives | SpiffWorkflow, pre-formed prompts, human validates at gates | Controlled web UI |
| L2 | Assisted Work | User drives | METIS provides knowledge/structure/flags | MCP-exposed services |
| L3 | Open Collaboration | User drives | Minimal structure, maximum freedom | Either |

**Key insight from John:** Claude Family's weakness has been too much freedom for SOP-type work. Constraint level must match the activity type.

**Coding lifecycle:** Level 1 wrapping Level 2/3 — dev work is free but git/branch/PR/review/merge process is enforced.

### Dual Interface Architecture (DECIDED)

METIS needs both:
- **Controlled web UI** — for Level 1 guided workflows
- **MCP server** — for Level 2/3 assisted work and collaboration

Both share the same backend (API Layer, Augmentation Layer, Knowledge Engine). The difference is who drives — Workflow Engine (L1) or user's client (L2/3).

**Build order:** MCP/API first, web UI second. Nimbus staff are technical enough to use Claude Desktop/Code as clients initially.

### MCP Review — Claude Family Inventory (COMPLETED)

**6 Active MCP Servers:**
1. **project-tools v2** — 60 tools. Sessions, work tracking, knowledge/memory/RAG, BPMN sync, messaging, protocols, deployment.
2. **bpmn-engine** — SpiffWorkflow. 50 BPMN processes.
3. **postgres** — direct SQL (unrestricted).
4. **sequential-thinking** — structured reasoning.
5. **mui** — MUI component library.
6. **playwright** — headless browser testing.

**4 Built But Inactive:** vault-rag, tool-search, manager-mui, flaui-testing.

### RAG Hook Analysis (COMPLETED)

`rag_query_hook.py` — fires on every user prompt. Prototype of the Augmentation Layer.

Pipeline:
- **Always:** Core protocol + critical session facts (SQL, no embeddings)
- **Gated:** `is_command()` skips short commands. `needs_rag()` gates expensive queries to questions only.
- **On-demand:** Knowledge graph (pgvector + relationship walk), vault RAG (document embeddings), nimbus context (keyword), schema context (table embeddings), skill suggestions
- **Self-learning:** Implicit feedback (negative phrases, query rephrasing), doc quality tracking, vocabulary expansion
- **Monitoring:** Context health with graduated urgency

### Architecture Framing (DECIDED)

**METIS is a context enhancement platform for Claude.** Everything it does — Knowledge Engine, Cognitive Memory, Augmentation Layer, workflows, integrations — exists to ensure Claude has the right information at the right time to deliver value.

### Knowledge Engine vs Cognitive Memory (DECIDED)

Two distinct subsystems feeding the Augmentation Layer:

| Subsystem | What It Holds | Lifecycle |
|---|---|---|
| Knowledge Engine | What the org knows: product domain, client configs, process definitions, documents | Curated, structured, relatively stable |
| Cognitive Memory | What the AI learned through working | Three tiers: short-term (session notepad), mid-term (project notebook), long-term (institutional memory) |

Both need proper first-principles design. Claude Family implementations are reference, not blueprint.

### Rebuild Not Port (DECIDED)

Claude Family patterns are proven concepts to carry forward — not code to port. METIS rebuilds behind proper API layer with auth, RBAC, multi-user, multi-tenant.

---

## KEY DECISIONS THIS SESSION

| # | Decision | Detail |
|---|---|---|
| 1 | Three constraint levels | L1 Guided (METIS drives), L2 Assisted (user drives + MCP), L3 Open (minimal structure) |
| 2 | Dual interface | Web UI for L1, MCP server for L2/3, shared backend |
| 3 | Build order | MCP/API first, web UI second |
| 4 | Constraint spectrum | SOP work needs tight rails (CF lesson: too much freedom = drift) |
| 5 | Coding lifecycle | L1 process wrapping L2/3 dev work |
| 6 | Knowledge vs Memory | Two distinct subsystems, both feed Augmentation Layer |
| 7 | Design from first principles | Don't map CF RAG forward 1:1, design knowledge system properly |
| 8 | Core framing | METIS = context enhancement platform for Claude |
| 9 | Rebuild not port | CF patterns are proven concepts, not blueprints |

---

## WHAT'S NEXT — PRIORITISED

### 1. Claude Family audit document
CF has been asked to produce a comprehensive audit of all systems — what works, what doesn't, its own assessment. This is critical input for knowledge system design.

### 2. Knowledge Engine + Cognitive Memory design session
From first principles. Knowledge types, storage structure, retrieval patterns, ingestion, decay/promotion, RBAC scoping. Use CF audit as input. This is Area 1 done properly.

### 3. MCP tool design (paused)
Resume AFTER knowledge system is designed. Tools are the interface; the knowledge system is the substance.

### 4. Still open from prior sessions
- Hand plan-of-attack-rewrite-brief.md to Claude Code
- Remaining Gate 1 docs (Process Inventory, Data Entity Map, Business Rules, Integration Points)
- Follow up on msg 67d8af18 (vault sync to claude-family)
- Toolkit Categories 2-4 brainstorm
- Validate unvalidated February vault output conversationally

---

## KEY FILES

| File | Status |
|---|---|
| `session-handoffs/2026-03-09-interaction-model-mcp-review.md` | NEW — this file |
| `security-architecture.md` | Unchanged from last session |
| `gate-one/actor-map.md` | Unchanged |
| `gate-zero/` | All 5 docs complete |

---

## SESSION STARTER FOR NEXT CHAT

```
METIS Session Starter — Post Interaction Model
READ FIRST: `session-handoffs/2026-03-09-interaction-model-mcp-review.md`

CONTEXT: Interaction model decided (3 constraint levels, dual interface).
MCP review complete. Knowledge vs Cognitive Memory separated.
METIS = context enhancement platform for Claude.

WAITING FOR: Claude Family audit document (systems inventory + assessment)

PRIORITY: Knowledge Engine + Cognitive Memory design session
(from first principles, CF audit as input, not mapping CF forward)

AFTER THAT:
1. MCP tool design (paused until knowledge system designed)
2. Hand plan-of-attack-rewrite-brief.md to Claude Code
3. Remaining Gate 1 docs
4. Follow up on msg 67d8af18 (vault sync to claude-family)

KEY FILES:
* session-handoffs/2026-03-09-interaction-model-mcp-review.md
* security-architecture.md (validated)
* system-product-definition.md (v0.3)
* gate-one/actor-map.md (validated)
* gate-zero/ — all 5 docs complete
```

---
*Session: 2026-03-09 | Status: Interaction model decided. MCP reviewed. Knowledge system design next. Awaiting CF audit.*
