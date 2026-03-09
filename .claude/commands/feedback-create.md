# Create New Feedback

Guide the user through creating a new feedback item (bug, design, question, or change request).

**Use `mcp__project-tools__create_feedback` — do NOT write raw SQL against `claude_pm.*`.**

---

## Execute These Steps

### Step 1: Gather Feedback Details

Ask the user for:

1. **Type** — What kind of feedback is this?
   - `bug` - Something broken or not working correctly
   - `design` - UI/UX issue, design concern, or architectural question
   - `question` - Need clarification or information
   - `change` - Feature request or enhancement

2. **Description** — What is the issue or request? Encourage detail:
   - For bugs: Steps to reproduce, expected vs actual behavior, error messages
   - For design: What is confusing or problematic, suggested improvement
   - For questions: Context and what needs clarification
   - For changes: What feature is needed and why

3. **Priority** (optional) — 1 (critical) to 5 (low). Default: 3.

### Step 2: Create the Feedback Item

Call `mcp__project-tools__create_feedback` with:

```
mcp__project-tools__create_feedback(
    feedback_type="bug",        -- bug | design | question | change
    description="Full description of the issue or request",
    priority=3                  -- 1=critical, 2=high, 3=medium, 4=low, 5=trivial
)
```

The tool auto-detects the current project from the working directory and routes through the WorkflowEngine state machine (initial status is always `new`).

**Valid feedback_type values**: `bug`, `design`, `question`, `change`
**Do NOT use `idea`** — not a valid type per column_registry.

### Step 3: Confirm Creation

Display success to the user:

```
Feedback Created

Type: [Bug/Design/Question/Change]
Code: FB-N
Description: [First 100 chars...]
Status: new
Priority: [N]

Next Steps:
- View open feedback: /feedback-check
- List all feedback: /feedback-list
- Advance status: mcp__project-tools__advance_status(type="feedback", id="FB-N", status="triaged")
```

---

## Error Handling

**If project not registered:**
- Query `claude.projects` to find the project
- If missing, use `/project-init` to register it first

**If invalid feedback_type:**
- Valid values are: `bug`, `design`, `question`, `change`
- `idea` is not valid — use `change` for feature requests/enhancements

**If database connection fails:**
- Check postgres MCP configuration
- Test: `SELECT 1;`

---

## Example Interaction

User: "The export button doesn't work"

1. Ask for type → Bug
2. Expand description → "Export to Excel button throws NullReferenceException when clicked after filtering data. Error: 'Object reference not set' in ExportService.cs line 89. Steps: 1) Apply filter 2) Click Export → crash."
3. Call `create_feedback(feedback_type="bug", description="...", priority=2)`
4. Display confirmation with FB code

---

**Version**: 2.0 (Rewrote: use create_feedback MCP tool, removed claude_pm.* raw SQL)
**Created**: 2025-12-20
**Updated**: 2026-03-09
**Location**: .claude/commands/feedback-create.md
