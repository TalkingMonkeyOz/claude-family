---
projects:
- claude-family
synced: false
synced_at: '2026-01-17T00:00:00.000000'
tags:
- quick-reference
- claude-family
---

# Observability

What we log, how it's analyzed, and gaps to address.

---

## Logging Tables (Updated 2026-02-03)

| Table | Rows | Purpose | Status |
|-------|------|---------|--------|
| `sessions` | 606 | Claude Code sessions | ✅ Active |
| `rag_usage_log` | 1504 | RAG queries via UserPromptSubmit hook | ✅ Active |
| `messages` | 176 | Inter-Claude messaging | ✅ Active |
| `agent_sessions` | 43 | Spawned agent tracking | ✅ Active |
| `feedback` | 82 | Issue tracking | ✅ Active |
| `vocabulary_mappings` | 28 | Informal → canonical mappings | ✅ Active |
| `scheduled_jobs` | 25 | Job definitions + history | ✅ Active |
| `reviewer_runs` | 14 | Reviewer script executions | ✅ Active |
| `todos` | 1618 | Persistent todos across sessions | ✅ Active |
| `mcp_usage_stats` | 53 | MCP aggregated stats | ✅ Active |
| `mcp_usage` | 3509 | MCP tool call details | ✅ Active |
| `enforcement_log` | 1333 | Rule violation reminders | ✅ Active

**Note**: `process_classification_log` deprecated - skills-first replaced process router (ADR-005)
**Note**: PostToolUse MCP logger now uses catch-all matcher (no matcher = fires for ALL tools, script filters to `mcp__` prefix internally). This replaced 68 individual matchers (2026-02-07).

---

## Key Insights

### RAG System (Active)

- 664 queries logged via UserPromptSubmit hook
- Automatic context injection on every prompt
- 85% token reduction achieved
- Logs: `~/.claude/hooks.log` and `claude.rag_usage_log`

### Scheduled Jobs System

- 25 jobs defined (16 active)
- MUI Manager Scheduler UI available
- Status: FAILED when genuinely failed, ISSUES_FOUND when script found problems
- Gap: Some jobs stopped running Dec 13 (path escaping bug fixed Jan 2026)

### Agent Success Rates (Last 60 Days)

| Agent | Spawns | Success | Avg Cost |
|-------|--------|---------|----------|
| lightweight-haiku | 4 | 100% | $0.010 |
| coder-sonnet | 3 | 100% | $0.120 |
| reviewer-sonnet | 3 | 100% | $0.105 |
| mui-coder-sonnet | 5 | 80% | $0.120 |

**Insights**:
- lightweight-haiku: Best cost-effectiveness ($0.01)
- Sonnet agents: Higher success rates now (vs Opus)
- mui-coder-sonnet: Specialized for MUI React work

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
1. ~~`enforcement_log` empty~~ ✅ Fixed - 1,333 rows logged
2. ~~`mcp_usage_stats` barely used~~ ✅ Fixed - 53 aggregated + 3,509 detailed in `mcp_usage`
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

**MCP usage by server**:
```sql
SELECT mcp_server, COUNT(*) as calls,
  ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*)) as success_rate
FROM claude.mcp_usage
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY mcp_server
ORDER BY calls DESC;
```

---

## Fixes Implemented

**2026-01-17**:
- ✅ Fixed scheduled jobs path escaping (working_directory + quoted paths)
- ✅ Fixed status semantics (ISSUES_FOUND vs FAILED)
- ✅ Created FB57 for ANTHROPIC_ADMIN_API_KEY setup

**2025-12-20**:
- ✅ Added 14 regex triggers for slash commands
- ✅ Increased doc-keeper-haiku timeout: 300s → 600s

**2025-12-21**:
- ✅ Skills-First architecture replaced process router (ADR-005)

---

## Action Items

- [x] ~~Implement enforcement_log writes~~ → Working (1,333 rows)
- [x] ~~Add MCP usage tracking~~ → Working via PostToolUse hooks (3,509 calls logged)
- [ ] Create MCW observability dashboard
- [ ] Add exit code semantics to MUI scheduler (exit 1 = issues found, exit 2+ = error)
- [x] Add keyword triggers to reduce LLM classification
- [x] Increase agent timeouts
- [x] Fix scheduled jobs path escaping

---

**Version**: 3.3 (Fixed deprecated query, added catch-all matcher note)
**Created**: 2025-12-26
**Updated**: 2026-02-07
**Location**: Claude Family/Observability.md
