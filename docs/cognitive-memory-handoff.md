# Cognitive Memory System - Design Handoff

## Problem

`@modelcontextprotocol/server-memory` dumps the **entire knowledge graph** into context via `read_graph`. No pagination, no budget. As the graph grows, it crowds out actual work.

## Solution: Three-Tier Cognitive Memory

| Tier | Budget | Content | Search |
|------|--------|---------|--------|
| SHORT | ~200 tokens | Session facts, creds, decisions | Fast exact lookup |
| MID | ~500 tokens | Recent patterns, corrections (7-30d) | Semantic (pgvector) |
| LONG | ~300 tokens | Validated patterns, procedures | Semantic + graph walk |

**Total**: ~1000 tokens (configurable). Compare: mcp-server-memory = unbounded.

## Four BPMN Processes (All Tested - 30/30 Passing)

1. **Capture** - 3 input paths (explicit/auto-detect/session-harvest), dedup, relation linking
2. **Retrieval** - Parallel 3-tier search, composite ranking, greedy budget fill
3. **Consolidation** - "Sleep cycle": short->mid (session end), mid->long (periodic), decay
4. **Contradiction** - 4 types: extends/reinforces/contradicts/supersedes

## Options Considered

| Option | Approach | Verdict |
|--------|----------|---------|
| A: Enhanced Notepad | Extend session_facts | Too minimal |
| B: New MCP Server | Standalone cognitive-memory-server | Best for Desktop |
| C: Memory Gateway | Proxy wrapping mcp-server-memory | Bandaid |
| D: Hybrid project-tools | Add to existing infra | Best for Code |

**Recommendation**: B for Desktop (SQLite, portable), D for Code (PostgreSQL, leverages F129 graph).

## Detailed Design

See [[Cognitive Memory - Process Details]] for full process descriptions, implementation strategy, and open questions.

## Files

| File | Purpose |
|------|---------|
| `processes/lifecycle/cognitive_memory_*.bpmn` | 4 BPMN models |
| `tests/test_cognitive_memory.py` | 30 tests (all passing) |
| `knowledge-vault/.../cognitive-memory-processes.md` | Full process details |

---

**Version**: 1.0
**Created**: 2026-02-25
**Updated**: 2026-02-25
**Location**: docs/cognitive-memory-handoff.md
