# Check Project Compliance

Check if current project has all required governance documents.

## What This Does

1. Queries `claude.v_project_governance` for current project
2. Reports which core documents exist/missing
3. Shows compliance percentage

## Instructions

When executing this command:

1. **Detect current project** from working directory

2. **Query compliance view**:
```sql
SELECT
    project_name,
    phase,
    has_claude_md,
    has_problem_statement,
    has_architecture,
    compliance_pct
FROM claude.v_project_governance
WHERE project_name = '{detected_project}';
```

3. **Report results** in table format:

| Document | Status |
|----------|--------|
| CLAUDE.md | [exists/missing] |
| PROBLEM_STATEMENT.md | [exists/missing] |
| ARCHITECTURE.md | [exists/missing] |

**Compliance: {X}%**

4. **If not 100%**, suggest:
   - Run `/retrofit-project` to add missing documents

## Example Output

```
Project: my-app
Phase: implementation

| Document | Status |
|----------|--------|
| CLAUDE.md | exists |
| PROBLEM_STATEMENT.md | MISSING |
| ARCHITECTURE.md | exists |

Compliance: 66%

To fix: Run /retrofit-project to add missing documents.
```

---

**Action ID**: See `claude.actions` WHERE action_name = 'check-compliance'
