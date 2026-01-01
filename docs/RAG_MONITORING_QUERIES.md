# RAG System Monitoring Queries

**Purpose**: Monitor RAG performance after threshold adjustment (0.45 → 0.30)

**Date**: 2025-12-31
**Changes**: Lowered similarity threshold from 0.45 to 0.30 based on industry research

---

## Quick Stats

```sql
-- Overall hit rate (last 24 hours)
SELECT
    COUNT(*) as total_queries,
    COUNT(*) FILTER (WHERE results_count > 0) as successful_queries,
    ROUND(COUNT(*) FILTER (WHERE results_count > 0) * 100.0 / COUNT(*), 1) as hit_rate_pct,
    ROUND(AVG(top_similarity) FILTER (WHERE results_count > 0), 3) as avg_similarity,
    ROUND(AVG(latency_ms), 0) as avg_latency_ms
FROM claude.rag_usage_log
WHERE created_at > NOW() - INTERVAL '24 hours';
```

---

## Hit Rate by Query Type

```sql
-- Compare session_preload vs user_prompt performance
SELECT
    query_type,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE results_count > 0) as hits,
    ROUND(COUNT(*) FILTER (WHERE results_count > 0) * 100.0 / COUNT(*), 1) as hit_rate_pct,
    ROUND(AVG(top_similarity) FILTER (WHERE results_count > 0), 3) as avg_similarity
FROM claude.rag_usage_log
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY query_type
ORDER BY query_type;
```

---

## Similarity Score Distribution

```sql
-- See what similarity scores we're getting
SELECT
    CASE
        WHEN top_similarity >= 0.5 THEN '0.50+'
        WHEN top_similarity >= 0.4 THEN '0.40-0.49'
        WHEN top_similarity >= 0.3 THEN '0.30-0.39'
        WHEN top_similarity >= 0.2 THEN '0.20-0.29'
        ELSE '<0.20'
    END as similarity_range,
    COUNT(*) as query_count,
    ROUND(AVG(results_count), 1) as avg_results
FROM claude.rag_usage_log
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND results_count > 0
GROUP BY similarity_range
ORDER BY similarity_range DESC;
```

---

## Recent Successful Queries

```sql
-- See what queries are working well
SELECT
    created_at,
    query_type,
    LEFT(query_text, 80) as query_preview,
    results_count,
    ROUND(top_similarity::numeric, 3) as similarity,
    latency_ms,
    docs_returned[1] as top_doc
FROM claude.rag_usage_log
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND results_count > 0
ORDER BY created_at DESC
LIMIT 10;
```

---

## Recent Failed Queries

```sql
-- See what queries are failing (for improvement)
SELECT
    created_at,
    query_type,
    LEFT(query_text, 80) as query_preview,
    latency_ms
FROM claude.rag_usage_log
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND results_count = 0
ORDER BY created_at DESC
LIMIT 10;
```

---

## Performance by Project

```sql
-- Which projects have better RAG performance?
SELECT
    project_name,
    COUNT(*) as total_queries,
    ROUND(COUNT(*) FILTER (WHERE results_count > 0) * 100.0 / COUNT(*), 1) as hit_rate_pct,
    ROUND(AVG(top_similarity) FILTER (WHERE results_count > 0), 3) as avg_similarity
FROM claude.rag_usage_log
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY project_name
ORDER BY hit_rate_pct DESC;
```

---

## Expected Improvements

**Before (0.45 threshold):**
- Hit rate: ~30%
- Only high-confidence matches returned
- Many relevant docs filtered out

**After (0.30 threshold):**
- Expected hit rate: 60-70%
- More relevant docs included
- Possible increase in lower-confidence matches

**Monitoring Period:** 48 hours

**Decision Criteria:**
- If hit rate 60%+ and quality good → Success, keep 0.30
- If hit rate < 50% → Lower to 0.25
- If too many irrelevant results → Raise to 0.35

---

## Logs Location

**Hooks log**: `~/.claude/hooks.log`
**Database log**: `claude.rag_usage_log` table

**Tail recent activity:**
```bash
# See recent RAG queries
grep "rag_query" ~/.claude/hooks.log | tail -20

# See query text
grep "Query text" ~/.claude/hooks.log | tail -10
```

---

**Version**: 1.0
**Created**: 2025-12-31
**Updated**: 2025-12-31
**Location**: docs/RAG_MONITORING_QUERIES.md
