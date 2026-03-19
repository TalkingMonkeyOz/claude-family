---
projects:
  - Project-Metis
tags:
  - build-tracking
  - work-breakdown
  - audit-trail
  - governance
  - design
---

# Build Tracking System Design

## Problem Statement

METIS has detailed design documents (Gates 0-2 complete) but zero formal structure for tracking build work. Need: hierarchical work breakdown, dependency ordering (not dates), audit trail, versioned plans, multi-Claude recall, and interface-driven access (no direct SQL).

## Research Summary

### Industry Approaches Evaluated

| Approach | Fit for METIS | Notes |
|----------|--------------|-------|
| WBS (8-80 hour rule) | Good | Tasks should be 1-3 session units — aligns with our Claude session model |
| Event Sourcing (overlay) | Adopted | Append-only event log alongside current-state tables. Perfect audit without full CQRS complexity |
| Shape Up (appetite) | Partial | "Appetite" concept useful — set willingness to invest, not time estimates. No dates. |
| Kanban WIP limits | Adopted | Limit concurrent in_progress items per stream to prevent spread |
| SAFe | Rejected | Over-engineered for our scale, too ceremony-heavy for AI-driven work |
| Full Event Sourcing | Rejected | Breaks existing tooling, unnecessary complexity for project tracking |

### Key Research Sources

- Event sourcing as audit overlay: immutable append-only log as source of truth for state transitions
- Anthropic multi-agent research: typed schemas and structured topology prevent error amplification (17x in unstructured networks)
- GitHub Copilot memory: session-scoped facts + persistent memory + spec files — validates our 5-system storage
- pgMemento: PostgreSQL trigger-based audit trail with schema versioning — inspiration for work_events table
- WBS standard: 100% rule (sum of child work = parent work), 8-80 hour work packages

## Design Decision: Extend Existing + 2 New Tables

### Hierarchy (Using Existing Tables)

```
claude.projects → "project-metis"
  └── claude.features [type='stream'] → "Augmentation Layer", "Knowledge Engine", etc.
        └── claude.features [type='feature', parent=stream] → scoped deliverables
              └── claude.features [type='feature', parent=parent] → optional sub-features
                    └── claude.build_tasks → granular 1-session work units
```

Existing `parent_feature_id` supports arbitrary depth. F119-F128 area features become streams.

### Schema Changes to Existing Tables

1. `features.feature_type`: Add `'stream'` to valid values
2. `features.plan_data`: Standardize JSONB structure (see [[build-tracking-plan-data-schema]])
3. `build_tasks.blocked_by_task_id`: Deprecated — replaced by task_dependencies table

### New Table 1: claude.work_events

Immutable append-only audit trail. Every state change logged automatically by MCP tools.

```sql
CREATE TABLE claude.work_events (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES claude.projects,
  entity_type varchar NOT NULL,  -- 'feature' | 'build_task' | 'feedback'
  entity_id uuid NOT NULL,
  event_type varchar NOT NULL,
  old_value jsonb,
  new_value jsonb,
  reason text,                   -- WHY it changed (critical audit field)
  session_id uuid REFERENCES claude.sessions,
  created_at timestamptz NOT NULL DEFAULT now()
);
```

Valid event_types: `created`, `status_changed`, `plan_updated`, `assigned`, `blocked`, `unblocked`, `completed`, `note_added`, `spec_updated`, `dependency_added`, `dependency_removed`

### New Table 2: claude.task_dependencies

Many-to-many dependency DAG between features AND tasks. Replaces single `blocked_by_task_id`.

```sql
CREATE TABLE claude.task_dependencies (
  dependency_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  predecessor_type varchar NOT NULL,  -- 'feature' | 'build_task'
  predecessor_id uuid NOT NULL,
  successor_type varchar NOT NULL,
  successor_id uuid NOT NULL,
  dependency_type varchar NOT NULL DEFAULT 'blocks',  -- 'blocks' | 'informs' | 'enables'
  created_at timestamptz NOT NULL DEFAULT now(),
  created_session_id uuid REFERENCES claude.sessions,
  UNIQUE(predecessor_type, predecessor_id, successor_type, successor_id)
);
```

### Specifications Strategy (No 3rd Table)

- **Structured metadata** → `features.plan_data` JSONB (requirements, acceptance criteria, rationale)
- **Prose specification** → vault file linked via `features.design_doc_path`
- **Version history** → `work_events` logging every `plan_updated` change with old/new values

## New MCP Tools

| Tool | Purpose |
|------|---------|
| `get_build_board(project)` | One-call orientation: streams → features → ready tasks, dependency resolution |
| `get_build_history(project, stream?)` | Retrospective: completed work, state transitions, who did what |
| `add_dependency(predecessor, successor, type)` | Manage the dependency graph |

## Modified Existing Tools

| Tool | Change |
|------|--------|
| `advance_status()` | Auto-log work_event on every status change |
| `start_work()` | Accept build_task_id, log event, check dependencies, enforce WIP |
| `complete_work()` | Log completion event with summary |

## Dog-Fooding Path

| Phase | What |
|-------|------|
| Phase 0 (Now) | Build tracking in `claude.*` tables |
| Phase 1 | Use it to track building METIS itself |
| Phase 2 | When METIS product exists, migrate as first customer dataset |
| Phase 3 | Productize as METIS work management module |

## Related

- [[feature-catalogue]] — F119-F128 area features that become streams
- [[brainstorm-capture-enforcement-layer]] — Enforcement layer design
- FB186 — "Claude Village" idea (migrate Claude Family into METIS)

---
**Version**: 1.0
**Created**: 2026-03-16
**Updated**: 2026-03-16
**Location**: knowledge-vault/10-Projects/Project-Metis/project-governance/build-tracking-design.md
