**MAINTENANCE HEALTH CHECK - System Integrity Verification**

Run system maintenance to detect and repair staleness across all subsystems, plus database health checks.

---

## Execute These Steps

### Step 1: Run System Maintenance (Automated Staleness Detection + Repair)

Call the `system_maintenance` MCP tool:

```
mcp__project-tools__system_maintenance(scope="full", auto_repair=true)
```

This implements the `system_maintenance` BPMN process and handles:
- **Schema registry**: Detects new/changed tables, runs schema_docs + embed_schema
- **Vault embeddings**: Detects unembedded .md files, runs embed_vault_documents
- **BPMN registry**: Detects unsynced .bpmn files, syncs to claude.bpmn_processes
- **Memory embeddings**: Detects mid-tier knowledge without embeddings, generates them
- **Column registry**: Detects missing CHECK constraint entries, syncs from pg_catalog

Display the results from the tool response. If `any_repaired` is true, show what was fixed.
If `any_stale` is false, report "All systems clean."

### Step 2: Database Health Check

```sql
SELECT
    relname as table_name,
    n_live_tup as row_count,
    last_vacuum,
    last_analyze
FROM pg_stat_user_tables
WHERE schemaname = 'claude'
  AND relname IN ('sessions', 'todos', 'feedback', 'features', 'build_tasks',
                  'messages', 'mcp_usage', 'knowledge', 'schema_registry',
                  'vault_embeddings', 'bpmn_processes', 'column_registry')
ORDER BY n_live_tup DESC;
```

### Step 3: Recent Activity

```sql
SELECT
    'sessions' as metric,
    COUNT(*) FILTER (WHERE session_start > NOW() - INTERVAL '7 days') as last_7d,
    COUNT(*) FILTER (WHERE session_start > NOW() - INTERVAL '24 hours') as last_24h
FROM claude.sessions
UNION ALL
SELECT
    'knowledge_entries',
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days'),
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours')
FROM claude.knowledge
UNION ALL
SELECT
    'mcp_calls',
    COUNT(*) FILTER (WHERE called_at > NOW() - INTERVAL '7 days'),
    COUNT(*) FILTER (WHERE called_at > NOW() - INTERVAL '24 hours')
FROM claude.mcp_usage;
```

### Step 4: Data Quality

```sql
-- Unclosed sessions older than 24h
SELECT 'unclosed_sessions_24h' as issue, COUNT(*) as count
FROM claude.sessions
WHERE session_end IS NULL AND session_start < NOW() - INTERVAL '24 hours'
UNION ALL
-- Build tasks without feature
SELECT 'tasks_no_feature', COUNT(*)
FROM claude.build_tasks WHERE feature_id IS NULL
UNION ALL
-- Knowledge without embeddings
SELECT 'knowledge_no_embedding', COUNT(*)
FROM claude.knowledge WHERE embedding IS NULL AND tier IN ('mid', 'long');
```

### Step 5: Hook Errors

```bash
tail -50 ~/.claude/hooks.log 2>/dev/null | grep -i "error\|fail\|exception" || echo "No recent hook errors"
```

---

## Display Format

```
+======================================================================+
|  SYSTEM MAINTENANCE REPORT                                            |
+======================================================================+

## STALENESS DETECTION + REPAIR
  Schema:          {status} ({detail})
  Vault:           {status} ({detail})
  BPMN:            {status} ({detail})
  Memory:          {status} ({detail})
  Column Registry: {status} ({detail})

## DATABASE HEALTH
  | Table              | Rows    | Last Vacuum | Last Analyze |
  |--------------------|---------|-------------|--------------|
  | ...                |         |             |              |

## RECENT ACTIVITY (7d / 24h)
  Sessions:    {n} / {n}
  Knowledge:   {n} / {n}
  MCP Calls:   {n} / {n}

## DATA QUALITY
  {issue}: {count}
  ...

## OVERALL STATUS: {HEALTHY / NEEDS ATTENTION / DEGRADED}

+======================================================================+
```

---

## Health Thresholds

| Metric | Healthy | Degraded | Action |
|--------|---------|----------|--------|
| All 5 subsystems clean | Yes | No | Auto-repaired by maintenance tool |
| Unclosed sessions (24h) | 0-2 | >5 | Run `/crash-recovery` |
| Knowledge without embeddings | 0 | >0 | Auto-fixed by maintenance tool |
| Embedding coverage | >95% | <80% | Run `/maintenance` again |

---

**Version**: 2.0 (Integrated system_maintenance MCP tool for automated staleness detection + repair)
**Created**: 2026-02-03
**Updated**: 2026-02-28
**Location**: .claude/commands/maintenance.md
