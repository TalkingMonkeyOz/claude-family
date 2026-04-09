---
projects:
  - claude-family
tags:
  - scheduler
  - jobs
  - automation
---

# Scheduled Jobs Management

How scheduled jobs work in the Claude Family ecosystem. 24 total jobs (14 active cron, 10 inactive/legacy).

---

## Architecture

**Master scheduler**: Windows Task Scheduler runs `Claude Family Job Runner` **hourly**. The Job Runner reads `claude.scheduled_jobs`, evaluates cron schedules, and executes any due jobs.

```
Windows Task Scheduler (hourly)
  └── job_runner.py
       ├── Reads claude.scheduled_jobs WHERE is_active = true
       ├── Evaluates cron expression against last_run
       └── Executes due jobs, updates last_run/last_status
```

**Key script**: `scripts/job_runner.py`
- `--list` shows all jobs with status
- `--force JOB` runs a specific job immediately
- `--dry-run` shows what would execute without running

---

## Windows Task Scheduler Tasks

| Task | Schedule | What It Does |
|------|----------|--------------|
| **Claude Family Job Runner** | Hourly | Master scheduler - triggers all cron jobs |
| PostgreSQL Backup | Weekly Sun 1am | DB backup to OneDrive (`backup_postgres.ps1`) |
| Documentation Audit | Daily 8am | Vault doc quality scan (`audit_docs.py`) |
| Claude Family Startup | Disabled | Legacy startup task |

The Job Runner is the only task that matters for cron job execution. The others are standalone Windows tasks.

---

## Active Cron Jobs (14)

| Job | Schedule (cron) | Description |
|-----|----------------|-------------|
| `vault-embeddings-update` | `0 2 * * *` (daily 2am) | Incremental Voyage AI embeddings for vault + project files |
| `memory-consolidation` | `0 3 * * *` (daily 3am) | Promote short-to-mid, mid-to-long tier memories; decay stale edges |
| `transcript-cleanup` | `0 3 * * *` (daily 3am) | Delete conversation transcripts older than 14 days |
| `knowledge-decay` | `0 4 * * *` (daily 4am) | Reduce edge strength on unused knowledge graph connections |
| `system-maintenance` | `0 5 * * *` (daily 5am) | Detect/repair staleness in schema, vault, BPMN, memory, column registry |
| `bpmn-sync` | `0 6 * * *` (daily 6am) | Sync .bpmn files from all repos to central registry with embeddings |
| `consistency-check` | `0 6 * * *` (daily 6am) | Compare hooks and commands across all projects, report drift |
| `document-scanner` | `0 6 * * *` (daily 6am) | Scan and index project docs to `claude.documents` |
| `compliance-audit-check` | `0 7 * * *` (daily 7am) | Check for due compliance audits, send messages to projects |
| `task_cleanup` | `0 */6 * * *` (every 6h) | Delete completed task JSON files from `~/.claude/tasks/` |
| `postgres-backup` | `0 2 * * 0` (Sun 2am) | Weekly DB backup to OneDrive |
| `vault-librarian` | `0 7 * * 0` (Sun 7am) | Vault health audit: uncataloged files, orphans, missing frontmatter |
| `knowledge-curator` | `0 8 * * 0` (Sun 8am) | LLM-assisted knowledge dedup and quality audit (see below) |
| `vocabulary_analyzer` | `0 9 1-7 * 1` (1st Mon 9am) | Analyze transcripts for vocabulary patterns to improve RAG |

### Knowledge Curator (New)

Weekly LLM-assisted knowledge quality audit:
1. Clusters knowledge entries by semantic similarity (Voyage AI)
2. Uses Haiku to classify clusters: duplicate, complementary, contradicting, stale
3. Uses Sonnet to merge confirmed duplicates
4. Picks the most-due project each run (round-robin)

**Execution model**: Uses Claude CLI (`claude -p "prompt"`) via the user's Max subscription. No API key needed. See `scripts/knowledge_curator.py` and BPMN model `knowledge_curation_process`.

---

## Inactive Jobs (10)

Legacy jobs retained for reference. All have `is_active = false`.

| Job | Last Trigger Type | Why Inactive |
|-----|-------------------|--------------|
| `insight-extraction` | cron | Superseded by knowledge-curator |
| `Windows: Documentation Audit` | cron | Replaced by document-scanner |
| `Agent Health Check` | session_start | No longer needed |
| `Anthropic Docs Monitor` | session_start | Monitoring paused |
| `data-quality-review` | session_start | Needs rewrite |
| `doc-staleness-review` | session_start | Replaced by vault-librarian |
| `governance-compliance-check` | session_start | Replaced by compliance-audit-check |
| `Link Checker` | session_start | Script broken, needs fix |
| `Orphan Document Report` | session_start | Replaced by vault-librarian |
| `sync-anthropic-usage` | session_start | API access removed |

---

## Adding a New Job

```sql
INSERT INTO claude.scheduled_jobs (
    job_id, job_name, job_description, trigger_type, schedule,
    command, working_directory, is_active, source
) VALUES (
    gen_random_uuid(),
    'my-job-name',
    'What the job does',
    'cron',
    '0 6 * * *',  -- standard 5-field cron expression
    'python scripts/my_script.py',
    'C:/Projects/claude-family',
    true,
    'database'
);
```

After adding, verify with `python scripts/job_runner.py --list`.

---

## Maintenance

### Useful commands
```bash
python scripts/job_runner.py --list          # See all jobs + last run
python scripts/job_runner.py --force JOB     # Force-run one job
python scripts/job_runner.py --dry-run       # Show what's due without running
```

### Disable a job
```sql
UPDATE claude.scheduled_jobs
SET is_active = false
WHERE job_name = 'job-name';
```

### View recent runs
```sql
SELECT job_name, last_run, last_status, last_output
FROM claude.scheduled_jobs
WHERE last_run IS NOT NULL
ORDER BY last_run DESC;
```

---

**Version**: 2.0
**Created**: 2026-01-13
**Updated**: 2026-04-09
**Location**: knowledge-vault/40-Procedures/infrastructure/Scheduled Jobs Management.md
