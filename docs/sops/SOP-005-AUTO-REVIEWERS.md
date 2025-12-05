# SOP-005: Auto-Reviewer Agents

**Status**: Active
**Version**: 1.0
**Created**: 2025-12-06
**Owner**: Claude Governance System

---

## Purpose

This SOP describes the auto-reviewer agents that automatically check documentation quality and database data quality across the Claude Family ecosystem.

---

## Overview

### Available Reviewer Agents

| Agent | Type | Purpose | Cost |
|-------|------|---------|------|
| `doc-reviewer-sonnet` | Sonnet | Documentation quality review | ~$0.15/run |
| `data-reviewer-sonnet` | Sonnet | Database data quality review | ~$0.18/run |

### When to Use

1. **Scheduled Reviews**: Run weekly via cron/Task Scheduler
2. **Pre-Release Checks**: Before major releases
3. **On-Demand**: When quality issues suspected
4. **CI/CD Integration**: As part of PR checks

---

## Documentation Reviewer (doc-reviewer-sonnet)

### What It Checks

1. **Document Existence**
   - CLAUDE.md present at project root
   - PROBLEM_STATEMENT.md present
   - ARCHITECTURE.md present

2. **Staleness**
   - CLAUDE.md: Warning if >7 days old
   - ARCHITECTURE.md: Warning if >30 days old
   - PROBLEM_STATEMENT.md: Warning if >30 days old

3. **Completeness**
   - Required sections present per template
   - Version footer exists
   - Updated date exists

4. **Accuracy**
   - Project ID matches database
   - Cross-references are valid

### Usage

**Via Script (Direct)**:
```bash
# Review single project
python scripts/reviewer_doc_quality.py --project claude-family

# Review all projects
python scripts/reviewer_doc_quality.py --all
```

**Via Orchestrator Agent**:
```python
# Spawn doc-reviewer agent
result = orchestrator.spawn_agent(
    agent_type="doc-reviewer-sonnet",
    task="Review documentation for mission-control-web project",
    workspace_dir="C:/Projects/mission-control-web"
)
```

### Output Format

```json
{
  "project": "project-name",
  "path": "C:\\Projects\\project-name",
  "reviewed_at": "2025-12-06T09:30:00",
  "summary": {
    "critical": 0,
    "warning": 1,
    "info": 0
  },
  "findings": [
    {
      "severity": "warning",
      "document": "CLAUDE.md",
      "issue": "Document stale (12 days old, threshold: 7)",
      "remediation": "Review and update CLAUDE.md"
    }
  ]
}
```

---

## Data Reviewer (data-reviewer-sonnet)

### What It Checks

1. **Constraint Violations**
   - Values not in `column_registry.valid_values`
   - Priority values outside 1-5 range

2. **Orphaned Records**
   - Features without valid project_id
   - Build_tasks without valid feature_id
   - Feedback without valid project_id

3. **Test Data Patterns**
   - Records containing "test", "TODO", "example", etc.
   - Placeholder data that should be cleaned

4. **Stale Data**
   - Unclosed sessions >24 hours old
   - Old records that should be archived

### Tables Checked

- `claude.feedback`
- `claude.features`
- `claude.build_tasks`
- `claude.projects`
- `claude.documents`
- `claude.sessions`

### Usage

**Via Script (Direct)**:
```bash
# Review all tables
python scripts/reviewer_data_quality.py --json

# Review specific table
python scripts/reviewer_data_quality.py --table feedback
```

**Via Orchestrator Agent**:
```python
# Spawn data-reviewer agent
result = orchestrator.spawn_agent(
    agent_type="data-reviewer-sonnet",
    task="Review data quality for claude schema",
    workspace_dir="C:/Projects/claude-family"
)
```

### Output Format

```json
{
  "reviewed_at": "2025-12-06T09:30:00",
  "total_summary": {
    "critical": 2,
    "warning": 5,
    "info": 1
  },
  "tables": [
    {
      "table": "feedback",
      "summary": {"critical": 1, "warning": 2, "info": 0},
      "findings": [
        {
          "severity": "critical",
          "table": "feedback",
          "column": "status",
          "issue": "Invalid value: pending",
          "count": 3,
          "valid_values": ["new", "in_progress", "resolved", "wont_fix"],
          "fix_sql": "UPDATE claude.feedback SET status = 'new' WHERE status = 'pending';"
        }
      ]
    }
  ]
}
```

---

## Severity Levels

| Severity | Meaning | Action Required |
|----------|---------|-----------------|
| **critical** | Blocks compliance, must fix | Fix immediately |
| **warning** | Quality issue, should fix | Fix within 1 week |
| **info** | Minor issue, nice to fix | Fix when convenient |

---

## Scheduling Reviews

### Windows Task Scheduler

Create scheduled task to run weekly:

```powershell
# Create weekly doc review task
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\Projects\claude-family\scripts\reviewer_doc_quality.py --all"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am
Register-ScheduledTask -TaskName "Claude-DocReview" -Action $action -Trigger $trigger
```

### Manual Review

Run before important releases or after major changes:

```bash
# Full ecosystem review
python scripts/reviewer_doc_quality.py --all > doc_review.json
python scripts/reviewer_data_quality.py --json > data_review.json
```

---

## Integration with MCW

The reviewer results can be displayed in Mission Control Web:

1. **Health Dashboard**: Shows latest reviewer run results
2. **Project Detail**: Shows per-project documentation status
3. **Activity Feed**: Logs reviewer runs and findings

---

## Troubleshooting

### Reviewer script fails

1. Check PostgreSQL is running
2. Verify psycopg/psycopg2 installed
3. Check database connection string

### Agent spawn fails

1. Verify orchestrator MCP server is running
2. Check agent_specs.json is valid JSON
3. Ensure MCP config file exists

### False positives for test data

Add legitimate entries to exclusion list in `reviewer_data_quality.py`:

```python
# Add to EXCLUDED_PATTERNS if needed
EXCLUDED_PATTERNS = ['pytest', 'unittest']
```

---

## Related Documents

- `SOP-004-PROJECT-INITIALIZATION.md` - Project setup requirements
- `ENFORCEMENT_HIERARCHY.md` - Overall enforcement system
- `CLAUDE_GOVERNANCE_SYSTEM_PLAN.md` - Phase F specification

---

**Version**: 1.0
**Created**: 2025-12-06
**Location**: C:\Projects\claude-family\docs\sops\SOP-005-AUTO-REVIEWERS.md
