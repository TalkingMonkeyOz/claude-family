**IDEATION PIPELINE: From Idea to Ready-to-Build Feature**

Structured workflow that guides an idea through evaluation, feature creation, and task breakdown using MCP tools.

---

## Step 1: Capture the Idea

Ask the user (or determine from context):
- **What**: Brief description of the idea
- **Why**: What problem does it solve?
- **Where**: Which project? (check working directory)
- **Type**: Feature, improvement, experiment?

### Log as Feedback

Use `mcp__project-tools__create_feedback` with:
- `project_path`: Current project
- `feedback_type`: `idea`
- `description`: Combined what + why
- `priority`: Initial assessment (1-5)

Note the returned `short_code` (e.g., FB45).

---

## Step 2: Evaluate Feasibility

### Quick Assessment (Do Yourself)

Answer these questions:
1. **Effort**: Small (1 session), Medium (2-5 sessions), Large (5+ sessions)?
2. **Risk**: What could go wrong?
3. **Dependencies**: What needs to exist first?
4. **Value**: How much does this help the user?

### Deep Assessment (Optional - Spawn Analyst)

For complex ideas, delegate research:

```
Task(
    subagent_type="analyst-sonnet",
    description="Evaluate feasibility of [idea]",
    prompt="Research the codebase and evaluate feasibility of: [idea description]. Check existing patterns, identify risks, estimate effort. Return: feasibility score (1-10), key risks, recommended approach."
)
```

### Decision Point

Present to user:
- **GO**: Proceed to feature creation
- **PARK**: Save as feedback for later (leave as FB item)
- **REJECT**: Close feedback as `wont_fix`

---

## Step 3: Create Feature

Use `mcp__project-tools__create_feature` with:
- `project_path`: Current project
- `feature_name`: Clear, concise name
- `description`: Full description including approach
- `priority`: 1 (critical) to 5 (backlog)
- `plan_data`: JSON object with structure:

```json
{
    "requirements": ["Req 1", "Req 2"],
    "approach": "High-level technical approach",
    "risks": ["Risk 1", "Risk 2"],
    "success_criteria": ["Criterion 1", "Criterion 2"],
    "estimated_sessions": 3,
    "source_feedback": "FB45"
}
```

Note the returned `short_code` (e.g., F93).

### Close Source Feedback

```
mcp__project-tools__update_work_status(
    item_type="feedback",
    item_id="FB45",
    new_status="implemented"
)
```

---

## Step 4: Break Down into Build Tasks

Create ordered build tasks using `mcp__project-tools__add_build_task`:

For each task:
- `feature_id`: From Step 3 (use the feature short code)
- `task_name`: Action-oriented (e.g., "Create ThemeContext provider")
- `description`: What to implement, acceptance criteria
- `step_order`: Sequential order (1, 2, 3...)
- `files_affected`: List of files this task will touch

### Task Ordering Guidelines

| Order | Type | Example |
|-------|------|---------|
| 1 | Schema/DB changes | "Add users table" |
| 2 | Core logic | "Implement auth service" |
| 3 | API/integration | "Create login endpoint" |
| 4 | UI components | "Build login form" |
| 5 | Tests | "Add auth test suite" |
| 6 | Docs | "Update API documentation" |

### Set Dependencies

If a task depends on another:
```sql
UPDATE claude.build_tasks
SET blocked_by_task_id = (SELECT task_id FROM claude.build_tasks WHERE short_code = 309)
WHERE short_code = 310;
```

---

## Step 5: Verify and Summarize

### Display Summary

```
+==================================================================+
|  IDEATION COMPLETE                                                |
+==================================================================+
|  Source: FB{n} → Feature: F{n}                                   |
|  Name: {feature_name}                                            |
|  Priority: {priority} | Sessions: ~{estimated}                   |
+------------------------------------------------------------------+
|  BUILD TASKS ({count}):                                          |
|  BT{n}: {task 1} [step 1]                                       |
|  BT{n}: {task 2} [step 2] ← blocked by BT{n-1}                 |
|  BT{n}: {task 3} [step 3]                                       |
+------------------------------------------------------------------+
|  READY TO START: BT{first_unblocked}                             |
+==================================================================+
```

### Next Steps

Suggest to user:
- "Ready to start? I'll begin with BT{n}: {task_name}"
- "Want to refine the plan first?"
- "Should I spawn an analyst to research any of these tasks?"

---

## Notes

- **MCP-first**: Use project-tools MCP for all writes (NOT raw SQL)
- **Status values**: Build tasks use `todo` (NOT `pending`)
- **Short codes**: Features = F{n}, Tasks = BT{n}, Feedback = FB{n}
- **plan_data**: Always include source_feedback link for traceability
- **Idempotent**: Re-running updates existing items rather than creating duplicates

---

**Version**: 1.0
**Created**: 2026-02-08
**Location**: .claude/commands/ideate.md
