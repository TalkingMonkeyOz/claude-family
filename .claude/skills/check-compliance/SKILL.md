---
name: check-compliance
description: "Run a comprehensive compliance audit checking governance, documentation, data quality, and standards"
user-invocable: true
disable-model-invocation: true
---

# Check Project Compliance

Run a comprehensive compliance audit for the current project.

---

## Step 1: Detect Current Project

Determine project from working directory.

## Step 2: Run the Audit Script

```bash
python "C:/Projects/claude-family/scripts/run_compliance_audit.py" {project_name} all
```

## Step 3: Report Results

Display the script output showing pass/fail/warn for each check.

## Step 4: Remediation (If Failures)

- Missing CLAUDE.md: Run `/retrofit-project`
- Missing hooks: Check `.claude/hooks.json` config
- Stale docs: Update or archive old documents
- Test data: Clean up test sessions

## Step 5: Verify Database Record

```sql
SELECT audit_id, project_name, audit_type,
       checks_passed, checks_failed, completed_at
FROM claude.compliance_audits
WHERE project_name = '{project_name}'
ORDER BY completed_at DESC
LIMIT 1;
```

## Audit Types

| Type | What It Checks |
|------|----------------|
| governance | CLAUDE.md, ARCHITECTURE.md, PROBLEM_STATEMENT.md, hooks, commands |
| documentation | docs/ folder, file count, recent updates |
| data_quality | Test data in sessions, session counts |
| standards | Standards docs exist, process router configured |
| all | All of the above |

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/check-compliance/SKILL.md
