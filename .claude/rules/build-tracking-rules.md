# Build Tracking Rules

## When Build Tracking Applies

Projects with **streams** (feature_type='stream') use the full build tracking system.
Projects without streams use the existing flat feature/task workflow — no changes.

## Hierarchy

```
Stream (feature_type='stream')
  └── Feature (parent_feature_id → stream)
       └── Build Task (feature_id → feature)
```

## Required Workflow

1. **Orient first**: Call `get_build_board(project)` at session start to see what's ready
2. **Respect dependencies**: `start_work()` will BLOCK if predecessors aren't completed
3. **Use the tools**: `start_work()` / `complete_work()` — don't raw UPDATE status
4. **Add deps explicitly**: Use `add_dependency()` when tasks depend on each other

## Dependency Rules

- Tasks can depend on other tasks or features
- Features can depend on other features
- Circular dependencies are rejected
- `start_work()` validates all predecessors are completed before allowing start
- `complete_work()` reports when parent feature is ready for completion

## Override Mechanism

If you must bypass a condition check (emergency fix, testing):
```
advance_status("build_tasks", "BT5", "in_progress", override_reason="Emergency hotfix")
```
Override is logged to audit_log. Use sparingly.

## Stream Completion

- A stream is complete when ALL child features are completed/cancelled
- A feature is complete when ALL build tasks are completed/cancelled
- `complete_work()` auto-detects and reports readiness up the chain
