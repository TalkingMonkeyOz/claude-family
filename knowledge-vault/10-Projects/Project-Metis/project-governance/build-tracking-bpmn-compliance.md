---
projects:
  - Project-Metis
  - claude-family
tags:
  - bpmn
  - build-tracking
  - compliance
  - enforcement
---

# BPMN Process: P3 Build Compliance (Enforcement & Awareness)

Detail for [[build-tracking-bpmn]]. Addresses how Claude instances **know about**, **use**, and **recall** the build tracking system — all through interfaces, never direct SQL.

---

## A) Awareness — How Claude Knows It Has It

```
[Session Start]
  ▼
[System: start_session() executes]
  │ Auto-loads:
  │   ✓ CLAUDE.md — documents build tracking tools and workflow
  │   ✓ .claude/rules/build-tracking-rules.md — enforcement rules
  │   ✓ Session facts from previous session (including WIP tasks)
  ▼
[System: Project has streams?]
  │ Query: features where type='stream' and project_id matches
  ▼
◆ Yes → [Inject build board summary]
  │      "3 ready tasks | 1 in_progress (yours from last session) | 2 blocked"
  │      Stored as session_fact("build_context", summary)
  ▼
◆ No  → [Skip — project not using build tracking yet]
  ▼
[Builder: Oriented — knows available work and expectations]
```

### Awareness Mechanisms

| Layer | Mechanism | When Loaded |
|-------|-----------|-------------|
| Documentation | CLAUDE.md section on build tracking | Every session (auto) |
| Rules | `.claude/rules/build-tracking-rules.md` | Every session (auto) |
| Context | Build board summary in session facts | Session start (auto) |
| Memory | Patterns/decisions via recall_memories() | On demand |

---

## B) Usage — How Claude Interacts (Interface Layer)

**Principle**: All work management goes through MCP tools. No direct SQL on tracking tables.

| Action | Tool (Interface) | NEVER Do |
|--------|-----------------|----------|
| See available work | `get_build_board(project)` | `SELECT * FROM features/build_tasks` |
| Claim a task | `start_work(build_task_id)` | `UPDATE build_tasks SET status=...` |
| Complete a task | `complete_work(task_id, summary)` | Manual UPDATE + INSERT event |
| Add dependency | `add_dependency(pred, succ, type)` | `INSERT INTO task_dependencies` |
| Check history | `get_build_history(project)` | `SELECT FROM work_events` |
| Report blocker | `advance_status(task, 'blocked', reason)` | Direct status UPDATE |
| Find work item | `recall_entities("chunking")` | Keyword SQL search |

### Enforcement Hook (Pre-Edit / Pre-Write)

```
[Trigger: Claude attempts Edit/Write on project source files]
  ▼
[Hook: Check session context]
  │ ✓ Active build_task via start_work()? → ALLOW
  │ ✓ File is documentation/config only? → ALLOW (no task needed)
  │ ✓ File is in .claude/ or knowledge-vault/? → ALLOW (meta-work)
  │ ✗ No active task for source code edit → WARN
  │     "No active build task. Run start_work(task_id) first or confirm this is non-tracked work."
  ▼
[Note: WARN not BLOCK — don't prevent emergency fixes, just flag]
```

---

## C) When To Use It (Decision Rules)

```
◆ What kind of work?
  │
  ├── Implementation (code, config, infrastructure)
  │     → MANDATORY: start_work(build_task_id) before editing
  │     → Hook enforces via pre-edit check
  │
  ├── Design (specs, BPMN, data models, deliverables)
  │     → MANDATORY: link to feature via start_work()
  │     → Store deliverable in vault with design_doc_path
  │
  ├── Research/exploration (no deliverable)
  │     → OPTIONAL: can link to feature for context
  │     → Store findings via remember() or stash()
  │
  └── Bug fix / urgent
        → Create feedback → create_linked_task if needed → start_work()
        → High-priority feedback auto-suggests build_task creation
```

---

## D) How To Recall It (Access Patterns)

| I want to... | Tool | What I Get |
|-------------|------|------------|
| See what to work on | `get_build_board(project)` | Ready tasks, in_progress, blockers by stream |
| Find specific work item | `recall_entities("chunking service")` | Matching features/tasks with status |
| See what was done | `get_build_history(project, stream?)` | Completed events, who did what, when |
| Get spec for a task | Read `design_doc_path` + `unstash(component)` | Vault spec + working papers |
| Check dependencies | Included in `get_build_board()` | Blocked/blocking relationships |
| Review decisions | `recall_memories("METIS chunking")` | Stored design decisions |
| See full audit trail | `get_build_history(project, entity_id=X)` | All events for one item |

### Context Budget

`get_build_board()` is designed to be **compact** — one screen of output covering all streams. It does the heavy lifting (joins, dependency resolution, WIP counting) server-side so Claude doesn't need multiple queries.

For deep dives into a specific stream or feature, `get_build_history()` accepts filters to avoid pulling everything.

---

## Compliance Rules File (To Be Created)

`.claude/rules/build-tracking-rules.md` should contain:

```markdown
# Build Tracking Rules
- Implementation work REQUIRES an active build_task via start_work()
- Design work REQUIRES linkage to a feature
- All status changes go through advance_status() — never direct SQL
- Check get_build_board() at session start if project has streams
- Log blockers immediately — don't defer to session end
- stash() working notes before session ends if task is partial
```

---
**Version**: 1.0
**Created**: 2026-03-16
**Updated**: 2026-03-16
**Location**: knowledge-vault/10-Projects/Project-Metis/project-governance/build-tracking-bpmn-compliance.md
