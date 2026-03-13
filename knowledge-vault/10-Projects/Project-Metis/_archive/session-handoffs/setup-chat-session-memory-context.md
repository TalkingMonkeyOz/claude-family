---
tags:
  - project/Project-Metis
  - session-handoff
  - area/orchestration-infra
  - area/knowledge-engine
  - topic/context-assembly
created: 2026-02-24
session: pending-chat-session-memory
---

# Session Setup: Session Memory & Context Persistence

**STATUS: ⚠ PARTIAL** — Chat #8a brainstorm exists but was Claude monologue (UNVALIDATED by John). Needs review before relying on content.

**Chat Topic:** How the platform maintains state during sessions, survives context compaction, and persists knowledge across sessions.

**Area(s):** Orchestration & Infrastructure (Area 7) + Knowledge Engine (Area 1) — cross-cutting

**Level:** Brainstorm — capture ideas, flag gaps, don't spec implementation

## Read These First

1. `orchestration-infra/README.md` — overall orchestration brainstorm, session management section
2. `orchestration-infra/agent-compliance-drift-management.md` — five-layer enforcement architecture, especially Layer 3 (task-driven context) and what works/doesn't from Claude Family
3. `orchestration-infra/agent-conventions.md` — 8 rules, enforcement layers
4. `knowledge-engine/brainstorm-knowledge-engine-deep-dive.md` — knowledge taxonomy, scope hierarchy, retrieval design
5. `system-product-definition.md` — what The System is (generic platform for dev houses)
6. Doc 6 in project files (`nimbus_doc6_constrained_deployment.docx`) — four-layer constraint architecture, especially §3.2 cached knowledge scoping

## What's Already Captured (Don't Redo)

- **Session management lifecycle:** start → work → end → resume. Database-backed. In orchestration README.
- **Session facts pattern:** Mentioned as "what works" in agent compliance doc. Custom scratchpad that survives compaction. Outperforms native memory graph.
- **Context JSONB:** Sessions table has a context JSONB field for session state. Mentioned but not designed.
- **Five-layer enforcement:** Rules injection, CLAUDE.md reinjection, task-driven context, sub-agent isolation, BPMN gates. Architecture decided.
- **CLAUDE.md reinjection:** Every 15 interactions. Decided but mechanism not designed.
- **200K cached prompt:** Constrained deployment pattern. Core knowledge cached in system prompt. Decided.
- **Two-tier model:** Core knowledge in cached prompt, bulk domain knowledge in MCP/KMS layer. Referenced in memory graph but not designed.

## What's NOT Designed (The Gaps)

### 1. Session Scratchpad / Agent Facts
- What exactly gets stored during a session?
- Who writes to it — the agent automatically, or explicitly via a tool?
- What format? Free text? Structured key-value? Both?
- How does the agent read it back after compaction?
- Is it per-session, per-task, or per-agent?
- How does it differ from the audit log? (audit = what happened, scratchpad = what matters right now)

### 2. Context Assembly
- When a query or task comes in, what gets assembled into the prompt?
- What's the assembly order? System prompt → cached knowledge → session context → retrieved knowledge → user query?
- How much of the 200K token cache is allocated to: core rules, domain knowledge, session state, retrieved context?
- What happens when context gets too large? What gets dropped first?
- How does retrieval (RAG) interact with cached knowledge? Do they overlap? Complement?

### 3. Cross-Session Persistence
- What survives when a session ends? (session context JSONB, work items, audit log — but what's the retrieval mechanism for the NEXT session?)
- How does a new session pick up where the last one left off? What gets loaded automatically?
- How does this work across different agents? (KnowledgeAgent ends, ConfigAgent starts — what context transfers?)

### 4. Compaction Survival
- Claude Family lesson: context compaction loses information. Session facts/notepad was built specifically to survive this.
- What's the equivalent mechanism for The System?
- Is it file-based (write to disk), database-based (write to session context), or tool-based (dedicated scratchpad tool)?
- How frequently should the agent checkpoint to the scratchpad?

### 5. Two-Tier Knowledge Model
- Tier 1: Cached system prompt (200K tokens) — core knowledge always in context
- Tier 2: MCP/KMS retrieval — bulk domain knowledge retrieved on demand
- What goes in Tier 1 vs Tier 2? How do we decide?
- How do they interact at query time? Does retrieval augment or replace cached knowledge?
- What's the overflow strategy when Tier 1 exceeds 200K?

## Claude Family Lessons to Discuss

These are direct experience from building and running Claude Family. They should inform the design:

- **Hook injection works.** rag_query_hook.py fires on every prompt, injects relevant context silently. Recency bias means rules at END of prompt work better than at START.
- **Custom scratchpad outperforms native memory graph.** The MCP Memory knowledge graph added noise, not value. Custom session facts/notepad was more reliable.
- **Long rule sets loaded once fade.** "Lost in the middle" effect. Must reinject, not load once.
- **Sub-agent isolation is the strongest defence.** Fresh context per task beats long sessions.
- **Explicit verbose rules beat elegant short ones.** "Read the file before saying it contains X" works. "Verify before claiming" does not.

## Outcome Expected

A brainstorm vault file covering session memory + context assembly design. Should answer: what state exists, where it lives, how it gets into the prompt, how it survives compaction and session boundaries. Gaps and open questions flagged, not necessarily resolved.

---
*Setup doc for next chat session — created 2026-02-24*
