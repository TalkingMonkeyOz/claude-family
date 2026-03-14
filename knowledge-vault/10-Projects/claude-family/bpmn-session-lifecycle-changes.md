---
projects:
  - claude-family
tags:
  - bpmn
  - session-lifecycle
  - design
  - session-end
  - session-resume
---

# BPMN Change Spec: session_lifecycle.bpmn

**File to modify**: `mcp-servers/bpmn-engine/processes/lifecycle/session_lifecycle.bpmn`
**Process ID**: `session_lifecycle`
**Reason**: Session-end does not stash task state for handoff; session-resume does not display next_steps or active dossiers.

---

## Current Model Gaps

**Session End** — `work_action_gateway` → `save_summary` (single task) → `close_session` → `end_normal`
- `save_summary` has no substeps: task state is lost, no handoff stash is created, learnings are not extracted

**Session Resume** (prior_state branch) — `display_session_summary` → `has_prior_tasks_gateway` → merge
- `display_session_summary` does not read `session_state.next_steps`
- No step queries or displays active workfile dossiers

---

## Change 1: Expand `save_summary` into a four-step chain

Replace the single `save_summary` scriptTask with this sequence:

```
save_summary_and_state
    → query_unfinished_tasks
        → stash_session_handoff
            → extract_and_store_learnings
                → close_session  (existing, unchanged)
```

### New Task Definitions

**`save_summary_and_state`** [MCP]
Saves session summary and next_steps to `claude.sessions` + UPSERTs `claude.session_state`.
Replaces prior `save_summary` behaviour. This is step 1 in the existing `/session-end` flow.

**`query_unfinished_tasks`** [MCP]
Queries `claude.todos` for this session where `status IN ('todo', 'in_progress')`.
Also reads current `session_facts` for decisions made this session.
Stores results in process variable `unfinished_tasks`.

**`stash_session_handoff`** [MCP]
Calls `stash(component="session-handoff", title="<YYYY-MM-DD> handoff", content=...)`.
Content bundles: unfinished task list + key decisions from session_facts + next_steps from session_state.
Enables the next Claude to run `unstash("session-handoff")` and see exactly where work stopped.

**`extract_and_store_learnings`** [MCP]
Calls `remember()` for each significant pattern/decision from the session.
Calls `consolidate_memories(trigger="session_end")` to promote short→mid tier memories.

### Sequence Flow Changes

| Action | Flow ID |
|--------|---------|
| Remove | `flow_save_summary_to_close` |
| Add | `flow_save_state_to_query_tasks`: `save_summary_and_state` → `query_unfinished_tasks` |
| Add | `flow_query_tasks_to_stash`: `query_unfinished_tasks` → `stash_session_handoff` |
| Add | `flow_stash_to_learnings`: `stash_session_handoff` → `extract_and_store_learnings` |
| Add | `flow_learnings_to_close`: `extract_and_store_learnings` → `close_session` |

`flow_end_session` condition on `work_action_gateway` is unchanged — it now targets `save_summary_and_state`.

---

## Change 2: Expand `display_session_summary` into a three-step chain

Replace the single `display_session_summary` scriptTask with this sequence:

```
display_summary_and_next_steps
    → query_active_dossiers
        → display_active_dossiers
            → has_prior_tasks_gateway  (existing, unchanged)
```

### New Task Definitions

**`display_summary_and_next_steps`** [MCP]
Reads `session_state.next_steps` and renders "NEXT PRIORITIES" section in the resume output.
Bug fix: the previous `display_session_summary` showed the session summary but omitted `next_steps`.

**`query_active_dossiers`** [MCP]
Calls `list_workfiles()` for this project.
Stores result in process variable `active_dossiers`.

**`display_active_dossiers`** [MCP]
Renders "ACTIVE DOSSIERS" section if `active_dossiers` is non-empty.
Shows per dossier: component name, file count, pinned status, last-accessed date.
Tells Claude which `unstash(component)` calls will load useful context.

### Sequence Flow Changes

| Action | Flow ID |
|--------|---------|
| Remove | `flow_summary_to_tasks_gw` |
| Add | `flow_summary_to_query_dossiers`: `display_summary_and_next_steps` → `query_active_dossiers` |
| Add | `flow_query_dossiers_to_display`: `query_active_dossiers` → `display_active_dossiers` |
| Add | `flow_dossiers_to_tasks_gw`: `display_active_dossiers` → `has_prior_tasks_gateway` |

`flow_restore_context` condition on `has_prior_state_gateway` is unchanged — it now targets `display_summary_and_next_steps`.

---

## Process Header Comment Update

Update path descriptions in the XML comment block:

```
2. Resumed session: ... → has_prior_state(True)
   → display_summary_and_next_steps → query_active_dossiers
   → display_active_dossiers → has_prior_tasks → ... → work_merge → do_work
3. Session end: do_work → action(end_session)
   → save_summary_and_state → query_unfinished_tasks
   → stash_session_handoff → extract_and_store_learnings
   → close_session → end_normal
```

---

## Diagram Layout Notes

Current layout: main flow at y=200, resume sub-flow at y=60-100 (above), compact/fresh-start at y=340-380 (below).

**Session-end expansion**: Insert three new tasks between `save_summary_and_state` (x=2010) and `close_session`. Shift `close_session` to approximately x=2450, `end_normal` to x=2610. New tasks at x=2130, 2250, 2340 (y=180).

**Resume expansion**: Insert `query_active_dossiers` and `display_active_dossiers` between `display_summary_and_next_steps` and `has_prior_tasks_gateway` in the y=60 row. Shift `has_prior_tasks_gateway` and downstream shapes right to accommodate.

---

## Required Tests (Write Before Implementing)

| Test | Precondition | Assert |
|------|-------------|--------|
| `test_session_end_stashes_handoff` | Session ends with open tasks | `stash_session_handoff` present in completed path |
| `test_session_end_no_tasks` | Session ends with no open tasks | `stash_session_handoff` still runs (empty task list) |
| `test_resume_displays_next_steps` | Prior session saved next_steps | `display_summary_and_next_steps` precedes `has_prior_tasks_gateway` |
| `test_resume_queries_dossiers` | Resume path taken | `query_active_dossiers` runs after `display_summary_and_next_steps` |
| `test_resume_no_dossiers` | `list_workfiles` returns empty | `display_active_dossiers` runs without error |
| `test_session_end_full_chain` | Normal session end | All four tasks complete in declared order |

---

**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: knowledge-vault/10-Projects/claude-family/bpmn-session-lifecycle-changes.md
