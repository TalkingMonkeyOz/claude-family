---
name: maintenance
description: "Run system maintenance health checks — staleness detection, database health, data quality, and hook errors"
user-invocable: true
disable-model-invocation: true
---

# Maintenance Health Check

Run system maintenance to detect and repair staleness across all subsystems, plus database health checks.

---

## Step 1: Run System Maintenance (Automated Staleness Detection + Repair)

Call the `system_maintenance` MCP tool:

```
mcp__project-tools__system_maintenance(scope="full", auto_repair=true)
```

This handles: schema registry, vault embeddings, BPMN registry, memory embeddings, and column registry.

Display results. If `any_repaired` is true, show what was fixed. If `any_stale` is false, report "All systems clean."

## Step 2: Database Health Check

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

## Step 3: Recent Activity

```sql
SELECT
    'sessions' as metric,
    COUNT(*) FILTER (WHERE session_start > NOW() - INTERVAL '7 days') as last_7d,
    COUNT(*) FILTER (WHERE session_start > NOW() - INTERVAL '24 hours') as last_24h
FROM claude.sessions
UNION ALL
SELECT 'knowledge_entries',
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days'),
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours')
FROM claude.knowledge
UNION ALL
SELECT 'mcp_calls',
    COUNT(*) FILTER (WHERE called_at > NOW() - INTERVAL '7 days'),
    COUNT(*) FILTER (WHERE called_at > NOW() - INTERVAL '24 hours')
FROM claude.mcp_usage;
```

## Step 4: Data Quality

```sql
SELECT 'unclosed_sessions_24h' as issue, COUNT(*) as count
FROM claude.sessions
WHERE session_end IS NULL AND session_start < NOW() - INTERVAL '24 hours'
UNION ALL
SELECT 'tasks_no_feature', COUNT(*)
FROM claude.build_tasks WHERE feature_id IS NULL
UNION ALL
SELECT 'knowledge_no_embedding', COUNT(*)
FROM claude.knowledge WHERE embedding IS NULL AND tier IN ('mid', 'long');
```

## Step 5: Hook Errors

```bash
tail -50 ~/.claude/hooks.log 2>/dev/null | grep -i "error\|fail\|exception" || echo "No recent hook errors"
```

---

## Health Thresholds

| Metric | Healthy | Degraded | Action |
|--------|---------|----------|--------|
| All 5 subsystems clean | Yes | No | Auto-repaired by maintenance tool |
| Unclosed sessions (24h) | 0-2 | >5 | Run `/crash-recovery` |
| Knowledge without embeddings | 0 | >0 | Auto-fixed by maintenance tool |

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/maintenance/SKILL.md
