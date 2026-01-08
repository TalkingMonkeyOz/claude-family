# Review Data Quality

Run the data quality reviewer to find garbage data in the database.

## What This Checks

1. **Test Data Patterns** - Names containing "test", "e2e", "demo", etc.
2. **Orphan Records** - Foreign keys pointing to deleted records
3. **Invalid Statuses** - Values not in column_registry
4. **Null Required Fields** - Missing important data

## Instructions

When executing this command:

1. Run the reviewer script:
```bash
python C:/Projects/claude-family/scripts/reviewer_data_quality.py
```

2. For specific table:
```bash
python C:/Projects/claude-family/scripts/reviewer_data_quality.py --table work_tasks
```

3. Report findings to user in a table:

| Table | Issue | Count |
|-------|-------|-------|
| work_tasks | test data | X |
| feedback | test data | Y |

4. Check the run was logged:
```sql
SELECT * FROM claude.reviewer_runs
WHERE reviewer_type = 'data-quality'
ORDER BY started_at DESC LIMIT 1;
```

5. If issues found, offer to clean up:
```sql
-- Preview what would be deleted
SELECT * FROM claude.work_tasks WHERE title ILIKE '%test%';

-- Delete test data (with user confirmation)
DELETE FROM claude.work_tasks WHERE title ILIKE '%test%';
```

## Scheduled

This review runs automatically **daily** via scheduled_jobs.

---

**Reviewer Type**: data-quality
**Schedule**: Daily

---

**Version**: 1.0
**Created**: 2025-12-15
**Updated**: 2026-01-08
**Location**: .claude/commands/review-data.md
