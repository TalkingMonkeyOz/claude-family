---
projects:
- claude-family
tags:
- health
- infrastructure
- reference
synced: false
---

# Claude Family System Health & Risks

**Purpose**: Single source of truth for what's working vs broken
**Last Verified**: 2026-01-07

---

## ✅ WORKING SYSTEMS

| System | Evidence | Last Verified |
|--------|----------|---------------|
| **SessionStart Hook** | 5 sessions logged today | 2026-01-07 |
| **RAG Hook** | 64 queries today, 944ms avg | 2026-01-07 |
| **TodoWrite Hook** | 98 todos updated today | 2026-01-07 |
| **Standards Validator** | hooks.log shows instruction matching | 2026-01-07 |
| **Vault Embeddings** | 8,450 chunks from 588 docs | 2026-01-07 |
| **MCP: postgres** | All queries working | 2026-01-07 |
| **MCP: orchestrator** | Agent spawning functional | 2026-01-07 |
| **Session Commands** | /session-resume is database-driven | 2026-01-07 |

---

## ❌ DEAD SYSTEMS

| System | Issue | Last Activity |
|--------|-------|---------------|
| **scheduled_jobs** | Never auto-triggers | 2025-12-07 |
| **reminders** | No hook checks this table | Never |
| **process_registry** | Replaced by skills (ADR-005) | Archived |

---

## ⚠️ KNOWN RISKS

### High Priority

| Risk | Impact | Mitigation |
|------|--------|------------|
| **No health dashboard** | Issues go unnoticed | Create daily health check |
| **Silent hook failures** | No alerts on failure | Add error aggregation |
| **Session end not enforced** | Stale sessions | Auto-close mechanism |

### Medium Priority

| Risk | Impact | Mitigation |
|------|--------|------------|
| **RAG latency ~1s** | Delay per prompt | Monitor, optimize |
| **Vault docs oversized** | Over 300 line limit | Split large docs |

---

## Verification Queries

```sql
-- Sessions today
SELECT COUNT(*) FROM claude.sessions
WHERE session_start::date = CURRENT_DATE;

-- RAG usage today
SELECT COUNT(*), AVG(latency_ms)::int
FROM claude.rag_usage_log WHERE created_at::date = CURRENT_DATE;

-- Dead scheduled jobs
SELECT job_name, last_run FROM claude.scheduled_jobs;
```

---

## Quick Health Check

```bash
# Hook log
tail -20 ~/.claude/hooks.log

# Hook scripts exist
ls scripts/*hook*.py .claude-plugins/*/scripts/*hook*.py
```

---

See also: [[System Architecture]], [[HOW_I_WORK]]

---

**Version**: 1.0
**Created**: 2026-01-07
**Updated**: 2026-01-07
**Location**: knowledge-vault/Claude Family/System Health.md
