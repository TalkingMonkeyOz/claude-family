# Create New Feedback

Guide the user through creating a new feedback item (bug, design, question, or change request) interactively.

---

## Step 1: Detect Current Project

Determine which project you're in:

```bash
pwd
```

If not found, query:
```sql
SELECT project_id FROM claude.projects
WHERE project_code ILIKE '%keyword%';
```

---

## Step 2: Ask User for Feedback Type

Use the AskUserQuestion tool to gather feedback details:

**Question 1: What type of feedback?**
- Bug - Something broken or not working
- Idea - Feature request, enhancement, or suggestion
- Question - Need clarification or information
- Change - Specific change request

---

## Step 3: Ask for Description

**Question 2: Describe the issue/request**

Prompt user to provide detailed description. Encourage them to include:
- For bugs: Steps to reproduce, expected vs actual behavior, error messages
- For design: What's confusing/problematic, suggested improvement
- For questions: Context and what needs clarification
- For changes: What feature is needed and why

---

## Step 4: Create Feedback in Database

```sql
-- Insert new feedback
INSERT INTO claude.feedback (
    project_id,
    feedback_type,
    description,
    status
)
VALUES (
    'PROJECT-ID'::uuid,
    'bug',  -- or 'idea', 'question', 'change'
    'User-provided description here',
    'new'
)
RETURNING feedback_id, created_at;
```

---

## Step 5: Offer to Add Initial Comment (Optional)

Ask user: "Would you like to add any additional notes or context?"

If yes, add a note to the description or use `remember()` to capture additional context for this feedback item.

---

## Step 6: Offer Screenshot Option

Inform user: "You can add screenshots by placing them in: `C:\Projects\{project}\feedback\{feedback_id}-1.png`"

Then update:
```sql
UPDATE claude.feedback
SET notes = 'Screenshot: feedback/{feedback_id}-1.png'
WHERE feedback_id = 'FEEDBACK-ID'::uuid;
```

---

## Step 7: Confirm Creation

Display success message:

```
✅ Feedback Created!

Type: [Bug/Design/Question/Change]
ID: feedback_id
Description: [First 80 chars...]
Created: timestamp

Next Steps:
- View all feedback: /feedback
- Add screenshots: Save to C:\Projects\{project}\feedback\{feedback_id}-N.png

Full guide: C:\claude\shared\docs\feedback-system-guide.md
```

---

## Error Handling

**If project not registered:**
- Provide registration instructions from feedback-system-guide.md
- Show program + project creation SQL

**If database connection fails:**
- Check postgres MCP connection
- Suggest running: `SELECT 1;`

**If description is too short:**
- Prompt for more details
- Minimum: 20 characters recommended

---

**Quick Usage Example:**

When user says: "The export button doesn't work"

1. Detect project → nimbus-user-loader
2. Ask type → Bug
3. Expand description → "Export to Excel button throws NullReferenceException when clicked after filtering data. Error: 'Object reference not set to an instance of an object' in ExportService.cs line 89"
4. Create feedback via `claude.feedback` INSERT
5. Confirm creation with feedback_id

---

**Version**: 1.1
**Created**: 2025-10-21
**Updated**: 2026-02-28
**Location**: .claude/commands/feedback-create.md
