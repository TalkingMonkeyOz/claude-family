# Check Project Compliance

Run a comprehensive compliance audit for the current project.

## What This Does

1. Runs `scripts/run_compliance_audit.py` with project name
2. Checks governance, documentation, data quality, and standards
3. Stores results in `claude.compliance_audits`
4. Updates audit schedule in `claude.audit_schedule`

## Instructions

When executing this command:

1. **Detect current project** from working directory

2. **Run the audit script**:
```bash
python "C:/Projects/claude-family/scripts/run_compliance_audit.py" {project_name} all
```

3. **Report the results** shown by the script

4. **If failures exist**, provide remediation steps:
   - For missing CLAUDE.md: Run `/retrofit-project`
   - For missing hooks: Check `.claude/hooks.json` config
   - For stale docs: Update or archive old documents
   - For test data: Clean up test sessions

5. **Verify database record**:
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

## Example Output

```
Compliance Audit - my-project
Type: all
==================================================
  [OK] governance/CLAUDE.md: CLAUDE.md exists with 4232 chars
  [OK] governance/ARCHITECTURE.md: ARCHITECTURE.md exists
  [FAIL] governance/PROBLEM_STATEMENT.md: PROBLEM_STATEMENT.md is missing
  [OK] governance/hooks.json: Hooks configuration exists
  [OK] governance/commands: 12 commands found
  [OK] documentation/docs_folder: docs/ folder exists
  [OK] documentation/file_count: 45 markdown files found
  [WARN] documentation/recent_updates: No updates in last 30 days
  [OK] data_quality/session_count: 8 sessions in last 30 days
  [OK] standards/standards_docs: 6 standards documents available
  [OK] standards/process_router: Process router configured

Summary: 9 passed, 1 failed, 1 warnings
Audit ID: abc123-...
```

## Related

- `/retrofit-project` - Add missing governance docs
- `/review-docs` - Run documentation quality review
- `/review-data` - Run data quality review
- `docs/standards/COMPLIANCE_CHECKLIST.md` - Manual checklist

---

**Version**: 2.0
**Updated**: 2025-12-08
