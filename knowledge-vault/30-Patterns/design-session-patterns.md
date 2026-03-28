---
projects:
- claude-family
- project-metis
- project-hal
tags:
- patterns
- design-session
- context-engineering
- brainstorming
---

# Design Session Patterns for AI Agents

Research compiled 2026-03-25 from Superpowers framework, Zylos Research, Anthropic docs, QCon 2026, and community best practices.

## The Superpowers 3-Phase Pattern (De Facto Standard)

From obra/superpowers (93K+ stars). Three phases with strict sequencing:

1. **Understand** — Socratic questions to fill gaps. Purpose, constraints, success criteria. Not a comprehensive interrogation — focused gap-filling.
2. **Explore** — Multiple approaches with trade-offs. Reasoned recommendations, not equally-weighted options. The AI has an opinion.
3. **Design** — Build piece-by-piece with checkpoints. "Does this work?" throughout. Iterative refinement creates shared ownership.

**Key principle**: "Structure enables creativity" — the framework guides without constraining.

## Anchored Iterative Summarization (Best Context Technique)

From Zylos Research (scored 4.04 vs competitors at 3.43-3.74). Maintain a persistent 4-field anchor:

1. **Intent** — what are we trying to achieve
2. **Changes made** — what has been done
3. **Decisions taken** — what has been decided
4. **Next steps** — what remains

On compaction, only newly-evicted messages are summarized and merged into the anchor. Maps directly to `store_session_fact("design_anchor", ...)`.

## Context Drift (The Real Killer)

**65% of enterprise AI failures in 2025 were context drift, not context exhaustion** (Zylos Research).

**Drift detection signals:**
- Agent re-processes completed work
- Goal statement rewording without user direction
- Technical detail corruption (variable names, file paths)
- "Forgotten" system instructions

**Prevention:**
- Compress at 70% utilization, not reactively at limits
- Content-aware ratios: old turns 3:1-5:1, tool outputs 10:1-20:1
- Never compress the 5-7 most recent turns
- Maintain the anchor — always current, always accessible

## The Context Flywheel (QCon London 2026)

Context informs decisions → decisions are captured → captured decisions become future context. The best AI coding teams build this flywheel deliberately.

**In practice**: Every design decision stored via `remember()` becomes retrievable context for the next session. The more disciplined the capture, the richer the future context.

## Co-Agentic Workflow Loop

From Cursor Forum community. Four phases, each producing first-class outputs:

**Plan → Implement → Summarize → Reflect**

Plans, summaries, and reflections are treated as artifacts, not throwaway text. They persist and inform future work.

## Design-First with Document Handoff

From theyawns.com (2026): "Every hour spent on documentation saved multiples in 'no, that's not what I meant' corrections."

- Produce formal design documents BEFORE writing code
- Human pushback is essential — the most valuable moments come from disagreeing with AI recommendations
- 9 documents before any code was written in their case study

## Key Resources

- [obra/superpowers](https://github.com/obra/superpowers) — Skills framework with brainstorming skill
- [Zylos AI Context Compression](https://zylos.ai/research/2026-02-28-ai-agent-context-compression-strategies) — Anchored summarization research
- [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Official recommendations
- [Design-First Claude Code](https://theyawns.com/2026/03/06/launching-a-claude-code-project-design-first-then-build/) — Case study
- [awesome-claude-code-toolkit](https://github.com/rohitg00/awesome-claude-code-toolkit) — 135 agents, 35 skills

## Implementation

These patterns are codified in the `/design-session` skill (global, all projects). See `~/.claude/skills/design-session/SKILL.md`.

---
**Version**: 1.0
**Created**: 2026-03-25
**Updated**: 2026-03-25
**Location**: knowledge-vault/30-Patterns/design-session-patterns.md
