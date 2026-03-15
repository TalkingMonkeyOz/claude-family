---
name: review-data
description: "Run data quality review to find garbage data, orphan records, invalid statuses, and null required fields"
user-invocable: true
disable-model-invocation: true
---

# Review Data Quality

Run the data quality reviewer to find garbage data in the database.

## What This Checks

1. **Test Data Patterns** - Names containing "test", "e2e", "demo", etc.
2. **Orphan Records** - Foreign keys pointing to deleted records
3. **Invalid Statuses** - Values not in column_registry
4. **Null Required Fields** - Missing important data

## Instructions

1. Run the reviewer script:
```bash
python C:/Projects/claude-family/scripts/reviewer_data_quality.py
```

2. For specific table:
```bash
python C:/Projects/claude-family/scripts/reviewer_data_quality.py --table work_tasks
```

3. Report findings in a table format.

4. Check the run was logged:
```sql
SELECT * FROM claude.reviewer_runs
WHERE reviewer_type = 'data-quality'
ORDER BY started_at DESC LIMIT 1;
```

5. If issues found, offer to clean up with user confirmation.

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/review-data/SKILL.md
