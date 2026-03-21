---
projects:
- claude-family
- project-metis
tags:
- coding
- research
- CKG
- context-engineering
- metis
---

# Coding Intelligence Research

## How We Got Here

**2026-03-20**: Built the Code Knowledge Graph (CKG) system — tree-sitter indexer parsing Python, TypeScript, Rust, C# across 5 projects (3,759 symbols, 19,517 cross-references). During the build, discovered Claude has built-in LSP tools (`goToDefinition`, `findReferences`, `documentSymbol`, etc.) that are rarely used in coding sessions.

**2026-03-21**: User asked what tools Claude forgets to use. Analysis showed 15 of 66 tools had zero calls ever; top 10 tools = 80% of all usage. The CKG tools themselves were brand new and not yet discoverable by other Claude instances.

**The catalyzing example**: In Monash Reports, two in-cell dropdown components were created doing the same thing — one in each view, built in different sessions, with no awareness of the other. Classic cross-session duplication.

**User's question**: "What tools can we give you to do a better job at coding? And is it even worth building?"

This is the prototype for **Metis** — the vision of a cohesive AI development platform with automatic context assembly.

## Research Sources

### 1. Codified Context (arxiv 2602.20478, Feb 2026)
**URL**: https://arxiv.org/html/2602.20478v1

Study of 283 development sessions on a 108,000-line C# distributed system. Three-tier knowledge architecture:
- **Tier 1 (Hot)**: ~660-line constitution always loaded. Conventions, checklists, known failure modes.
- **Tier 2 (Warm)**: 19 specialist agents (~9,300 lines total), invoked per task via trigger tables. Over 50% is domain knowledge, not just behavioral instructions.
- **Tier 3 (Cold)**: 34 knowledge docs (~16,250 lines), retrieved on-demand via MCP.

Key findings:
- Agents "trust documentation absolutely" — making staleness a critical failure
- Knowledge-to-code ratio reached 24.2%
- "Retrieval as a PLANNING step before implementation"
- Complex domains need complete mental models embedded in agents, not just cold retrieval

### 2. Context Engineering for Coding Agents (Martin Fowler, 2026)
**URL**: https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html

Three context-loading triggers:
- **LLM-triggered** (skills, MCP): Probabilistic — no guarantee Claude will use it
- **Human-triggered** (slash commands): Deterministic but manual
- **Software-triggered** (hooks): Deterministic at lifecycle events — this is what we want

Skills as bundles of instruction + supporting resources. Warning about "illusion of control" — context engineering increases probability but can't guarantee behavior.

### 3. Advanced Context Engineering (HumanLayer, 2026)
**URL**: https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md

Three-phase workflow: **Research → Plan → Implement**
- "Frequent intentional compaction" — keep context at 40-60%
- Plans are the connecting artifact between phases
- "Specs became our source of truth for what was being built and why"
- High-leverage human review at research and plan stages, minimal at code level
- Used to handle 300K LOC Rust codebases

### 4. Titansoft RAG Knowledge Base (2026)
**URL**: https://blog.titansoft.com.sg/2026/03/17/we-built-a-custom-knowledge-base-so-our-ai-assistant-would-stop-forgetting-everything/

Vector DB + MCP server for cross-session knowledge persistence. Atomic updates — modify individual entries without re-ingesting. Same knowledge accessible from any AI tool via shared MCP interface.

### 5. Augment Code Semantic Engine (2026)
**URL**: https://siliconangle.com/2026/02/06/augment-code-makes-semantic-coding-capability-available-ai-agent/

Enterprise-grade semantic dependency analysis. Understands service boundaries, API contracts, and configuration inheritance across multiple repositories.

### 6. Copilot Semantic Code Search (GitHub, March 2026)
**URL**: https://github.blog/changelog/2026-03-17-copilot-coding-agent-works-faster-with-semantic-code-search/

Copilot agent now searches by meaning rather than exact text matches. Industry trend: hybrid indexing (AST + semantic) is becoming standard.

## Design Synthesis

### What We Already Have (Disconnected)

| Layer | Components | Status |
|-------|-----------|--------|
| **Tier 1 (Hot)** | CLAUDE.md, coding-ethos instruction, core protocol | Working |
| **Tier 2 (Warm)** | CKG, LSP, coding standards DB, workfile dossiers | Exists but not connected |
| **Tier 3 (Cold)** | Vault RAG, DB schema, entity catalog, dependency graphs | Working but underused |

### The Connected Model

Not more tools — a **workflow** with three intensities:
- **Small** (1 file): Quick CKG check → implement → hooks validate
- **Medium** (2-3 files): Research → brief plan → implement → review
- **Large** (3+ files): Full Structured Autonomy with agent spawning

The **dossier as hub**: auto-populated from CKG, standards, memory, module maps. One call (`unstash`) loads all coding context for a component.

### Open Questions (All Resolved)
1. **Are the problems real?** YES — audit found 28 duplicate functions, 1,437-line monolith, repeated state management across 4 projects.
2. **What other problems?** Expanded from 4 to 10 categories (naming drift, cognitive debt, verification debt, shallow error handling, god classes).
3. **Worth building?** YES — industry data: 1.7x more issues, 4x duplication in AI code. Our audit confirmed.
4. **Enforcement mechanism?** Advisory skill + hooks (not blocking). `/coding-intelligence` skill guides workflow; hooks auto-load dossier at session start.

## Related Work Items
- **Feature**: F156 (Coding Intelligence System) — COMPLETED 2026-03-21
- **BPMN**: `coding-intelligence-workflow.bpmn` (3 intensity paths)
- **Skill**: `/coding-intelligence` (registered in DB, deployed)
- **Why doc**: [[coding-intelligence-why.md]]
- **Usage guide**: [[dossier-usage-guide.md]]
- **Dossier workfile**: `coding-intelligence` component (pinned)
- **Bug fix**: FB207 (CKG arrow function indexing) — RESOLVED
- **Metis connection**: Prototype for Metis AI development platform

---
**Version**: 1.1
**Created**: 2026-03-21
**Updated**: 2026-03-21
**Location**: 20-Domains/coding-intelligence-research.md