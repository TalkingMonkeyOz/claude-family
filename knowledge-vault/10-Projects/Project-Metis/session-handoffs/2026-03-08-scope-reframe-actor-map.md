---
tags:
  - project/Project-Metis
  - type/session-handoff
  - phase/gate-one
created: 2026-03-08
session: post-gate-zero-scope-reframe-actor-map
status: complete
supersedes: 2026-03-08-gate-zero-complete.md
---

# Session Handoff: Scope Reframe + Plan Validation + Actor Map

## Session Summary

Three major deliverables completed. System product definition reframed for domain-agnostic scope. Plan-of-attack walked through and validated — rewrite brief written for doc consolidator. Actor Map (Gate 1 Doc 2) written with full agent architecture validated against industry research.

---

## WHAT WAS DONE

### 1. system-product-definition.md updated to v0.3
- **Section 1 reframed:** "Enterprise AI platform that learns what your organisation does." Humans produce artifacts (configs, design docs, test scenarios, code, deployment docs). AI dramatically speeds up the cycle. Augmentation Layer mentioned as enabler, not headline.
- **Section 2 reframed:** "Knowledge-intensive organisations" as primary target. Dev houses as lead example (nimbus proves it there first). Also fits PS firms, consulting, healthcare, legal, financial services.
- **Section 3 reframed:** Opening line + fifth problem heading. "AI tools don't understand your domain."
- **Section 7.3:** Multi-tenant table: "development house" → "company" / "organisation"
- **Subtitle** updated. Version bumped to v0.3.

### 2. plan-of-attack.md walkthrough — VALIDATED
8 decisions captured. Rewrite brief written to `plan-of-attack-rewrite-brief.md` for doc consolidator handoff.

Key decisions:
1. **Build from zero** — Claude Family is knowledge gained, not codebase. METIS is purpose-built.
2. **Use area-level features F119-F128** as structure. Old F1-F10 numbering retired.
3. **Augmentation Layer is core Phase 1** — must help build itself (dog-fooding).
4. **Phase 2 is streams, not monolith** — one end-to-end workflow at a time (e.g. assisted defect tracking with Jira), not "build all nimbus at once."
5. **Generic framing** with nimbus as lead example.
6. **Infrastructure platform-agnostic** — no Azure specificity.
7. **MVP = one stream working end-to-end**, not the whole pipeline.
8. **Separate system blockers from customer blockers.**

### 3. Actor Map (Gate 1 Doc 2) — COMPLETE
Written to `gate-one/actor-map.md`. Design lifecycle updated.

**6 Human Actors:**
- Platform Builder, Enterprise Admin, PS Consultant, Support Staff, Developer, End Customer (indirect)
- Enterprise Staff deliberately split into 3 (PS/Support/Dev) — different interaction patterns
- Additional roles (Sales, Marketing) identified but deferred

**3 AI Agent Categories (confirmed by industry research):**
- **Category A — Project Agents:** Controller → Supervisors (3-4 sub-agents each) → Specialists (design, analysis, BPMN, test, coder, documentation). Not a fixed list — grows over time.
- **Category B — Event-Driven Agents:** Document Scanner, Knowledge Ingestion, Notification. Triggered by events, isolated, do job and finish.
- **Category C — System-Level Agents:** Master AI (run sheet), Health Monitor, Knowledge Quality. Persistent/scheduled.

**Agent architecture confirmed:** Hub-and-spoke / supervisor pattern. Specialised agents, not one general agent. 3-layer context hierarchy (global standards → project context → agent purpose). Parallel work is a decomposition problem, not a technology problem — break elephant into pieces, track pieces. Augmentation Layer handles work awareness and tracking. Multi-agent cost (multiplied API calls) must feed into commercial model.

---

## KEY DECISIONS THIS SESSION

| Decision | Detail |
|---|---|
| Scope breadth: MEDIUM | Knowledge-intensive organisations, dev houses as lead example |
| Section 1 framing | Humans produce artifacts, AI accelerates, Augmentation Layer is enabler |
| Build from zero | Claude Family = knowledge, not codebase |
| Features structure | F119-F128 (areas), retire F1-F10 |
| Augmentation Layer Phase 1 | Core, must dog-food |
| Streams not monolith | One end-to-end workflow per phase |
| Agent architecture | Specialised agents with controller (supervisor pattern) |
| Agent categories | 3 categories: project, event-driven, system-level |
| Human actors split | Enterprise Staff → PS Consultant, Support Staff, Developer |
| Parallel work | Decomposition problem, Augmentation Layer concern |

---

## WHAT'S NEXT — PRIORITISED

### 1. Plan-of-attack rewrite
Hand `plan-of-attack-rewrite-brief.md` to doc consolidator (Claude Code). Produce the actual rewritten plan document using validated decisions.

### 2. Security conversation
Flagged gap from Gate Zero Doc 2 (assumptions/constraints). Data isolation, auth model, agent security boundaries. Not yet discussed.

### 3. Remaining Gate 1 documents
- Process Inventory (Doc 1) — scattered across 9 areas, needs formal consolidation
- Data Entity Map (Doc 3) — scattered, needs consolidation
- Business Rules Inventory (Doc 4) — scattered, needs consolidation
- Integration Points (Doc 5) — partial, needs detail

### 4. Still open from prior sessions
- Follow up on msg 67d8af18 (vault sync to claude-family)
- Toolkit Categories 2-4
- Validate unvalidated February vault output conversationally

---

## KEY FILES

| File | Status |
|---|---|
| `system-product-definition.md` | v0.3 — scope reframe DONE |
| `plan-of-attack-rewrite-brief.md` | NEW — validated brief for doc consolidator |
| `plan-of-attack.md` | SUPERSEDED by rewrite brief (keep as reference) |
| `gate-one/actor-map.md` | NEW — Gate 1 Doc 2 VALIDATED |
| `design-lifecycle.md` | UPDATED — Actor Map marked complete |
| `session-handoffs/2026-03-08-gate-zero-complete.md` | SUPERSEDED by this handoff |

---

## SESSION STARTER FOR NEXT CHAT

```
METIS Session Starter — Post Actor Map
READ FIRST: `session-handoffs/2026-03-08-scope-reframe-actor-map.md`

CONTEXT: Gate Zero COMPLETE. Gate 1 Doc 2 (Actor Map) COMPLETE.
system-product-definition.md updated to v0.3 (domain-agnostic).
Plan-of-attack validated — rewrite brief ready for doc consolidator.

PRIORITY: Either hand plan rewrite brief to Claude Code,
or continue with security conversation (Gate Zero gap).

AFTER THAT:
1. Remaining Gate 1 docs (Process Inventory, Data Entity Map,
   Business Rules, Integration Points — all scattered, need consolidation)
2. Follow up on msg 67d8af18 (vault sync to claude-family)

KEY FILES:
* session-handoffs/2026-03-08-scope-reframe-actor-map.md
* system-product-definition.md (v0.3)
* plan-of-attack-rewrite-brief.md (NEW — for doc consolidator)
* gate-one/actor-map.md (NEW — validated)
* design-lifecycle.md (Actor Map marked complete)
* gate-zero/ — all 5 docs complete
* research/augmentation-layer-research.md
```

---
*Session: 2026-03-08 | Status: 3 deliverables complete. Gate 1 progressing. Next: plan rewrite handoff + security conversation.*
