# Retrofit Project

Add missing governance documents to an existing project.

## What This Does

1. Checks which core documents are missing
2. Creates missing documents from templates
3. Updates CLAUDE.md to governance standard
4. Rescans documents
5. Verifies 100% compliance

## Instructions

When executing this command:

1. **Detect current project** from working directory

2. **Check current compliance**:
```sql
SELECT
    has_claude_md,
    has_problem_statement,
    has_architecture,
    compliance_pct
FROM claude.v_project_governance
WHERE project_name = '{detected_project}';
```

3. **For each missing document**:

   **If missing PROBLEM_STATEMENT.md**:
   - Ask user: "What problem does {project} solve?"
   - Ask user: "Who uses this project?"
   - Generate from template, filling in responses
   - Save to project root

   **If missing ARCHITECTURE.md**:
   - Analyze existing codebase structure
   - Generate architecture overview
   - Save to project root

   **If CLAUDE.md needs update**:
   - Check if it follows new standard (has Problem Statement section, Work Tracking table)
   - If not, update to governance standard while preserving project-specific content

4. **Get/create project_id**:
```sql
-- Check if project exists
SELECT project_id FROM claude.projects WHERE project_name = '{project}';

-- If not, create it
INSERT INTO claude.projects (project_name, status, phase)
VALUES ('{project}', 'active', 'implementation')
RETURNING project_id;
```

5. **Update CLAUDE.md** with project_id if missing

6. **Rescan documents**:
```bash
python C:\Projects\claude-family\scripts\scan_documents.py --project {project}
```

7. **Verify compliance**:
```sql
SELECT * FROM claude.v_project_governance WHERE project_name = '{project}';
```

8. **Report**:
   - What was created/updated
   - New compliance percentage (should be 100%)

## Example Usage

```
/retrofit-project
```

In project directory, will detect project and add missing docs.

---

**Action ID**: See `claude.actions` WHERE action_name = 'retrofit-project'

---

**Version**: 1.0
**Created**: 2025-12-06
**Updated**: 2026-01-08
**Location**: .claude/commands/retrofit-project.md
