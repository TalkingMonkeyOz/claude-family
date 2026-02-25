---
tags:
  - project/Project-Metis
  - area/orchestration-infra
  - scope/system
  - level/2
  - phase/0
projects:
  - Project-Metis
created: 2026-02-24
synced: false
---

# Agent Conventions — Enforceable Rules

> **Scope:** system
>
> **Design Principles:**
> - Rules must be specific enough to be mechanically checked — "verify before claiming" fails, "read the file before saying it contains X" works
> - Fewer rules, more specific — agents follow 8 clear rules better than 20 vague ones
> - Rules are enforced through the five-layer architecture (see [[orchestration-infra/agent-compliance-drift-management]])
> - Only humans modify rules. Agents propose, humans approve.

**Parent:** [[orchestration-infra/README|Orchestration & Infrastructure]]
**Source:** Doc 4 §5.4 (prose version), agent compliance design, Claude Family experience

---

## The Rules

Eight rules. Every Claude Code agent (including Agent Teams teammates) must follow these. They go into CLAUDE.md and are injected via the core protocol layer.

### Rule 1: DECOMPOSE BEFORE BUILDING

Before writing code, create work items. State what you will build, in what order, and what "done" looks like. Do not start coding until the plan is stated.

**Why:** Prevents agents from diving in without structure. Makes work auditable. Enables compliance measurement (did tasks exist before tool calls?).

**Measurable:** Audit log — was first `work_item.create` timestamp before first code-modifying tool call in the session?

### Rule 2: VERIFY BEFORE CLAIMING

Read the file before saying it contains X. Query the database before saying the table exists. Run the test before saying it passes. Never claim a state you haven't checked.

> Lesson from Claude Family: "Verify before claiming" was too vague. Agents interpreted it loosely. The specific examples (read the file, query the DB, run the test) are what make this enforceable.

**Measurable:** Sample check (Haiku judge) — did the agent reference file contents or DB state without a preceding read/query in the audit log?

### Rule 3: FOLLOW THE CONVENTIONS

Use the naming conventions, data standards, and code patterns defined in CLAUDE.md. If unsure, check CLAUDE.md first. Do not invent new patterns without documenting them in an ADR.

**Why:** Consistency across agents and sessions. New agents can onboard by reading CLAUDE.md.

**Measurable:** Lint pass rate. Naming convention violations in code review.

### Rule 4: TEST EVERYTHING

Every module has tests. Every public function has at least one test. Run tests after every change. If tests fail, fix them before committing.

**Measurable:** CI pipeline — test pass rate, coverage percentage.

### Rule 5: DELEGATE COMPLEX WORK

If a task touches 3+ files across different modules, consider breaking it into smaller tasks or spawning a sub-agent with clean context. Don't accumulate unrelated context.

> Lesson from Claude Family: Sub-agent isolation is the strongest defence against context rot. Fresh context per task beats long sessions every time. Research confirms: two-level hierarchy (router + specialists) is most drift-resistant.

**Measurable:** Session length vs compliance score correlation. Sub-agent spawn rate for multi-file tasks.

### Rule 6: AUDIT EVERYTHING

Every database write gets an audit entry. Every external API call gets logged. Every session start and end is recorded. If it modifies state, it must be traceable.

**Measurable:** Audit coverage — ratio of state-changing operations to audit entries.

### Rule 7: FLAG UNCERTAINTY

If unsure about a requirement, convention, or architecture decision — say so. Check the ADRs. Check the knowledge base. Ask rather than guess. Wrong guesses create rework.

**Why:** Hallucination prevention. The system must know what it doesn't know.

**Measurable:** Haiku judge — did the agent express uncertainty when answering outside its verified knowledge?

### Rule 8: NEVER MODIFY THESE RULES

Rules can only be changed by a human. Agents can PROPOSE changes by documenting them, but cannot activate changes to the rules section of CLAUDE.md without human approval.

> Lesson from Claude Family: Agent self-modification of protocols actively degrades compliance. The agent's natural tendency to compress and simplify rules loses the specificity that makes them enforceable. This is semantic drift — not a bug, a fundamental characteristic to design around.

**Anti-compression safeguard:** If a proposed rule change reduces word count by >10% without adding new specificity, it MUST be flagged for human review.

**Measurable:** Protocol version tracking — word count trends, change frequency, who initiated.

---

## Enforcement Layers

These rules are enforced through five layers (detail in [[orchestration-infra/agent-compliance-drift-management]]):

| Layer | Mechanism | What It Catches |
|-------|-----------|----------------|
| 1. Core Protocol Injection | Rules injected at END of every prompt (recency bias) | Semantic drift — rules fade from attention |
| 2. CLAUDE.md Reinjection | Full conventions reinjected every ~15 interactions | Context rot — rules lost in long sessions |
| 3. Task-Driven Context | Work items persist in DB, read before each task | Behavioral drift — tasks go stale |
| 4. Sub-Agent Isolation | Clean context per complex task | Context pollution — accumulated irrelevant state |
| 5. BPMN Gates | SpiffWorkflow checks at defined checkpoints | All types — mechanical enforcement, not willpower |

---

## Compliance Measurement

Seven metrics tracked (detail in [[orchestration-infra/agent-compliance-drift-management]]):

1. Task creation compliance (Rule 1)
2. Verify-before-claim rate (Rule 2)
3. Task closure rate (hygiene)
4. Session fact usage (memory effectiveness)
5. Sub-agent spawn rate (Rule 5)
6. BPMN gate pass/fail (Rule enforcement)
7. Protocol version correlation (are rule changes improving things?)

Three measurement methods:
- **Automated checks** — every session (cheap, fast, mechanical)
- **Haiku LLM-as-judge** — 10% sample (cheap, catches nuance)
- **Human review** — monthly (evidence-based, not gut feel)

---

## Gap: Rule Prioritisation

What happens when rules conflict? Example: Rule 4 says test everything, but Rule 5 says delegate complex work. If testing requires understanding the full context of a multi-module change, does the agent test locally or delegate the test to a sub-agent?

**Not yet resolved.** Needs a worked example during Phase 1 when agents are actually running. Capture conflicts as they arise.

## Gap: Rule Scope by Agent Role

Should all agents follow all 8 rules equally? Or should specialist agents have modified rules?

Example: A Review Agent (read-only) doesn't need Rule 6 (audit everything) because it doesn't write state. But it very much needs Rule 2 (verify before claiming).

**Brainstorm:**
- Core rules (1, 2, 3, 7, 8) apply to ALL agents
- Operational rules (4, 5, 6) may have role-specific interpretations
- Define per-role rule profiles when agent roles are formally designed

## Gap: Rule Evolution Process

How do we formally propose, test, and adopt rule changes?

**Brainstorm:**
1. Human or agent identifies a rule that isn't working
2. Proposed change documented with: what's wrong, proposed wording, expected impact
3. New protocol version created with `changed_by` and `change_reason`
4. Run both old and new versions in parallel (A/B test) if practical
5. Compare compliance metrics across versions
6. Accept, reject, or iterate

This is the "evidence-based improvement" approach from the compliance design — but the actual process hasn't been spelled out as a workflow yet. Candidate for BPMN validation in the consolidation pass.

---
*Source: Doc 4 §5.4 agent conventions, agent compliance design, Claude Family experience | Created: 2026-02-24*
