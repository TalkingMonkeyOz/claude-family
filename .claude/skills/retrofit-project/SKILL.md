---
name: retrofit-project
description: "Add missing governance documents (CLAUDE.md, ARCHITECTURE.md, PROBLEM_STATEMENT.md) to an existing project"
user-invocable: true
disable-model-invocation: true
---

# Retrofit Project

Add missing governance documents to an existing project.

---

## What This Does

1. Checks which core documents are missing
2. Creates missing documents from templates
3. Updates CLAUDE.md to governance standard
4. Rescans documents
5. Verifies 100% compliance

## Instructions

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
   - **PROBLEM_STATEMENT.md**: Ask user what problem the project solves and who uses it. Generate from template.
   - **ARCHITECTURE.md**: Analyze existing codebase structure, generate overview.
   - **CLAUDE.md**: Check if it follows governance standard, update if needed while preserving project-specific content.

4. **Get/create project_id**:
```sql
SELECT project_id FROM claude.projects WHERE project_name = '{project}';
-- If not found:
INSERT INTO claude.projects (project_name, status, phase)
VALUES ('{project}', 'active', 'implementation')
RETURNING project_id;
```

5. **Rescan documents**:
```bash
python C:\Projects\claude-family\scripts\scan_documents.py --project {project}
```

6. **Verify compliance** and report new percentage (should be 100%).

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/retrofit-project/SKILL.md
