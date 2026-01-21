# Retrofit Project

Add missing governance documents to an existing project.

## What This Does

1. Checks which core documents are missing
2. Creates missing documents from templates
3. Updates CLAUDE.md to governance standard
4. **Sets up slash commands** (if missing)
5. Rescans documents
6. Verifies 100% compliance

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

6. **Set up slash commands** (if missing):
   - Check if `.claude/commands/` exists and has all standard commands
   - If missing, run propagation:
```bash
python C:\Projects\claude-family\scripts\propagate_commands.py --all
```
   - Register commands in database if not present:
```sql
-- Check if project has commands
SELECT COUNT(*) FROM claude.shared_commands
WHERE scope = 'project' AND scope_ref = '{project_id}';

-- If count is 0, copy from template
INSERT INTO claude.shared_commands (command_name, filename, description, content, tags, version, scope, scope_ref, is_core, is_active)
SELECT
    command_name, filename, description, content, tags, version,
    'project', '{project_id}', false, true
FROM claude.shared_commands
WHERE scope = 'project'
AND scope_ref = '9b563af2-4762-4878-b5bf-429dac0cc481'  -- nimbus-import template
ON CONFLICT DO NOTHING;
```

7. **Rescan documents**:
```bash
python C:\Projects\claude-family\scripts\scan_documents.py --project {project}
```

8. **Verify compliance**:
```sql
SELECT * FROM claude.v_project_governance WHERE project_name = '{project}';
```

9. **Report**:
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

**Version**: 1.1
**Created**: 2025-12-06
**Updated**: 2026-01-21
**Location**: .claude/commands/retrofit-project.md
