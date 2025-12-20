---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:17:06.377067'
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

## Process Router Analysis

| Method | Count | Avg Latency | Notes |
|--------|-------|-------------|-------|
| LLM | 373 | 4,191ms | Slow, expensive |
| Regex | 63 | 7ms | Fast, cheap |
| Keywords | 25 | 6ms | Fast, cheap |

**Insight**: 81% of classifications use LLM (slow). Could optimize with better keyword matching.

---

## Agent Usage Stats

| Agent | Spawns | Success Rate | Avg Cost |
|-------|--------|--------------|----------|
| coder-haiku | 42 | 57% | $0.035 |
| python-coder-haiku | 28 | 71% | $0.045 |
| lightweight-haiku | 12 | 83% | $0.013 |
| analyst-sonnet | 11 | 45% | $0.300 |
| reviewer-sonnet | 9 | 56% | $0.105 |
| researcher-opus | 6 | 17% | $0.725 |

**Insights**:
- `lightweight-haiku` has best success rate (83%)
- `researcher-opus` has worst success rate (17%) - needs investigation
- Haiku agents are most cost-effective

---

## Knowledge Retrieval

| Method | Count | Avg Latency | Avg Results |
|--------|-------|-------------|-------------|
| keyword | 21 | 11ms | 5.0 |

**Note**: Only keyword search used. Semantic search not implemented.

---

## Fixes Implemented (2025-12-20)

### Slash Command Regex Triggers

Added 14 high-priority regex triggers for slash commands to bypass slow LLM classification:

| Pattern | Process | Trigger ID |
|---------|---------|------------|
| `^/session-start` | PROC-SESSION-001 | 55 |
| `^/session-end` | PROC-SESSION-002 | 56 |
| `^/session-commit` | PROC-SESSION-003 | 57 |
| `^/session-resume` | PROC-SESSION-004 | 58 |
| `^/feedback-create` | PROC-COMM-001 | 59 |
| `^/feedback-check` | PROC-COMM-001 | 60 |
| `^/feedback-list` | PROC-COMM-001 | 61 |
| `^/project-init` | PROC-PROJECT-001 | 62 |
| `^/phase-advance` | PROC-PROJECT-002 | 63 |
| `^/retrofit-project` | PROC-PROJECT-003 | 64 |
| `^/check-compliance` | PROC-PROJECT-004 | 65 |
| `^/review-docs` | PROC-DOC-002 | 66 |
| `^/knowledge-capture` | PROC-DATA-003 | 67 |
| `^/review-data` | PROC-DATA-001 | 68 |

**Expected Impact**: Slash commands now use 7ms regex path instead of 4,191ms LLM path.

### Agent Timeout Increase

Increased `doc-keeper-haiku` timeout from 300s to 600s in `agent_specs.json`.

**Root Cause**: 100% of recent agent failures were timeouts - orchestrator wasn't honoring spec timeouts.

---

## Task Breakdown Pattern

For complex tasks, use this multi-agent pattern:

```
1. Planner First: Use planner-sonnet to break down the task
2. Spawn in Parallel: Multiple lightweight-haiku or coder-haiku for independent subtasks
3. Review Last: Use reviewer-sonnet to validate the combined work
```

**Why This Works**:
- Avoids single-agent timeouts on large tasks
- Each subtask is scoped to succeed within timeout
- Parallel execution is faster overall
- Cost-effective (haiku agents are 10-50x cheaper than opus)

**Anti-Pattern** (DON'T):
- Don't spawn researcher-opus for large exploratory tasks (17% success rate)
- Don't give coder-haiku tasks requiring deep research first

---

## Gaps to Address

### High Priority

1. **enforcement_log empty** - Violations not being logged
2. **mcp_usage_stats barely used** - Tool call tracking incomplete
3. **researcher-opus 17% success** - ✅ Mitigated with task breakdown pattern

### Medium Priority

4. **No dashboards** - Data exists but no visualization
5. ~~**LLM classification overhead** - 81% using slow path~~ - ✅ Fixed with slash command triggers
6. **No alerting** - Failures go unnoticed

### Low Priority

7. **No cost rollup** - Per-session/project cost tracking
8. **No trend analysis** - Week-over-week comparisons

---

## Analysis Queries

### Top Failing Agents
```sql
SELECT agent_type, COUNT(*),
       ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*)) as success_rate
FROM claude.agent_sessions
GROUP BY agent_type
HAVING COUNT(*) > 5
ORDER BY success_rate ASC;
```

### Classification Performance
```sql
SELECT classification_method, COUNT(*), ROUND(AVG(latency_ms)) as avg_ms
FROM claude.process_classification_log
GROUP BY classification_method;
```

### Recent Failures
```sql
SELECT agent_type, task_description, error_message
FROM claude.agent_sessions
WHERE success = false
ORDER BY spawned_at DESC
LIMIT 10;
```

---

## Related Docs

- [[Claude Family Postgres]] - Database schema
- [[Orchestrator MCP]] - Agent spawning
- [[MCP configuration]] - MCP setup
- [[Project - Claude Family]] - Infrastructure overview

---

## Action Items

- [ ] Implement enforcement_log writes in process_router
- [ ] Add MCP usage tracking to orchestrator
- [ ] Create MCW dashboard for observability
- [x] Add keyword triggers to reduce LLM classification ✅ (2025-12-20: Added 14 regex triggers for slash commands)
- [x] Increase agent timeouts ✅ (2025-12-20: doc-keeper-haiku 300→600s)
- [ ] Verify orchestrator uses spec timeouts (not hardcoded)
- [ ] Add Week-over-Week trend queries to MCW