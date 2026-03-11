---
tags:
  - project/Project-Metis
  - type/session-handoff
  - phase/gate-zero
created: 2026-03-07
session: gate-zero-docs-and-skill
status: complete
supersedes: 2026-03-07-doc-review-complete.md
---

# Session Handoff: Gate Framework Skill + Gate Zero Docs 1-3

## Session Summary

Two-part session:
1. **Gate framework skill (FB174)** — written and installed as user skill in Claude Desktop
2. **Gate Zero documents 1-3** — Problem Statement, Assumptions & Constraints, Stakeholders & Decision Rights — all validated and written to vault

Major scope reframe this session: METIS is domain-agnostic at its core. Not just for development houses. Skills shape the slant per enterprise type.

---

## WHAT WAS DONE

### Gate Framework Skill (FB174)
- Written to `skills/gate-framework/SKILL.md` (~230 lines)
- Covers: 5 gates with default deliverables, customisation mechanism, iterative methodology, anti-monologue rule, gate readiness assessment, dual-lens principle, progress tracking
- Explicitly pairs with `project-session-manager` — both reference each other
- Session-manager update patch at `skills/session-manager-update-patch.md`
- **John confirmed both skills installed in Claude Desktop**

### Gate Zero Documents
All in `gate-zero/` folder:

| Doc | File | Status |
|-----|------|--------|
| 1. Problem Statement | `problem-statement.md` | ✅ VALIDATED |
| 2. Assumptions & Constraints | `assumptions-constraints.md` | ✅ VALIDATED |
| 3. Stakeholders & Decision Rights | `stakeholders-decision-rights.md` | ✅ VALIDATED |
| 4. System Map (C4 L1/L2) | NOT STARTED | Next |
| 5. Ethos | `ethos.md` (project root) | ✅ DONE (prior session) |

---

## KEY DECISIONS THIS SESSION

### Scope Reframe (IMPORTANT)
- METIS is domain-agnostic. The core problem is universal: any enterprise wanting enterprise-grade AI needs the AI to deeply understand what that enterprise does
- nimbus is the first target but the platform is not development-specific
- Skills shape the slant per enterprise type (dev house → dev skills, contractor → analysis/design skills, logistics → operations skills)
- `system-product-definition.md` still reflects the older dev-focused framing — needs updating to align

### Skill Structure
- Gate framework and session-manager are SEPARATE complementary skills
- Both explicitly reference each other

### AI Autonomy Model
- Initially ALL decisions go via human
- Over time, AI earns autonomy where it demonstrates very high confidence consistently
- Progressive: system learns which decisions it gets right and can act on those

### nimbus Stakeholders
- Grant Custance (Director) — strategic approval
- Harrison Custance (MD) — operational go/no-go, day-to-day sponsor
- Justin (CFO/COO) — commercial terms, budget
- David (CTO) — technical, infrastructure, security, integration
- Sharon (Chief Customer Manager) — customer-facing impact, support readiness

### Assumptions & Constraints
- 3 assumptions: LLM dependency, domain knowledge required, useful from day one with imperfect knowledge
- 4 constraints: human in loop, one-person build, data isolation/security, cloud hosted
- Security flagged as known gap needing its own conversation

---

## WHAT'S NEXT — PRIORITISED

### 1. Gate Zero Doc 4: System Map (C4 L1/L2)
This is a diagram, not a conversation. Needs to show what exists and what connects at context and container level. May need Mermaid/C4 tooling.

### 2. Update system-product-definition.md
Align with the broader scope reframe (domain-agnostic, skills as slant). Section 2 (Who It's For) and Section 3 (The Problem) need updating.

### 3. Validate plan-of-attack.md conversationally
Still UNVALIDATED from February. Must step through topic by topic.

### 4. Flesh out Actor Map (Gate 1 Doc 2)
Human roles and agent roles need defining.

### 5. Security conversation
Flagged during assumptions/constraints — data isolation and security haven't been formally discussed.

### Still open
- Follow up on msg 67d8af18 (vault sync to claude-family)
- Toolkit Categories 2-4
- Pipelines of work

---

## SESSION STARTER FOR NEXT CHAT

```
METIS Session Starter — Gate Zero Completion
READ FIRST: `session-handoffs/2026-03-07-gate-zero-session.md`

CONTEXT: Gate Zero 4/5 docs done. Major scope reframe: METIS is 
domain-agnostic, skills shape the slant per enterprise type.
Gate framework skill installed.

PRIORITY: Gate Zero Doc 4 — System Map (C4 L1/L2)
This is a diagram showing what exists and what connects.
9 areas already defined. Needs C4 context + container diagrams.

AFTER C4:
1. Update system-product-definition.md with scope reframe
2. Validate plan-of-attack.md conversationally
3. Actor Map (Gate 1 Doc 2)
4. Security conversation

KEY FILES:
* session-handoffs/2026-03-07-gate-zero-session.md
* gate-zero/problem-statement.md — VALIDATED
* gate-zero/assumptions-constraints.md — VALIDATED
* gate-zero/stakeholders-decision-rights.md — VALIDATED
* ethos.md — Gate Zero Doc 5 (DONE)
* design-lifecycle.md — gate progress tracker
* system-product-definition.md — needs scope reframe update
* plan-of-attack.md — UNVALIDATED
```

---

## KEY FILES
- This handoff: `session-handoffs/2026-03-07-gate-zero-session.md`
- Prior handoff: `session-handoffs/2026-03-07-doc-review-complete.md`
- Gate Zero docs: `gate-zero/problem-statement.md`, `gate-zero/assumptions-constraints.md`, `gate-zero/stakeholders-decision-rights.md`
- Ethos: `ethos.md`
- Gate framework skill: `skills/gate-framework/SKILL.md`
- Design lifecycle: `design-lifecycle.md`

---
*Session: 2026-03-07 | Status: Gate Zero 4/5 done, scope reframed, skill installed. Next: C4 System Map.*
