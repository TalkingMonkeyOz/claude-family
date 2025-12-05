# Review Documentation Staleness

Run the documentation staleness reviewer to find outdated docs.

## What This Checks

1. **Stale Documents** - Files not updated in 30+ days
2. **Missing Files** - Documents in DB but file doesn't exist
3. **Critical Docs** - CLAUDE.md, ARCHITECTURE.md older than 14 days

## Instructions

When executing this command:

1. Run the reviewer script:
```bash
python C:/Projects/claude-family/scripts/reviewer_doc_staleness.py
```

2. For specific project:
```bash
python C:/Projects/claude-family/scripts/reviewer_doc_staleness.py --project {project_name}
```

3. Report findings to user:
   - List stale documents with days since update
   - Flag any missing files
   - Highlight critical docs needing review

4. Check the run was logged:
```sql
SELECT * FROM claude.reviewer_runs
WHERE reviewer_type = 'doc-staleness'
ORDER BY started_at DESC LIMIT 1;
```

5. If issues found, suggest:
   - Update stale docs with current info
   - Remove or archive missing file references
   - Review critical docs for accuracy

## Scheduled

This review runs automatically **weekly** via scheduled_jobs.

---

**Reviewer Type**: doc-staleness
**Schedule**: Weekly
