---
tags:
  - project/Project-Metis
  - scope/system
  - type/tracker
created: 2026-02-27
updated: 2026-03-07
---

# GAP Tracker

Gaps are tracked in project-tools DB as feedback items. This file is a lightweight index.

## Resolved (in gap-resolution-summary.md)

| GAP | Title | Status | DB Ref |
|-----|-------|--------|--------|
| GAP-1 | Knowledge Graph Relationships | ✅ RESOLVED Feb 25 | — |
| GAP-2 | Integration Hub Connector Interface | ✅ RESOLVED Feb 25 | — |
| GAP-3 | Session Memory | ⏸️ PARKED (Claude Code building) | — |
| GAP-4 | Evaluation Framework | ✅ RESOLVED Feb 26 | — |
| GAP-5 | Chunking Strategy | ✅ RESOLVED Feb 26 | — |
| GAP-7 | BPMN for MVP | ✅ RESOLVED Feb 26 | — |
| GAP-9 | Background Job Scheduling | ✅ RESOLVED Feb 26 | — |

## Resolved via DB (Feb 26-27 sessions)

| GAP | Title | Resolution | DB Code |
|-----|-------|------------|---------|
| GAP-6 | Knowledge Staleness Detection | ✅ RESOLVED — Event-driven dependency tracking, not time-based | FB148 |
| GAP-8 | Two-Way Sync Conflict Resolution | ✅ RESOLVED — Intelligent triage layer, not dumb field sync | FB149 |
| GAP-10 | External Rule/Change Discovery | ✅ RESOLVED — 4 signal sources: code changes, API monitoring, manual triggers, scheduled scans | FB150 |
| GAP-11 | Commercial Model for The System | ⏸️ PARKED with direction — Monthly subscription, detail deferred to customer #2 | FB151 |
| GAP-12 | Multi-Product Customers | ✅ RESOLVED — Scope hierarchy: Org → Product → Client → Engagement | FB152 |
| GAP-13 | Customer Scenario Replication | ✅ RESOLVED — AI-assisted investigation flow, not just env cloning | FB153 |
| GAP-14 | Generic Integration Catalogue | ✅ RESOLVED — Common services data layer with integration categories | FB154 |
| GAP-15 | Dog-Fooding Loop Formalisation | ✅ RESOLVED — Platform uses itself, same supervised pattern | FB155 |
| GAP-16 | Client-Facing Self-Service Portal | ✅ RESOLVED — Future-phase, groundwork in scope hierarchy + constrained deployment | FB156 |

## Cross-Area (resolved, in gap-resolution-summary.md)

CROSS-1 through CROSS-4 all ✅ RESOLVED.

## Open

| GAP | Title | Status | DB Code | Notes |
|-----|-------|--------|---------|-------|
| GAP-17 | PM Lifecycle & Client Timelines | ◐ FIRST PASS | FB157 | Vault: project-governance/pm-lifecycle-client-timelines.md. Covers issue threads, timeline intelligence, proactive PM alerts, plan vs reality, cross-workstream view. Will cycle back for deeper design. |

## BPMN Model Gaps (Resolved 2026-03-07)

20 gaps across 3 lifecycle BPMN files identified and resolved via BPMN model update + test additions.

### Task Lifecycle (task_lifecycle.bpmn) — 7 gaps

| BPMN-GAP | Title | Status | Resolution |
|----------|-------|--------|------------|
| BPMN-TL-1 | Multi-task support | ✅ RESOLVED 2026-03-07 | Added `has_more_tasks_gw` gateway + loop back to `create_task` |
| BPMN-TL-2 | Build_task bridging | ✅ RESOLVED 2026-03-07 | Added `bridge_to_build_task` scriptTask `[HOOK] Bridge to Build Task` after `sync_to_db` |
| BPMN-TL-3 | Feature completion cascade | ✅ RESOLVED 2026-03-07 | Added `check_feature_completion` scriptTask `[DB]` after `mark_completed` |
| BPMN-TL-4 | Phantom blocker loop | ✅ RESOLVED 2026-03-07 | `resolve_blocker` now flows directly to `mark_completed` (resolve = done, not retry) |
| BPMN-TL-5 | Session scoping detail | ✅ RESOLVED 2026-03-07 | Renamed `check_staleness` to `[HOOK] Check Session Staleness (session_id match)` |
| BPMN-TL-6 | Discipline gate detail | ✅ RESOLVED 2026-03-07 | Renamed `mark_gate_blocked` to `[HOOK] Discipline Gate (Write/Edit/Bash/Task blocked)` |
| BPMN-TL-7 | Midway update path | ✅ RESOLVED 2026-03-07 | Added `midway_status_update` scriptTask `[CLAUDE]` + `flow_outcome_update` path in `outcome_gw` |

### Session Lifecycle (session_lifecycle.bpmn) — 7 gaps

| BPMN-GAP | Title | Status | Resolution |
|----------|-------|--------|------------|
| BPMN-SL-1 | Per-prompt RAG cycle | ✅ RESOLVED 2026-03-07 | Added `rag_per_prompt` scriptTask `[HOOK]` on path from `work_merge_gateway` to `do_work` |
| BPMN-SL-2 | Auto-archive on startup | ✅ RESOLVED 2026-03-07 | Added `auto_archive` scriptTask `[HOOK] Auto-Archive Old Sessions (>24h)` before `session_start` |
| BPMN-SL-3 | Message checking | ✅ RESOLVED 2026-03-07 | Added `check_messages` scriptTask `[MCP]` between `session_start` and `load_state` |
| BPMN-SL-4 | Precompact detail | ✅ RESOLVED 2026-03-07 | Renamed `save_checkpoint` to `[HOOK] PreCompact: Inject Todos + Features + Facts + Notes` |
| BPMN-SL-5 | Hook chain in do_work | ✅ RESOLVED 2026-03-07 | Added `bpmn:documentation` on `do_work` listing PreToolUse/PostToolUse hook chain |
| BPMN-SL-6 | Dual end paths | ✅ RESOLVED 2026-03-07 | Added `auto_close_session` scriptTask `[HOOK]` + `end_auto` endEvent; `work_action_gateway` gets `action=="auto_close"` condition |
| BPMN-SL-7 | do_work detail | ✅ RESOLVED 2026-03-07 | Enriched `do_work` documentation with full per-prompt hook chain description |

### Feature Workflow (feature_workflow.bpmn) — 6 gaps

| BPMN-GAP | Title | Status | Resolution |
|----------|-------|--------|------------|
| BPMN-FW-1 | Task creation step | ✅ RESOLVED 2026-03-07 | Added `create_build_tasks` userTask `[CLAUDE]` between `set_planned` and `complexity_gateway` |
| BPMN-FW-2 | Set in_progress | ✅ RESOLVED 2026-03-07 | Added `set_in_progress` scriptTask `[DB]` after `create_build_tasks` |
| BPMN-FW-3 | Per-task work loop | ✅ RESOLVED 2026-03-07 | Added `next_task_gw` → `start_task` → `implement_task` → `complete_task` → loop; `implement_directly` enters the loop |
| BPMN-FW-4 | Testing enforcement note | ✅ RESOLVED 2026-03-07 | Added `bpmn:documentation` on `run_tests`: "SHOULD BE ENFORCED: Currently optional in practice..." |
| BPMN-FW-5 | Review enforcement note | ✅ RESOLVED 2026-03-07 | Added `bpmn:documentation` on `review_code`: "SHOULD BE ENFORCED: Spawn reviewer-sonnet agent..." |
| BPMN-FW-6 | plan_data annotation | ✅ RESOLVED 2026-03-07 | Added `bpmn:documentation` on `plan_feature` describing plan_data JSONB structure |

---
*Source of truth for open gaps: project-tools DB. This file is an index only.*
