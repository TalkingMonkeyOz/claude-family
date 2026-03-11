---
projects:
- claude-family
tags:
- architecture
- specification
- critical
synced: false
---

# System Functional Specification

**Purpose**: End-to-end specification of how the Claude Family system works.

**Status**: DRAFT - Under verification

---

## System Flow

```
User runs `claude` in project dir
        ↓
Config regenerated from database → [[Config Management SOP]]
        ↓
SessionStart hook fires → [[Session Lifecycle - Session Start]]
        ↓
Session ID created & stored → [[#Session ID Lifecycle]]
        ↓
Context loaded → [[Session Architecture]]
        ↓
Work happens (hooks fire) → [[Claude Hooks]]
        ↓
Session ends → [[Session Lifecycle - Session End]]
```

---

## Core Subsystems

| Subsystem | Document | Status |
|-----------|----------|--------|
| Launch & Config | [[Config Management SOP]] | ✅ Verified |
| Session Lifecycle | [[Session Architecture]] | ✅ Verified |
| Hook System | [[Claude Hooks]] | ✅ Verified |
| Database Schema | [[Database Architecture]] | ✅ FK docs added |
| MCP Integration | [[MCP configuration]] | ✅ Verified |
| RAG Self-Learning | [[#Self-Learning RAG]] | ✅ Implemented |
| Error Handling | [[#Known Issues]] | 🔴 Active issues |

---

## Session ID Lifecycle

**CRITICAL BUG**: Session continuation doesn't trigger SessionStart.

| Step | Status | Evidence (verified 2026-01-04) |
|------|--------|--------------------------------|
| Claude Code provides session_id | ✅ | stdin JSON contains session_id |
| SessionStart creates DB record | ⚠️ | Only on NEW sessions, not continuations |
| Other hooks receive session_id | ✅ | All hooks get session_id from Claude Code |
| Session exists when hooks fire | ❌ | Continuation = no SessionStart = no DB record |

**Root Cause**: When Claude Code continues a conversation (resume/compact), it uses the same session_id but SessionStart hook doesn't fire. Hooks then try to INSERT with a session_id that doesn't exist.

**Fix needed**: Lazy session creation in hooks - check if session exists, create if not.

---

## Known Issues

| Issue | Impact | Status |
|-------|--------|--------|
| Session continuation bypass | FK violations | ✅ Fixed (lazy session creation) |
| 176 orphaned agent_sessions | Data quality | ⏳ Backfill needed |
| Duplicate FK on mcp_usage | Schema ambiguity | ✅ Fixed (dropped) |
| history.jsonl.lock EBADF | Random errors | Report to Anthropic |

---

## Silent Failures

**How to detect**: Check `~/.claude/hooks.log` for WARNING/ERROR entries.

| Component | Failure Mode | Detection | Impact |
|-----------|--------------|-----------|--------|
| `get_db_connection()` | Returns None silently | Check logs for "DB connection failed" | No logging, data loss |
| RAG query | Falls back to empty results | "RAG pre-load: 0 docs" in logs | Missing context |
| MCP usage logger | Logs warning, continues | "MCP usage logging failed" | Missing analytics |
| Config generator | May use stale config | Compare file timestamps | Outdated settings |

**Health Check**: Run `grep -iE "warning|error|failed" ~/.claude/hooks.log | tail -20`

---

## Quick Health Check

```sql
-- Recent sessions
SELECT COUNT(*), project_name FROM claude.sessions
WHERE session_start > NOW() - INTERVAL '24 hours'
GROUP BY project_name;

-- FK violations
-- grep "foreign key constraint" ~/.claude/hooks.log | tail -10

-- Orphaned records
SELECT COUNT(*) FROM claude.agent_sessions WHERE parent_session_id IS NULL;
```

---

## Self-Learning RAG

The RAG system continuously improves through feedback capture and analysis.

### Learning Loop

```
QUERY → RETRIEVE → DELIVER → CAPTURE FEEDBACK → ANALYZE → OPTIMIZE
                                    ↓
                            (Loop back to QUERY)
```

### Feedback Capture (3 Types)

| Type | Signal | Confidence | Stored In |
|------|--------|------------|-----------|
| Explicit | User rates "helpful" at session end | High (0.9) | `rag_feedback` |
| Implicit | Query rephrase within 3 prompts | Medium (0.7) | `rag_feedback` |
| Implicit | No mention of returned doc | Low (0.5) | `rag_feedback` |
| Implicit | User says "wrong doc", "not helpful" | High (0.9) | `rag_feedback` |

### Miss Counter (Doc Quality)

Docs that fail 3 times get flagged for review:

| Miss Count | Action |
|------------|--------|
| 1-2 | Auto re-embed with better keywords |
| 3 | Flag for human review |
| 3+ | Notify user, pause auto-retrieval |

### Database Tables

| Table | Purpose |
|-------|---------|
| `claude.rag_feedback` | Feedback signals (explicit + implicit) |
| `claude.rag_doc_quality` | Miss counter, quality scoring |
| `claude.rag_query_patterns` | Learned query-doc associations |

### Analytics Queries

```sql
-- Docs that consistently fail
SELECT doc_path, miss_count, quality_score, flagged_for_review
FROM claude.rag_doc_quality WHERE miss_count >= 2;

-- Feedback by signal type
SELECT signal_type, COUNT(*), AVG(signal_confidence)
FROM claude.rag_feedback GROUP BY signal_type;

-- Optimal threshold analysis
SELECT AVG(r.top_similarity) FILTER (WHERE f.helpful)
FROM claude.rag_usage_log r
JOIN claude.rag_feedback f ON r.log_id = f.log_id;
```

---

## Related Documents

- [[Database Architecture]] - Schema reference (76 tables)
- [[Database FK Constraints]] - All 42+ FK constraints
- [[Session Architecture]] - Session lifecycle
- [[Claude Hooks]] - Hook implementation
- [[Config Management SOP]] - Config generation
- [[Family Rules]] - Mandatory procedures

---

**Version**: 1.2
**Created**: 2026-01-04
**Updated**: 2026-01-04 (RAG Self-Learning added)
**Location**: knowledge-vault/Claude Family/System Functional Specification.md
