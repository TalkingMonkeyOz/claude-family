---
name: review-docs
description: "Run documentation staleness review to find outdated docs, missing files, and stale critical documents"
user-invocable: true
disable-model-invocation: true
---

# Review Documentation Staleness

Run the documentation staleness reviewer to find outdated docs.

## What This Checks

1. **Stale Documents** - Files not updated in 30+ days
2. **Missing Files** - Documents in DB but file doesn't exist
3. **Critical Docs** - CLAUDE.md, ARCHITECTURE.md older than 14 days

## Instructions

1. Run the reviewer script:
```bash
python C:/Projects/claude-family/scripts/reviewer_doc_staleness.py
```

2. For specific project:
```bash
python C:/Projects/claude-family/scripts/reviewer_doc_staleness.py --project {project_name}
```

3. Report findings: stale documents with days since update, missing files, critical docs needing review.

4. Check the run was logged:
```sql
SELECT * FROM claude.reviewer_runs
WHERE reviewer_type = 'doc-staleness'
ORDER BY started_at DESC LIMIT 1;
```

5. If issues found, suggest: update stale docs, remove missing file references, review critical docs for accuracy.

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/review-docs/SKILL.md
