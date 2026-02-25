---
tags:
  - project/Project-Metis
  - area/quality-compliance
  - scope/system
  - level/2
  - phase/2
  - phase/3
projects:
  - Project-Metis
created: 2026-02-24
updated: 2026-02-24
synced: false
---

# Quality & Compliance — Brainstorm (Area 4)

> **Scope:** system — generic quality feedback loop, not tied to any specific customer product
>
> **Design Principles:**
> - Quality is a continuous feedback loop, not a phase or a gate
> - BPMN process maps are the primary source for test generation and impact analysis
> - Testing capabilities are tools within the loop, not the whole area
> - Background AI agents do focused analysis jobs on schedule or trigger — not human dashboard reviews
> - Generic configuration validation — Award/pay rules are one customer's example, not the design target

## Area 4 Is: The Quality Conscience of the Platform

Not just a testing engine. It's the quality feedback loop that asks "are things right?" from multiple angles:

1. **Are we following our own procedures?** Internal compliance — agents following BPMN gates, deliverables through proper sign-off, doing what we said we'd do.
2. **Are we testing properly?** Meta-quality — test coverage, test quality, generating the right scenarios.
3. **Is there customer feedback clustering?** Pattern detection — multiple customers reporting similar issues, systemic signals.
4. **Did something change that needs re-validation?** Change-triggered regression — product update, config change, external rule change.

## Three Testing Capabilities

### Capability A: Configuration Validation Engine (CORE)
- Customer configures their product → system validates configurations produce correct outcomes
- Scenario generation from BPMN process maps + configuration knowledge
- Expected vs actual outcome comparison via API
- Examples: Award rules → pay outcomes (nimbus), pricing rules → invoice calculations (generic), scheduling rules → roster outputs (generic)
- Test suites generated from BPMN use cases and code — not hand-written

### Capability B: UI Validation
- Playwright is one test runner — system is open to others including Claude agents running tests directly
- Validates workflows work end-to-end through the UI
- Captures results and feeds back to development cycle
- Complementary to Capability A — different mechanics (browser automation vs API)

### Capability C: Customer Scenario Replication (NICE TO HAVE — LATER)
- Customer provides real-world expected outcomes (e.g., pay scenarios)
- System replicates the scenario configuration and validates output matches
- Mix of standard and config-dependent edge cases
- **Not core. Note for later fleshing out.**

### Regression Mode (applies to both A and B)
- Triggered by change to a specific rule, configuration, or product update
- The hard problem: knowing WHAT ELSE to test when you change one thing
- **BPMN is the answer** — if processes are fully mapped, system traces which features/modules a change touches and generates regression scope automatically
- Example: change a contract rule → system knows it affects schedule management → generates regression suite covering schedule scenarios with various options on/off
- Significant work, high value — a BPMN cross-referencing problem, not just a testing problem

## BPMN as Test Generation Source — KEY DESIGN POINT

This is the differentiator. BPMN isn't just enforcement gates (Area 9). It's:

1. **The workflow engine** — drives what happens, in what order, with what gates
2. **The analysis engine** — understands what touches what, traces impact, identifies regression scope
3. **The test generation source** — if you know the process, you can generate tests from it
4. **The documentation source** — process maps ARE the documentation

Quality of testing is directly proportional to quality of BPMN process mapping. This makes Area 9 a critical dependency — not just a cross-cutting concern.

> **Validated by Claude Family experience:** BPMN gap analysis (FB130-FB147) found 20+ gaps, 14 resolved. Biggest wins: FB126 (tool designed but never built — BPMN found it), FB141 (silent bug in RAG hook), FB130 (zombie task detection leading to subsystem rewrite). FB147 (automate BPMN alignment checks proactively) is exactly this regression/impact analysis capability.

## Implementation Model: Background Agent Jobs

Not a human dashboard. Focused AI agent tasks, scheduled or event-triggered:

- **Something deployed** → agent runs regression analysis
- **Customer feedback arrives** → agent checks for pattern matches against recent changes
- **Daily sweep** → agent checks open work items following proper lifecycle gates
- **Weekly** → agent reviews test coverage against BPMN process maps, flags gaps
- **External rule change detected** → agent identifies affected configurations, queues re-validation

Each is a small focused job using constrained deployment pattern — narrow scope, specific knowledge, specific tools. Run, report findings (as work items, alerts, or knowledge), stop.

## Relationship to Other Areas

- **Area 4 owns:** "something changed or might be wrong → what's affected → validate → flag failures" (proactive)
- **Area 5 owns:** "something broke → triage → diagnose → resolve → learn" (reactive)
- **Area 5 feeds Area 4** with customer signals and pattern data
- **Area 4 feeds Area 5** with "go check these things"
- **Area 9 (BPMN) is critical dependency** — test generation quality = process mapping quality
- **Area 1 (Knowledge Engine)** provides the knowledge for scenario generation (Category A product + Category B compliance + Category E engagement)
- **Area 3 (Delivery Accelerator)** invokes testing capabilities at pipeline gates

## Decisions Made This Session

1. **Three testing capabilities:** Configuration Validation (core), UI Validation (complementary), Customer Scenario Replication (nice-to-have, later)
2. **Regression is a mode, not a separate engine** — applies to both config validation and UI validation
3. **BPMN as test generation source** — tests generated from process maps and code, not hand-written
4. **BPMN elevated beyond enforcement** — analysis layer, test generation, impact tracing, documentation source. Second brain alongside Knowledge Engine.
5. **Area 4 is the quality feedback loop** — not just testing. Internal compliance, test quality, customer signal clustering, change-triggered re-validation.
6. **Background agent jobs** — scheduled/triggered AI tasks doing focused analysis, not interactive sessions.
7. **Generic framing** — configuration validation engine. Customer-specific rules (Award, pricing, scheduling) are examples, not design targets.
8. **Compliance monitoring lives in Area 4** — proactive validation. Area 5 handles reactive resolution.

## Open Questions / Gaps

- [ ] How does the platform discover external rule changes? (e.g., Award legislation changes, product updates from vendor) — ingestion trigger design
- [ ] Test coverage metrics — what's "good enough" BPMN mapping before test generation is reliable?
- [ ] Customer Scenario Replication — flesh out later, not core
- [ ] Specific BPMN-to-test-case generation logic — belongs in Area 9 deep dive or here?

---
*Source: Area 2-5 sweep session, Feb 24 2026 | Builds on: Doc 1 §3.1, Doc 2 §2.3, Doc 4 WS5, Claude Family FB130-FB147*
