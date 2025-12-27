---
projects:
- claude-family
synced: false
synced_at: '2025-12-27T00:00:00.000000'
tags:
- quick-reference
- claude-family
---

# Observability

What we log, how it's analyzed, and gaps to address.

---

## Logging Tables

| Table | Rows | Purpose | Status |
|-------|------|---------|--------|
| `process_classification_log` | 461 | Process router decisions | ✅ Active |
| `sessions` | 211 | Claude Code sessions | ✅ Active |
| `agent_sessions` | 127 | Spawned agent tracking | ✅ Active |
| `messages` | 90 | Inter-Claude messaging | ✅ Active |
| `feedback` | 46 | Issue tracking | ✅ Active |
| `knowledge_retrieval_log` | 21 | Vault queries | ✅ Active |
| `mcp_usage_stats` | 2 | MCP tool calls | ⚠️ Barely used |
| `enforcement_log` | 0 | Rule violations | ❌ NOT USED |

---

## Key Insights

### Process Router (Classification)

| Method | Count | Latency | Notes |
|--------|-------|---------|-------|
| LLM | 373 | 4,191ms | Slow, expensive |
| Regex | 63 | 7ms | Fast (slash commands) |
| Keywords | 25 | 6ms | Fast |

**Fix**: Added 14 regex triggers for slash commands (now 7ms vs 4,191ms)

### Agent Success Rates

| Agent | Spawns | Success | Avg Cost |
|-------|--------|---------|----------|
| lightweight-haiku | 12 | 83% | $0.013 |
| python-coder-haiku | 28 | 71% | $0.045 |
| coder-haiku | 42 | 57% | $0.035 |
| reviewer-sonnet | 9 | 56% | $0.105 |
| analyst-sonnet | 11 | 45% | $0.300 |
| researcher-opus | 6 | 17% | $0.725 |

**Insights**:
- lightweight-haiku: Best success rate (83%)
- researcher-opus: Worst (17%) - use task breakdown pattern instead
- Haiku agents: Most cost-effective

---

## Task Breakdown Pattern (Multi-Agent)

For complex tasks:

```
1. Planner: planner-sonnet breaks down task
2. Execute: Multiple lightweight-haiku/coder-haiku in parallel
3. Review: reviewer-sonnet validates combined work
```

**Why**:
- Avoids single-agent timeouts
- Parallel execution faster
- Cost-effective (haiku 10-50x cheaper than opus)

**Anti-Patterns**:
- ❌ researcher-opus for large exploratory tasks (17% success)
- ❌ coder-haiku for tasks needing deep research first

---

## Gaps to Address

### High Priority
1. `enforcement_log` empty - violations not logged
2. `mcp_usage_stats` barely used - tracking incomplete
3. ~~researcher-opus 17% success~~ ✅ Mitigated with task breakdown

### Medium Priority
4. No dashboards - data exists, no visualization
5. ~~LLM classification overhead~~ ✅ Fixed with slash command triggers
6. No alerting - failures go unnoticed

### Low Priority
7. No cost rollup per-session/project
8. No trend analysis (week-over-week)

---

## Analysis Queries

**Top failing agents**:
```sql
SELECT agent_type, COUNT(*),
  ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*)) as success_rate
FROM claude.agent_sessions
GROUP BY agent_type
HAVING COUNT(*) > 5
ORDER BY success_rate ASC;
```

**Classification performance**:
```sql
SELECT classification_method, COUNT(*), ROUND(AVG(latency_ms)) as avg_ms
FROM claude.process_classification_log
GROUP BY classification_method;
```

---

## Fixes Implemented

**2025-12-20**:
- ✅ Added 14 regex triggers for slash commands (PROC-SESSION-*, PROC-COMM-*, etc.)
- ✅ Increased doc-keeper-haiku timeout: 300s → 600s

---

## Action Items

- [ ] Implement enforcement_log writes
- [ ] Add MCP usage tracking to orchestrator
- [ ] Create MCW observability dashboard
- [ ] Verify orchestrator uses spec timeouts (not hardcoded)
- [ ] Add week-over-week trend queries to MCW
- [x] Add keyword triggers to reduce LLM classification
- [x] Increase agent timeouts

---

**Version**: 2.0 (Condensed)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: Claude Family/Observability.md
