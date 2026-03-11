---
projects:
  - claude-family
  - claude-manager-mui
tags:
  - scheduler
  - jobs
  - automation
synced: false
---

# Scheduled Jobs Management

How scheduled jobs work in the Claude Family ecosystem.

---

## Architecture

Jobs are tracked in two places:

| Source | Purpose | Execution |
|--------|---------|-----------|
| **Windows Task Scheduler** | OS-level automation | Runs automatically |
| **claude.scheduled_jobs** | Claude-triggered jobs | Run via MUI Manager or session hooks |

The `source` column in `scheduled_jobs` indicates where a job runs from:
- `windows_task_scheduler` - Windows runs it
- `database` - Claude runs via MUI Manager or manually

---

## Windows Task Scheduler Jobs

| Task | Schedule | Script |
|------|----------|--------|
| Claude Family - PostgreSQL Backup | Weekly Sat 2am | `scripts/backup_postgres.ps1` |
| Claude Family - Documentation Audit | Daily 9am | `scripts/audit_docs.py` |

These are synced to `claude.scheduled_jobs` for visibility (prefixed with "Windows:").

---

## Database Jobs (Active)

Query active jobs:
```sql
SELECT job_name, trigger_type, schedule, last_run, last_status
FROM claude.scheduled_jobs
WHERE is_active = true
ORDER BY source, job_name;
```

### Trigger Types

| Type | When It Runs |
|------|--------------|
| `session_start` | Claude should run at session start |
| `cron` | Scheduled time (no daemon - manual) |
| `windows_scheduler` | Windows Task Scheduler |

---

## MUI Manager Scheduler

The `claude-manager-mui` app has a Scheduler interface:

- **Sidebar**: Tools > Scheduler
- **Startup Dialog**: Shows overdue jobs on app launch
- **Run Jobs**: Click play button to execute

### Files
- `src/features/scheduler/SchedulerView.tsx`
- `src/features/scheduler/OverdueJobsDialog.tsx`
- `src-tauri/src/commands.rs` (get_scheduled_jobs, run_job)

---

## Adding New Jobs

### Database Job (Claude-triggered)
```sql
INSERT INTO claude.scheduled_jobs (
    job_id, job_name, job_description, trigger_type, schedule,
    command, working_directory, is_active, source
) VALUES (
    gen_random_uuid(),
    'my-job-name',
    'What the job does',
    'session_start',  -- or 'cron'
    'daily',          -- human-readable
    'python C:/Projects/claude-family/scripts/my_script.py',
    'C:/Projects/claude-family',
    true,
    'database'
);
```

### Windows Task (automated)
1. Create in Windows Task Scheduler
2. Add reference to DB for visibility:
```sql
INSERT INTO claude.scheduled_jobs (
    job_id, job_name, job_description, trigger_type, schedule,
    command, is_active, source
) VALUES (
    gen_random_uuid(),
    'Windows: My Task Name',
    'What it does - managed by Windows',
    'windows_scheduler',
    'Schedule description',
    'script path',
    true,
    'windows_task_scheduler'
);
```

---

## Anthropic Docs Monitor

Special job that monitors 10 Anthropic documentation pages for changes.

**State stored in**: `claude.global_config` (key: `anthropic_docs_monitor`)

**Pages monitored**:
- Claude Code changelog, best practices, sandboxing
- Agent SDK, advanced tool use, computer use
- Models overview, extended thinking, token efficiency
- MCP specification

Run: `python scripts/monitor_anthropic_docs.py --verbose`

---

## Recent Changes (2026-01-24 Audit)

**Deleted 4 jobs:**
- `Review Local LLM Usage` - purpose served (llama3.3 removed)
- `Windows: Document Scanner` - duplicate of `Document Scanner`
- `Stale Session Cleanup` - no script, placeholder
- `transcript_cleanup` - Windows version supersedes

**Fixed bugs:**
- Path bug in `compliance-audit-check`, `consistency-check` (changed to relative paths)
- Exit code bug in 3 scripts - now return 0 on successful run

**Current count**: 15 jobs (12 DB-triggered, 3 Windows refs)

---

## Maintenance

### Disable a job
```sql
UPDATE claude.scheduled_jobs
SET is_active = false,
    job_description = job_description || ' [DISABLED: reason]'
WHERE job_name = 'job-name';
```

### View job history
```sql
SELECT job_name, last_run, last_status, last_output
FROM claude.scheduled_jobs
WHERE last_run IS NOT NULL
ORDER BY last_run DESC;
```

---

**Version**: 1.1
**Created**: 2026-01-13
**Updated**: 2026-01-24
**Location**: knowledge-vault/40-Procedures/Scheduled Jobs Management.md
