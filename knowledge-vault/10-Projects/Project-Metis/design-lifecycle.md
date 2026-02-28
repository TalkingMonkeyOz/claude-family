---
tags:
  - project/Project-Metis
  - scope/system
  - type/process
created: 2026-02-28
updated: 2026-02-28
---

# METIS Design Lifecycle — Where We Are

This is the master checklist for the design phase of Project METIS. Every session should check this file to understand where we are in the process and what comes next.

## Phases

| # | Phase | Status | Notes |
|---|-------|--------|-------|
| 1 | **First-pass brainstorm** — all 9 areas | ✅ DONE | All areas BRAINSTORM-COMPLETE as of Feb 24 |
| 2 | **Feature catalogue** — 10 user-facing features | ✅ DONE | Validated by John, Feb 28. Vault: feature-catalogue.md |
| 3 | **Gap review** — identify missing pieces | ✅ DONE | 9 resolved (FB148-156), 1 open: GAP-17 PM lifecycle (FB157) |
| 4 | **Remaining topic sessions** — deepen unfinished areas | ○ NOT STARTED | Chat 8a: Session Memory (unvalidated monologue). Chat 8b: Context Assembly (not started). GAP-17: PM lifecycle design (FB157, not started). |
| 5 | **Second-pass iteration** — deepen thin areas | ○ NOT STARTED | Project Governance, Support & Defect Intel, Commercial model for The System (not nimbus). These have README-level brainstorm only. |
| 6 | **Consolidation** — cross-area alignment | ○ NOT STARTED | Resolve contradictions, ensure coherent story across all 9 areas. |
| 7 | **Plan of attack** — validate/rewrite build sequence | ○ DRAFT EXISTS | Vault: plan-of-attack.md (Feb 26 monologue, unvalidated). Validate AFTER design is solid, not before. |
| 8 | **Presentable plan** — stakeholder document | ○ NOT STARTED | Management-ready. Covers nimbus pitch, Monash go-ahead, commercial model. |
| 9 | **Detailed design** — DB schema, component specs | ○ NOT STARTED | Likely 40-60 tables. Multi-session effort. API contracts, data flows. |
| 10 | **BPMN validation** — Claude Code Console | ○ NOT STARTED | Pass consolidated design to Claude Code to model processes and validate. Needs to be in good state first. |
| 11 | **PID / build handoff** — formal initiation | ○ NOT STARTED | Project Initiation Document. Build sequencing for Claude Code execution. |

## Rules

- Each phase should be substantially complete before moving to the next
- Phases 4 and 5 can run in parallel (both are deepening work)
- Phase 7 (plan of attack) comes AFTER consolidation — the build plan reflects the finished design, not the other way around
- Phase 10 (BPMN validation) is the quality gate before committing to build
- Every session should read this file at start and update it if phase status changes

## Current Position

**We are at Phase 4.** First pass, feature catalogue, and gap review are done. Next work is remaining topic sessions (GAP-17 PM lifecycle, Chat 8a session memory, Chat 8b context assembly) and second-pass iteration of thin areas.

---
*Created: 2026-02-28 | Updated: 2026-02-28 — Reordered: plan of attack moved after consolidation (Phase 7). Build plan should reflect finished design.*
