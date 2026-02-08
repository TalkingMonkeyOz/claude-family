**MAINTENANCE HEALTH CHECK - System Integrity Verification**

Run periodic health checks on Claude Family infrastructure to detect issues before they become problems.

---

## Execute These Steps

### Step 1: Database Connectivity
```sql
SELECT
    current_database() as database,
    current_schema() as schema,
    NOW() as server_time,
    version() as postgres_version;
```

### Step 2: Core Table Health
```sql
SELECT
    relname as table_name,
    n_live_tup as row_count,
    last_vacuum,
    last_analyze
FROM pg_stat_user_tables
WHERE schemaname = 'claude'
  AND relname IN ('sessions', 'todos', 'feedback', 'features', 'build_tasks',
                  'messages', 'agent_sessions', 'mcp_usage', 'knowledge')
ORDER BY n_live_tup DESC;
```

### Step 3: Recent Activity Check
```sql
SELECT
    'sessions' as metric,
    COUNT(*) FILTER (WHERE session_start > NOW() - INTERVAL '7 days') as last_7d,
    COUNT(*) FILTER (WHERE session_start > NOW() - INTERVAL '24 hours') as last_24h
FROM claude.sessions
UNION ALL
SELECT
    'todos_created',
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days'),
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours')
FROM claude.todos
UNION ALL
SELECT
    'mcp_calls',
    COUNT(*) FILTER (WHERE called_at > NOW() - INTERVAL '7 days'),
    COUNT(*) FILTER (WHERE called_at > NOW() - INTERVAL '24 hours')
FROM claude.mcp_usage
UNION ALL
SELECT
    'knowledge_entries',
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days'),
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours')
FROM claude.knowledge;
```

### Step 4: Orphaned Data Check
```sql
-- Sessions without identity
SELECT 'sessions_no_identity' as issue, COUNT(*) as count
FROM claude.sessions WHERE identity_id IS NULL
UNION ALL
-- Sessions never closed (older than 24h)
SELECT 'unclosed_sessions_24h', COUNT(*)
FROM claude.sessions
WHERE session_end IS NULL AND session_start < NOW() - INTERVAL '24 hours'
UNION ALL
-- Todos without project
SELECT 'todos_no_project', COUNT(*)
FROM claude.todos WHERE project_id IS NULL
UNION ALL
-- Build tasks without feature
SELECT 'tasks_no_feature', COUNT(*)
FROM claude.build_tasks WHERE feature_id IS NULL;
```

### Step 5: Scheduled Jobs Status
```sql
SELECT
    job_name,
    trigger_type,
    is_active,
    last_run,
    last_status,
    CASE
        WHEN last_run IS NULL THEN 'NEVER_RUN'
        WHEN last_run < NOW() - INTERVAL '7 days' THEN 'STALE'
        WHEN last_status IN ('FAILED', 'ERROR') THEN 'FAILING'
        ELSE 'OK'
    END as health
FROM claude.scheduled_jobs
WHERE is_active = true
ORDER BY
    CASE
        WHEN last_status IN ('FAILED', 'ERROR') THEN 1
        WHEN last_run IS NULL THEN 2
        WHEN last_run < NOW() - INTERVAL '7 days' THEN 3
        ELSE 4
    END;
```

### Step 6: Configuration Drift Check
```sql
-- Check if workspaces have mismatched project names
SELECT 'workspace_project_mismatch' as issue, COUNT(*) as count
FROM claude.workspaces w
LEFT JOIN claude.projects p ON w.project_name = p.project_name
WHERE p.project_id IS NULL AND w.project_name IS NOT NULL
UNION ALL
-- Check for projects without workspaces
SELECT 'project_no_workspace', COUNT(*)
FROM claude.projects p
LEFT JOIN claude.workspaces w ON p.project_name = w.project_name
WHERE w.workspace_id IS NULL;
```

### Step 7: Embedding Health (RAG System)
```sql
SELECT
    'vault_embeddings' as system,
    COUNT(*) as total_docs,
    COUNT(*) FILTER (WHERE embedding IS NOT NULL) as embedded,
    COUNT(*) FILTER (WHERE embedding IS NULL) as missing_embedding
FROM claude.vault_embeddings
UNION ALL
SELECT
    'knowledge',
    COUNT(*),
    COUNT(*) FILTER (WHERE embedding IS NOT NULL),
    COUNT(*) FILTER (WHERE embedding IS NULL)
FROM claude.knowledge;
```

### Step 8: MCP Server Check
```bash
# Check if MCP processes are configured
cat ~/.claude/settings.json | grep -c "mcpServers" || echo "No MCP config"
```

### Step 9: Recent Hook Errors (from hooks.log)
```bash
# Check for recent hook errors (enforcement_log table is orphaned - writer deleted)
tail -50 ~/.claude/hooks.log 2>/dev/null | grep -i "error\|fail\|exception" || echo "No recent hook errors"
```

---

## Display Format

```
+======================================================================+
|  MAINTENANCE HEALTH CHECK                                             |
+======================================================================+

## DATABASE CONNECTIVITY: {OK/FAIL}
  Database: {database} | Schema: {schema}
  Server Time: {time} | Version: {version}

## CORE TABLES
  | Table           | Rows    | Last Vacuum | Last Analyze |
  |-----------------|---------|-------------|--------------|
  | sessions        | {n}     | {date}      | {date}       |
  | ...             |         |             |              |

## RECENT ACTIVITY (7 days / 24 hours)
  Sessions: {n} / {n}
  Todos: {n} / {n}
  MCP Calls: {n} / {n}
  Knowledge: {n} / {n}

## DATA QUALITY ISSUES
  {issue}: {count} - {severity}
  ...

## SCHEDULED JOBS
  OK: {n} jobs
  STALE: {n} jobs (not run in 7 days)
  FAILING: {n} jobs
  NEVER_RUN: {n} jobs

## EMBEDDING HEALTH
  Vault: {embedded}/{total} ({pct}% coverage)
  Knowledge: {embedded}/{total} ({pct}% coverage)

## OVERALL STATUS: {HEALTHY / DEGRADED / UNHEALTHY}

+======================================================================+
```

---

## Health Thresholds

| Metric | Healthy | Degraded | Unhealthy |
|--------|---------|----------|-----------|
| Unclosed sessions (24h) | 0-2 | 3-10 | >10 |
| Orphaned data | 0 | 1-5 | >5 |
| Stale jobs | 0 | 1-3 | >3 |
| Embedding coverage | >95% | 80-95% | <80% |
| Session activity (7d) | >5 | 1-5 | 0 |

---

## Recommended Actions

| Issue | Action |
|-------|--------|
| Unclosed sessions | Run `/crash-recovery` to investigate |
| Orphaned data | Manual cleanup or data migration needed |
| Stale jobs | Check scheduler_runner.py and trigger_type |
| Missing embeddings | Run `python scripts/embed_vault_documents.py` |
| No recent sessions | System may not be in use |
| Failing jobs | Check job logs and command paths |

---

**Version**: 1.0
**Created**: 2026-02-03
**Updated**: 2026-02-03
**Location**: .claude/commands/maintenance.md
