---
tags:
  - project/Project-Metis
  - area/quality-compliance
  - scope/system
  - level/1
  - phase/2
  - phase/3
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-02-24
synced: false
---

# Quality & Compliance

> **Scope:** system (generic platform capability — configuration validation and quality feedback loop, configured per customer)
>
> **Design Principles:**
> - Quality is a continuous feedback loop, not a phase or a gate
> - BPMN process maps are the primary source for test generation and impact analysis
> - AI generates test scenarios from configurations and BPMN maps, not from scratch
> - Expected vs actual outcome comparison is the universal validation pattern
> - The system knows what it doesn't know — flags uncertainty for human review
> - Background AI agents do focused analysis jobs on schedule or trigger
> - Configuration validation is system testing, not legal/regulatory interpretation

**Priority:** MEDIUM — Phase 2-3
**Status:** ✓ FIRST PASS
**Parent:** [[Project-Metis/README|Level 0 Map]]

## What This Area Is

The quality conscience of the platform. A continuous feedback loop asking "are things right?" from four angles:

1. **Internal process compliance** — are we following our own procedures and BPMN gates?
2. **Testing quality** — are we generating the right scenarios, achieving adequate coverage?
3. **Customer signal clustering** — is feedback pointing to systemic issues?
4. **Change-triggered re-validation** — did something change that needs regression?

## Three Testing Capabilities

- **Configuration Validation Engine (CORE)** — customer configures product, system validates outcomes via API. Test suites generated from BPMN + code. Generic: Award rules, pricing rules, scheduling rules all fit the pattern.
- **UI Validation** — Playwright or equivalent. Open to other test runners including Claude agents. End-to-end workflow validation.
- **Customer Scenario Replication (LATER)** — customer provides expected outcomes, system replicates and validates. Nice-to-have, not core.

**Regression** is a mode applied to both, not a separate engine. BPMN process maps drive impact analysis — trace what a change touches, generate regression scope.

## Key Design Decision: BPMN as Test Generation Source

BPMN isn't just enforcement gates. For testing it's:
- Analysis engine — traces what touches what
- Test generation source — knows the process, generates tests from it
- Impact analysis — change one thing, know what to retest

Validated by Claude Family: BPMN gap analysis (FB130-FB147) found 20+ real issues, 14 resolved. See [[quality-compliance/brainstorm-quality-compliance|brainstorm]] for details.

## Implementation: Background Agent Jobs

Not interactive sessions. Scheduled/triggered AI tasks:
- Deployment → regression analysis
- Customer feedback → pattern matching against recent changes
- Daily → lifecycle gate compliance check
- Weekly → test coverage vs BPMN map gap analysis

## Decisions (8 resolved)

1. ✓ Three testing capabilities: Config Validation (core), UI (complementary), Customer Scenario (later)
2. ✓ Regression is a mode, not a separate engine
3. ✓ BPMN as test generation source — tests from process maps and code
4. ✓ BPMN elevated beyond enforcement — analysis + test generation + impact tracing
5. ✓ Area 4 = quality feedback loop, not just testing
6. ✓ Background agent jobs for analysis tasks
7. ✓ Generic framing — customer rules are examples, not design targets
8. ✓ Compliance monitoring lives in Area 4 (proactive). Area 5 handles reactive.

## Dependencies

- **Area 9 (BPMN/SOP)** — CRITICAL. Test generation quality = process mapping quality
- **Area 1 (Knowledge Engine)** — knowledge for scenario generation (Category A/B/E)
- **Area 2 (Integration Hub)** — product API for running scenarios
- **Area 3 (Delivery Accelerator)** — invokes testing at pipeline gates
- **Feeds Area 5** — test failures become defects. Area 5 feeds back customer signals.

## Open Questions

- [ ] How does platform discover external rule changes? (ingestion trigger design)
- [ ] Test coverage metrics — what BPMN mapping quality enables reliable test generation?
- [ ] Customer Scenario Replication — flesh out later
- [ ] BPMN-to-test-case generation logic — Area 9 deep dive or here?

## Deeper Design

- [[quality-compliance/brainstorm-quality-compliance|Brainstorm: Quality & Compliance]]

---
*Source: Doc 1 §3.1, Doc 2 §2.3, Doc 4 WS5, Area 2-5 sweep Feb 24 2026*
