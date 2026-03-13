---
projects:
- claude-family
- project-metis
tags:
- design
- storage
- unified
- tasks
- bpmn
synced: false
---

# Unified Storage Design — Task Tracking Fix and BPMN Cleanup

**Parent**: [design-unified-storage.md](../../../docs/design-unified-storage.md)

---

## Task Tracking Fix

Minimal, targeted changes based on audit findings. The system needs closure enforcement, not more creation-side enforcement.

### 1. Source column

```sql
ALTER TABLE claude.todos ADD COLUMN source varchar(20)
  DEFAULT 'native_task'
  CHECK (source IN ('native_task', 'build_task', 'manual'));

-- Populate: todo_sync_hook sets 'native_task' for TodoWrite,
-- task_sync_hook sets 'native_task' for TaskCreate (same behavior)
-- create_linked_task sets 'build_task'
-- Manual DB inserts get 'manual'
```

Distinguishes the two creation paths. Enables accurate reporting on which system produces more closure.

### 2. Session-end closure gate

Before closing a session, surface unclosed tasks:

```
Open tasks this session: 4 created, 1 completed
- [ ] BT42: Implement hybrid search (in_progress)
- [ ] BT43: Add tsvector columns (todo)
- [ ] BT44: Update RAG hook (todo)

Action required: complete, defer, or cancel each.
```

**Implementation**: In `session_end_hook.py` or `/session-end`:

```python
open_tasks = query("""
  SELECT task_id, title, status FROM claude.todos
  WHERE session_id = %s AND status NOT IN ('completed', 'cancelled')
""", current_session_id)

if open_tasks:
    inject_advisory(format_closure_prompt(open_tasks))
```

Advisory, not blocking. Emergency exits still work. But the prompt makes it visible.

### 3. Feature completion wiring

`complete_work()` already checks if all tasks are done. The gap: tasks created via TodoWrite are not linked to features. Fix in `task_sync_hook.py`:

```python
# After syncing a TodoWrite task to claude.todos:
active_feature = get_active_feature(project_id)
if active_feature and not task.feature_id:
    task.feature_id = active_feature.id
```

This closes the loop: TodoWrite tasks get linked to the active feature, so `complete_work()` can accurately check "all tasks done."

### 4. Startup completion ratio

Add to session startup output:

```
Tasks: 12 completed / 47 total (25% closure rate) | 8 open this project
```

Making backlog growth visible creates organic pressure to close tasks. No enforcement needed.

---

## BPMN Cleanup

### Actions on existing models

| Action | Model | Effort | Rationale |
|--------|-------|--------|-----------|
| **Retire** | `L1_knowledge_management` | Low | Superseded by `knowledge_full_cycle`. Add cross-ref comment. |
| **Retire** | `knowledge_graph_lifecycle` | Trivial | Mark `[ASPIRATIONAL - requires Apache AGE, not installed]`. |
| **Merge** | `rag_pipeline` | Low | Keep as subprocess. `knowledge_full_cycle` references it instead of inlining. |
| **Fix** | `working_memory` Path 3 | Low | Remove compaction path. Add note: "See `precompact`." |
| **Fix** | `cognitive_memory_consolidation` | Trivial | Update `evaluate_mid` to `access_count >= 5, age >= 7d`. |
| **Fix** | `cognitive_memory_capture` | Trivial | Update dedup threshold comment to 0.75. |
| **Remove** | `work_context_assembly` (WCC) | Trivial | Dossier replaces WCC. Mark `[SUPERSEDED by dossier_lifecycle]`. |

### New models to create

| Model | Level | Scope |
|-------|-------|-------|
| `dossier_lifecycle` | L2 | Open, jot, file, search, RAG-inject cycle |
| `unified_retrieval` | L2 | RRF fusion pipeline: embed, tsvector, parallel search, fuse, budget-cap |

### Net change

13 models become 10: retire 2, remove 1 (WCC), create 2, fix/merge 4.

### Alignment improvement

Current: 72% model-to-code alignment across 13 models.
Target: 90%+ across 10 models. Fewer models, each accurately reflecting running code.

---

## Metis Gate 2 Alignment

| CF Concept | Metis Equivalent | Gate 2 Evidence |
|------------|-----------------|-----------------|
| Dossier pattern | Activity Space | Cross-session topic continuity, proven in production |
| Confidence ranking | Unified ranking | No tiers, just relevance + recency + confidence |
| RRF hybrid search | Retrieval path | BM25+vector validated, measurable improvement |
| pg_cron maintenance | Event-driven lifecycle | Autonomous, no session dependency |
| Entropy gate | Storage quality | SimpleMem pattern prevents accumulation |
| Closure gate | Completion tracking | Advisory enforcement that works |

CF is the working prototype. Every design decision is tested in production before Metis Gate 2 review. Failures are cheap here. Successes transfer directly.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/claude-family/design-storage-ops.md
