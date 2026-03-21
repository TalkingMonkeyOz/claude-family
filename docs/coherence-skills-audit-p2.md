# Skills Coherence Audit — Part 2: Low Priority & Skills List

Part 1 (summary + HIGH/MEDIUM): [coherence-skills-audit.md](coherence-skills-audit.md)

---

## LOW Priority

### L1 — `check-compliance` audit checks for "process router configured" — process router was retired

**Skill**: `check-compliance/SKILL.md` line 53
**Claim**: Standards audit checks "Standards docs exist, process router configured"
**Reality**: Process router was retired 2026-03-15 (replaced by skills system per ADR-005). A compliance check flagging "process router not configured" as a failure would be incorrect.

---

### L2 — `agentic-orchestration` uses `general-purpose` agent in example but it's not in the quick-reference table or agents directory

**Skill**: `agentic-orchestration/SKILL.md` line 97
**Issue**: Model Override example uses `subagent_type="general-purpose"` but this agent is absent from the quick-reference table (lines 36-46) and from `.claude/agents/*.md`. Attempting to spawn it may produce an error.

---

### L3 — `coding-intelligence` skill has no YAML frontmatter

**Skill**: `coding-intelligence/SKILL.md`
**Issue**: Every other skill has YAML frontmatter (name, description, model, allowed-tools). This skill starts directly with `# Coding Intelligence` — no frontmatter block. Cannot be loaded by the skills system via name matching. (Newly created, untracked in git — may be intentional but should be flagged.)

---

### L4 — `session-save` uses invalid `memory_type` "solution" (already reported as M1) — also affects `remember()` quality gate

**Note**: Covered under M1. Listing here only to note the quality gate in `remember()` would not reject "solution" silently — it would accept it as an unrecognized type routed to the default tier. Not a hard failure but produces miscategorized memories.

---

### L5 — `retrofit-project` references `claude.v_project_governance` view — existence unverified by any other skill or rule

**Skill**: `retrofit-project/SKILL.md` line 33
**Claim**: `SELECT ... FROM claude.v_project_governance WHERE ...`
**Note**: No other skill, rule, or MEMORY.md reference confirms this view exists. If absent, the skill silently fails at step 2.

---

### L6 — `doc-keeper` glob pattern uses `skill.md` (lowercase) but all files are `SKILL.md` (uppercase)

**Skill**: `doc-keeper/SKILL.md` line 56
**Claim**: `Glob(".claude/skills/*/skill.md")`
**Reality**: All 33 skill files use `SKILL.md` (uppercase). Works on Windows (case-insensitive) but would fail on Linux/CI with case-sensitive filesystems.

---

## Skills Checked (33 total)

| # | Skill | Status |
|---|-------|--------|
| 1 | agentic-orchestration | H1, L2 |
| 2 | bpmn-modeling | H3 |
| 3 | check-compliance | L1 |
| 4 | code-review | Clean |
| 5 | coding-intelligence | L3 |
| 6 | database | M6 |
| 7 | doc-keeper | M5, L6 |
| 8 | doc-lifecycle | Clean |
| 9 | feature-workflow | H2, M7 |
| 10 | feedback | H2 |
| 11 | ideate | Clean |
| 12 | knowledge-capture | Clean |
| 13 | maintenance | Clean |
| 14 | messaging | Clean |
| 15 | phase-advance | M2 |
| 16 | planner | Clean |
| 17 | project-ops | M2, M4 |
| 18 | react-expert | Clean |
| 19 | retrofit-project | L5 |
| 20 | review-data | Clean |
| 21 | review-docs | Clean |
| 22 | sa-plan | H4 |
| 23 | self-test | Clean |
| 24 | session-commit | Clean |
| 25 | session-management | M8 |
| 26 | session-save | M1 |
| 27 | session-status | Clean |
| 28 | sql-optimization | Clean |
| 29 | testing | Clean |
| 30 | todo | Clean |
| 31 | winforms | Clean |
| 32 | wpf-ui | Not read (file too large) |
| 33 | work-item-routing | H2, M3 |

---

**Version**: 1.0
**Created**: 2026-03-21
**Updated**: 2026-03-21
**Location**: docs/coherence-skills-audit-p2.md
