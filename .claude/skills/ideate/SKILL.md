---
name: ideate
description: "Structured ideation pipeline — capture idea, evaluate feasibility, create feature, and break down into build tasks"
user-invocable: true
disable-model-invocation: true
---

# Ideation Pipeline: From Idea to Ready-to-Build Feature

Structured workflow that guides an idea through evaluation, feature creation, and task breakdown.

---

## Step 1: Capture the Idea

Ask the user (or determine from context):
- **What**: Brief description of the idea
- **Why**: What problem does it solve?
- **Where**: Which project? (check working directory)
- **Type**: Feature, improvement, experiment?

### Log as Feedback

Use `work_create(type="feedback",` with:
- `project_path`: Current project
- `feedback_type`: `idea`
- `description`: Combined what + why
- `priority`: Initial assessment (1-5)

Note the returned `short_code` (e.g., FB45).

---

## Step 2: Evaluate Feasibility

### Quick Assessment

1. **Effort**: Small (1 session), Medium (2-5 sessions), Large (5+ sessions)?
2. **Risk**: What could go wrong?
3. **Dependencies**: What needs to exist first?
4. **Value**: How much does this help the user?

### Deep Assessment (Optional - Spawn Analyst)

For complex ideas, delegate research via Task tool with analyst-sonnet.

### Decision Point

Present to user:
- **GO**: Proceed to feature creation
- **PARK**: Save as feedback for later (leave as FB item)
- **REJECT**: Close feedback as `wont_fix`

---

## Step 3: Create Feature

Use `work_create(type="feature",` with:
- `project_path`: Current project
- `feature_name`: Clear, concise name
- `description`: Full description including approach
- `priority`: 1 (critical) to 5 (backlog)
- `plan_data`: JSON with requirements, approach, risks, success_criteria, estimated_sessions, source_feedback

---

## Step 4: Break Down into Build Tasks

Create ordered build tasks using `work_create(type="simple_task",`:

| Order | Type | Example |
|-------|------|---------|
| 1 | Schema/DB changes | "Add users table" |
| 2 | Core logic | "Implement auth service" |
| 3 | API/integration | "Create login endpoint" |
| 4 | UI components | "Build login form" |
| 5 | Tests | "Add auth test suite" |
| 6 | Docs | "Update API documentation" |

---

## Step 5: Verify and Summarize

Display summary showing source feedback, feature code, build tasks, and first unblocked task.

Suggest next steps: start building, refine the plan, or spawn analyst for research.

---

## Notes

- **MCP-first**: Use project-tools MCP for all writes (NOT raw SQL)
- **Status values**: Build tasks use `todo` (NOT `pending`)
- **Short codes**: Features = F{n}, Tasks = BT{n}, Feedback = FB{n}

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/ideate/SKILL.md
