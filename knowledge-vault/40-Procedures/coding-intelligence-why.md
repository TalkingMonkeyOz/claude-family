---
projects:
- claude-family
tags:
- coding-intelligence
- ai-assisted-development
- context-engineering
- why-we-build
---

# Why We're Building the Coding Intelligence System

## The Problem

**AI-assisted code has measurable quality issues:**
- **1.7x more bugs** than human-written code (industry data, 2026)
- **4x higher duplication** — same logic reimplemented 3+ times per codebase
- **52-78% contain code smells** — poor structure, god classes, cognitive debt
- **Context loss** — decisions from brainstorms vanish; not captured in code

**We saw this in our own projects:**
- claude-family: 28 identical `get_db_connection()` functions
- trading-intelligence: 3+ implementations of Sharpe ratio, CAGR, return calculations
- nimbus-mui: 1,437-line monolithic component handling 6 separate concerns
- monash-nimbus-reports: 4 report types each reimplementing state management

These aren't hypothetical problems — they cause real maintenance burden.

## Why It Happens

Every Claude session starts from scratch:
1. **No persistent code memory** — can't remember prior implementations
2. **No semantic code search** — can't find similar patterns
3. **Context loss between sessions** — decisions made during brainstorms aren't captured
4. **Manual context assembly** — each task requires researcher to hunt for patterns
5. **No enforced standards** — same problem solved 3 different ways

## The Three-Tier Context Model

Industry research (Codified Context paper, Martin Fowler, HumanLayer ACE guide) shows what works:

| Tier | Load Pattern | Volume | Purpose |
|------|--------------|--------|---------|
| **Tier 1 (Hot)** | Always | ~660 lines | CLAUDE.md, core protocol, coding ethos |
| **Tier 2 (Warm)** | Per-task | ~9,300 lines | CKG results, dossier, standards, LSP |
| **Tier 3 (Cold)** | On-demand | ~16,250 lines | Vault, schema, catalog, graphs |

**Key insight**: Knowledge-to-code ratio reaches 24.2% in well-organized projects. We have the infrastructure — it's just disconnected.

## What We Build

**Not** another tool. **A workflow** that connects existing tools:

1. **Small task** (1 file): Quick CKG check → implement → hooks validate
2. **Medium task** (2-3 files): Research → brief plan → implement → review
3. **Large task** (3+ files): Analyst researches → coder implements → reviewer reviews

**The hub**: _Dossier_ — component-scoped working context auto-populated from:
- CKG (10-20 related symbols)
- Coding standards (file-type rules)
- Active memory (relevant decisions)
- Module map (structure)
- Existing patterns

One `unstash()` call loads all context instead of invoking 5 tools.

## Success Looks Like

- Reduce duplication below 15% (currently 35-52%)
- Issue density in AI code < 1.2x human code (currently 1.7x)
- 80%+ of design decisions captured in working memory
- Code-smell prevalence < 30% (currently 52-78%)
- 3+ file features work without manual context compilation

## Related Work

- **Research doc**: [[coding-intelligence-research.md]] (full synthesis)
- **Workfile dossier**: stashed in `coding-intelligence` component
- **Feature**: F156 (this system)
- **BPMN model**: `coding-intelligence-workflow.bpmn` (under development)

---
**Version**: 1.0
**Created**: 2026-03-21
**Updated**: 2026-03-21
**Location**: 40-Procedures/coding-intelligence-why.md
