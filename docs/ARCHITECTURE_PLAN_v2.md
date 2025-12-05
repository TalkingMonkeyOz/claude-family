# Claude Family Architecture Plan v2.0
**Created:** 2025-12-01
**Updated:** 2025-12-03
**Status:** IMPLEMENTED
**Author:** claude-code-unified (Opus 4.5)

---

## Executive Summary

This document provides a comprehensive architectural analysis of the Claude Family infrastructure. **Major milestone achieved:** Schema consolidation complete - all 4 legacy schemas merged into unified `claude` schema.

---

## Part 1: Current State (Post-Consolidation)

### 1.1 Database Overview

| Schema | Tables | Purpose | Status |
|--------|--------|---------|--------|
| `claude` | **35** | **UNIFIED** - All infrastructure, PM, and MCW data | **ACTIVE - Primary** |
| `nimbus_context` | 12 | Nimbus project API metadata | Active |
| `tax_calculator` | 37 | ATO tax calculation data | Active |
| `public` | ~10 | Legacy/backup tables | Deprecated |

**Previous schemas (now consolidated):**
- ~~`claude_family`~~ → Merged into `claude`
- ~~`claude_pm`~~ → Merged into `claude`
- ~~`claude_mission_control`~~ → Merged into `claude`

### 1.2 Unified `claude` Schema Tables (35 tables)

| Category | Tables | Row Count | Status |
|----------|--------|-----------|--------|
| **Documents** | documents | 1,727 | Needs cleanup (94% orphaned) |
| **Sessions** | sessions | 156 | Active |
| **Build** | build_tasks | 145 | Active |
| **Knowledge** | knowledge | 144 | **Cleaned** (8 standard types) |
| **Components** | components | 110 | Active |
| **Requirements** | requirements | 109 | Active |
| **Work** | work_tasks | 49 | Active |
| **Feedback** | feedback, feedback_comments, feedback_screenshots | 46 | Active |
| **Features** | features | 35 | Active |
| **Projects** | projects | **12** | **Cleaned** (test data removed) |
| **Messages** | messages | 29 | Active |
| **Schema** | schema_registry | 27 | Active |
| **Procedures** | procedures | 22 | Active |
| **Identities** | identities | 12 | Clean (3 active, 9 archived) |
| **Scheduling** | scheduled_jobs, job_run_history | 11 | **Configured** |
| **Activity** | activity_feed | **50** | **New - Backfilled** |
| **Other** | Various | - | See schema_registry |

### 1.3 Data Quality Status

| Table | Before | After | Action Taken |
|-------|--------|-------|--------------|
| **projects** | 33 rows (21 test junk) | 12 real projects | Deleted test data |
| **knowledge** | 38 inconsistent types | 8 standard types | Normalized values |
| **identities** | 12 rows | 12 rows | Clean - no action |
| **activity_feed** | 0 rows | 50 rows | Backfilled + triggers |
| **scheduled_jobs** | 8 jobs | 11 jobs | Added 3 new jobs |

### 1.4 Standardized Knowledge Types

| Type | Count | Description |
|------|-------|-------------|
| `pattern` | 75 | Reusable code/design patterns |
| `gotcha` | 16 | Common pitfalls/traps |
| `best-practice` | 15 | Recommended approaches |
| `bug-fix` | 12 | Bug fixes and workarounds |
| `reference` | 10 | Facts, configs, references |
| `architecture` | 8 | System design decisions |
| `troubleshooting` | 5 | How to fix problems |
| `api-reference` | 3 | API patterns and limitations |

---

## Part 2: Implemented Features

### 2.1 Activity Feed System

**Status:** IMPLEMENTED

Three database triggers now populate `claude.activity_feed`:

1. **Session Start Trigger** - Fires on INSERT to sessions
2. **Session End Trigger** - Fires on UPDATE when session_end changes from NULL
3. **Message Trigger** - Fires on INSERT to messages

```sql
-- Activity feed is now auto-populated
SELECT * FROM claude.activity_feed ORDER BY created_at DESC LIMIT 10;
```

### 2.2 Scheduled Jobs System

**Status:** IMPLEMENTED (11 jobs configured)

| Job | Type | Trigger | Frequency | Priority |
|-----|------|---------|-----------|----------|
| Stale Session Cleanup | maintenance | session_start | daily | 2 |
| sync-anthropic-usage | sync | session_start | daily | 2 |
| Data Quality Check | audit | session_start | weekly | 3 |
| Document Scanner | indexer | session_start | daily | 3 |
| MCP Memory Sync | sync | session_start | 3 days | 4 |
| Schema Registry Sync | sync | session_start | weekly | 4 |
| Review Local LLM Usage | maintenance | session_start | 14 days | 5 |
| User Import Sync | sync | session_start | - | 5 |
| Agent Health Check | health_check | session_start | weekly | 6 |
| Documentation Audit | audit | session_start | monthly | 8 |
| PostgreSQL Backup | backup | schedule | weekly | 10 |

### 2.3 Reminders System

**Status:** IMPLEMENTED

```sql
-- Check due reminders
SELECT title, check_after, reminder_count, status
FROM claude.reminders
WHERE status = 'pending' AND check_after <= NOW();
```

Current reminder: "Remove backward-compat views" - due 2025-12-08

### 2.4 Session Startup Hook

**Status:** IMPLEMENTED

File: `.claude-plugins/claude-family-core/scripts/session_startup_hook.py`

Features:
- Checks `claude.session_state` for saved todo lists
- Checks `claude.reminders` for due items
- Checks `claude.messages` for pending messages
- Checks `claude.scheduled_jobs` for due jobs
- Outputs JSON context for Claude Code

---

## Part 3: Remaining Work

### 3.1 Documents Table Cleanup (Priority: HIGH)

| Issue | Count | Recommended Action |
|-------|-------|-------------------|
| Orphaned (no project_id) | 1,625 (94%) | Audit and assign or delete |
| Duplicates | 338 (20%) | Deduplicate |
| "OTHER" type | 1,291 (75%) | Reclassify |
| Case inconsistency | 33 | Normalize |

### 3.2 Backward Compatibility Views

**Remove after:** 2025-12-08 (reminder set)

Views to drop:
- `claude_pm.projects` → `claude.projects`
- `claude_family.session_history` → `claude.sessions`
- `claude_family.shared_knowledge` → `claude.knowledge`

### 3.3 MCW Integration Points

MCW pages that need testing:
- Activity Feed page → `claude.activity_feed`
- Scheduler page → `claude.scheduled_jobs`
- Reminders page → `claude.reminders`
- Messages page → `claude.messages`

---

## Part 4: Architecture Decisions

### ADR-001: Schema Consolidation

**Status:** Accepted (2025-12-01)
**Decision:** Consolidate 4 schemas into unified `claude` schema
**Rationale:** Reduce complexity, simplify queries, enable better FK relationships

---

## Appendix: Quick Reference Queries

```sql
-- Check activity feed
SELECT * FROM claude.activity_feed ORDER BY created_at DESC LIMIT 10;

-- Check due reminders
SELECT * FROM claude.reminders WHERE status = 'pending' AND check_after <= NOW();

-- Check scheduled jobs status
SELECT job_name, trigger_type, last_run, trigger_condition
FROM claude.scheduled_jobs WHERE is_active = true ORDER BY priority;

-- Check data quality
SELECT
    (SELECT COUNT(*) FROM claude.projects) as projects,
    (SELECT COUNT(*) FROM claude.identities WHERE status = 'active') as active_identities,
    (SELECT COUNT(*) FROM claude.knowledge) as knowledge_items,
    (SELECT COUNT(*) FROM claude.activity_feed) as activity_entries;
```

---

**Document Version:** 2.0
**Previous Version:** 1.0 (2025-12-01)
**Next Review:** 2025-12-10
