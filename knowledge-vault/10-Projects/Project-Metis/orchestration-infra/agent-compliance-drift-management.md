---
tags:
  - project/Project-Metis
  - area/orchestration-infra
  - type/brainstorm-capture
  - scope/system
  - topic/agent-compliance
  - topic/drift-management
  - status/experimental
projects:
  - Project-Metis
created: 2026-02-23
synced: false
---

# Agent Compliance & Drift Management

> **Scope:** The System (generic platform concern — applies to any multi-agent AI system, not nimbus-specific)
>
> **Design Principles:**
> - Don't fight transformer architecture — design around it
> - Measure, compare versions, iterate — no mechanism offers formal guarantees
> - Verbose specific rules beat elegant compressed ones for compliance
> - Layered enforcement — no single mechanism is sufficient
>
> **Status:** EXPERIMENTAL — every mechanism described here must be measured, not assumed to work

**Parent:** [[orchestration-infra/README|Orchestration & Infrastructure]]

## The Problem: Agent Drift Is Real and Measured

Based on Rath 2026 paper (arXiv:2601.04170) + 6+ months Claude Family experience.

### Three Drift Types

| Drift Type | What Happens | Example |
|-----------|-------------|---------|
| **Semantic Drift** | Outputs diverge from intent while remaining syntactically valid | Protocol rules get shortened "for elegance" — losing enforceability |
| **Coordination Drift** | Multi-agent consensus degrades, bottlenecks emerge | Task assignments go stale, work gets duplicated |
| **Behavioral Drift** | Novel strategies emerge that bypass intended processes | Agent caches results in chat instead of using designated tools |

### Key Numbers (Rath 2026)

- Drift signs after median 73 interactions (1-2 hours of active work)
- By 600 interactions, semantic drift affects ~50% of systems
- 42% drop in task success rate for drifted systems
- Behavioral boundaries degrade fastest (46% decline over 500 interactions)
- 3.2x increase in human intervention required for drifted systems

### Three Research-Validated Mitigations

Combined: 80% reduction in drift errors at cost of 23% more compute and 9% latency.

1. **Episodic Memory Consolidation** — Summarise and prune context periodically
2. **Drift-Aware Routing** — Route to agents with higher stability scores, reset drifted ones
3. **Adaptive Behavioral Anchoring** — Inject more baseline examples as drift increases

> Lesson from Claude Family: External memory systems retain 21% higher stability at 300 interactions. Two-level hierarchy (router + specialists) outperforms flat or deep (3+) structures.

## Five-Layer Enforcement Architecture

| # | Layer | Mechanism | Addresses | Failure Mode |
|---|-------|-----------|-----------|-------------|
| 1 | **Core Protocol Injection** | 6-8 rules injected at END of every prompt. Cached system prompt. | Semantic drift (recency bias keeps rules fresh) | Fades in very long sessions |
| 2 | **CLAUDE.md Reinjection** | Full conventions reinjected every N prompts (not just session start) | Context rot. Detailed rules survive longer. | Cost. Frequency tuning needed. |
| 3 | **Task-Driven Context** | work_items table + task spec files. Agent reads spec before each piece of work. | Behavioral drift. Tasks persist independently of chat context. | Tasks go stale if not closed. |
| 4 | **Sub-Agent Isolation** | Complex work spawns sub-agents with clean context per task. | Context rot. Fresh context window per task. | Coordination overhead. |
| 5 | **BPMN Gates** | SpiffWorkflow checks at defined checkpoints. System validates, not agent memory. | All drift types. Mechanical enforcement. | Only works at defined checkpoints. |

Layers 1-2 = soft reminders. Layer 3 = state persistence. Layer 4 = isolation. Layer 5 = mechanical enforcement.

> Lesson from Claude Family: Rules at END of prompts work better than at START (recency bias is real and exploitable). File-persisted state beats chat memory (survives compaction). Sub-agents with clean context beat long sessions. System gates beat agent willpower.

## Protocol Anti-Compression Rule

> Lesson from Claude Family: "You keep changing the core protocol to shorter, more ambiguous instructions. The issue is you have no idea what that means later on." — John

This IS semantic drift. The agent optimises for conciseness (what LLMs naturally do) but compression destroys enforceability.

**Rule:** If a protocol change reduces word count by >10% without adding new specificity, it MUST be flagged for human review.

**Enforcement:**
- Track word count across protocol versions
- Agents can PROPOSE changes but cannot activate without human approval
- `protocol_versions` table stores verbatim text, never summarised
- Each version records: change_reason, changed_by (human/agent), diff_from_previous, compliance_scores while active

## Compliance Metrics Framework

Seven measurable metrics, three measurement layers:

### Metrics

| Metric | What It Measures | How |
|--------|-----------------|-----|
| Task creation compliance | Rule "DECOMPOSE" followed | Audit log: first tool call vs first work_item.create |
| Verify-before-claim rate | Rule "VERIFY" followed | Audit log: reference to file/DB preceded by read? |
| Task closure rate | Task hygiene | work_items completed/failed vs stale at session end |
| Session fact usage | Persistent memory usage | Count fact writes per session, correlate with success |
| Sub-agent spawn rate | Rule "DELEGATE" followed | For 3+ file tasks: spawned sub-agent or did inline? |
| BPMN gate pass/fail | Enforcement catching drift | SpiffWorkflow rejection rate per agent per period |
| Protocol version correlation | What actually works | Compliance scores compared across protocol versions |

### Three Measurement Layers

1. **Automated checks** (every session) — tasks-before-tools, task closure, protocol word count, BPMN gate compliance, session length correlation
2. **Haiku LLM-as-judge** (10% sample) — verify-before-claim, source citation, on-topic adherence, protocol compression detection. Cost ~$0.001 per check.
3. **Human review** (monthly) — protocol version comparison, trend analysis, dashboard review. Data-driven, not gut feel.

### Database Tables

- `protocol_versions` — versioned protocol text with compliance_scores JSONB
- `compliance_checks` — individual check results per session
- `compliance_summaries` — periodic rollups for dashboard and trending

## What Works (Claude Family Evidence)

| Mechanism | Evidence |
|-----------|----------|
| Hook injection every prompt | Recency bias is real and exploitable |
| CLAUDE.md reinjection every N prompts | Periodic > one-time. Frequency needs tuning. |
| Session facts / notepad | Survives compaction. Outperforms native memory graph. |
| Explicit verbose rules | "Read the file before saying it contains X" beats "Verify before claiming" |
| Sub-agent isolation | Strongest defence against context rot. Research confirms. |
| Pattern interrupt ("STOP!") | Breaks autoregressive generation. Works for first rule. |

## What Doesn't Work (Claude Family Evidence)

| Mechanism | Evidence |
|-----------|----------|
| Native memory graph (MCP) | Replaced by custom system. Added noise. |
| Long rule sets loaded once | Fades after ~100 interactions. Must reinject. |
| Tasks (native or custom) | Right idea, unreliable execution. Active experiment. |
| Skills (lazy-loaded) | Flaky activation. Can't rely on for critical compliance. |
| Agent self-modification of protocols | Natural compression tendency degrades compliance. Must be gated. |

## Implementation Sequence

| Phase | What Gets Built | Compliance Layer | Measurement |
|-------|----------------|-----------------|-------------|
| Phase 0 | Core protocol v1 in CLAUDE.md. Audit log. Protocol versions table. | Layer 1 + 5 (reference) | Manual observation. Baseline data. |
| Phase 1 | Session mgmt. Work items. Hook injection. | + Layer 2 + 3 | Automated checks. Protocol version tracking. |
| Phase 2 | Sub-agent orchestration. BPMN enforcement (SpiffWorkflow). | + Layer 4 + 5 | + BPMN gates. + Haiku judge. + Session length correlation. |
| Phase 3 | Compliance dashboard. Automated summaries. Cross-version comparison. | All 5 operational | Full summaries. Monthly human review. Evidence-based evolution. |

## Open Decisions

| # | Decision | Recommendation | Blocking? |
|---|----------|---------------|-----------|
| 1 | CLAUDE.md reinjection frequency | Every 15 interactions. Measure and adjust. | No — tunable |
| 2 | Who can modify protocols? | Human only. Agent can propose, not activate. | Yes — safeguard |
| 3 | Haiku judge sampling rate | 10% initially. Increase if issues found. | No — adjustable |
| 4 | Native vs custom tasks | Try native persistent tasks. Revert if no improvement after 4 weeks. | No — experiment |
| 5 | Compliance dashboard priority | Phase 3. Collect data from Phase 0-2 first. | No |

## References

- Rath, A. (2026). Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems. arXiv:2601.04170.
- Zhao et al. (2025). "Less is More": Reducing Cognitive Load and Task Drift.
- Arike et al. (2025). Long-term robustness and adversarial pressures on LLM agent behaviour.
- IMDA Singapore (2025). Model AI Governance Framework for Agentic AI.
- Claude Family Core Protocol v6 (2025-2026). Internal.

---
*Source: Orchestration Chat #8 session (Feb 23, 2026) | Companion doc: nimbus_agent_compliance_drift_management.docx*
