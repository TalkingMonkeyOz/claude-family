# Enforcement Hierarchy - Claude Governance System

**Document Type**: SOP
**Created**: 2025-12-04
**Status**: Active

---

## Overview

The Claude Governance System uses a hierarchy of enforcement mechanisms, from soft suggestions to hard database constraints. Each level provides different guarantees.

---

## Enforcement Levels

```
WEAK ──────────────────────────────────────────────────────► STRONG

CLAUDE.md    Slash        Hooks        DB            Reviewer
(guidance) → Commands  →  (block)  →  Constraints → Agents
             (manual)                  (reject)     (verify)
```

### Level 1: CLAUDE.md (Guidance)

**Type**: Soft suggestion
**Enforcement**: None - relies on Claude following instructions
**When blocked**: Never

**Examples**:
- "Check column_registry before INSERT"
- "Use TodoWrite for task tracking"
- "Follow session protocol"

**Limitations**:
- Claude may ignore or forget
- No verification of compliance
- User must notice violations

---

### Level 2: Slash Commands (Manual)

**Type**: Structured prompts
**Enforcement**: Must be explicitly invoked
**When blocked**: Never (but may warn)

**Examples**:
- `/session-start` - Session initialization
- `/check-compliance` - Verify governance
- `/retrofit-project` - Add missing docs

**Files**: `.claude/commands/*.md`

**Limitations**:
- User/Claude must remember to run
- No automatic enforcement
- Can be skipped

---

### Level 3: Hooks (Automated Block)

**Type**: Pre/post tool scripts
**Enforcement**: Automatic on tool use
**When blocked**: Script returns non-zero exit code

**Current Hooks**:

| Hook Type | Trigger | Script | Action |
|-----------|---------|--------|--------|
| PreToolUse | Write CLAUDE.md | validate_claude_md.py | Warn on violations |
| PreToolUse | Edit CLAUDE.md | validate_claude_md.py | Warn on violations |
| PreToolUse | mcp__postgres__execute_sql | validate_db_write.py | Block invalid column values |
| PreToolUse | mcp__postgres__execute_sql | validate_phase.py | Block build_task if wrong phase |
| SessionStart | startup | session_startup_hook.py | Load state, check messages |
| SessionStart | resume | session_startup_hook.py | Resume with saved state |
| SessionEnd | Any | check_doc_updates.py | Warn if docs stale |
| SessionEnd | Any | Prompt | Remind to run /session-end |

**Files**: `.claude/hooks.json`

**Capabilities**:
- Can block operations
- Can add warnings
- Can inject context
- Runs automatically

**Limitations**:
- Must be configured per project
- Can be bypassed by disabling hooks
- Only triggers on specific tools

---

### Level 4: Database Constraints (Hard Reject)

**Type**: PostgreSQL CHECK constraints and triggers
**Enforcement**: Automatic on INSERT/UPDATE
**When blocked**: Always - operation fails

**Current Constraints**:

| Table | Column | Type | Valid Values |
|-------|--------|------|--------------|
| projects | status | CHECK | active, paused, archived, completed |
| projects | phase | CHECK | idea, research, planning, implementation, maintenance, archived |
| projects | priority | CHECK | 1-5 |
| feedback | feedback_type | Trigger | bug, design, question, change, idea |

**Triggers**:
- `trg_validate_feedback_type` - Validates against column_registry
- `trg_validate_project_status` - Validates status and phase

**Capabilities**:
- Cannot be bypassed (except by DBA)
- Provides clear error messages
- Documents valid values in column_registry

**Limitations**:
- Only validates database operations
- Cannot enforce file-level rules
- Requires manual setup per table

---

### Level 5: Reviewer Agents (Verification)

**Type**: AI-powered review
**Enforcement**: Async verification
**When blocked**: Report findings, may request fixes

**Planned Agents**:
- Code compliance reviewer
- Documentation staleness checker
- Data quality auditor

**Status**: Phase F (not yet implemented)

---

## Quick Reference

### Where to Check Valid Values

```sql
-- Check all constrained columns
SELECT table_name, column_name, valid_values, description
FROM claude.column_registry
ORDER BY table_name, column_name;
```

### How to Add New Constraint

1. **Add to column_registry**:
```sql
INSERT INTO claude.column_registry (table_name, column_name, data_type, valid_values, description)
VALUES ('table', 'column', 'varchar(50)', '["val1", "val2"]'::jsonb, 'Description');
```

2. **Add CHECK constraint** (simple):
```sql
ALTER TABLE claude.tablename
ADD CONSTRAINT chk_tablename_column
CHECK (column IN ('val1', 'val2'));
```

3. **Or create trigger** (complex):
```sql
CREATE TRIGGER trg_validate_column
    BEFORE INSERT OR UPDATE ON claude.tablename
    FOR EACH ROW
    EXECUTE FUNCTION claude.validate_column_function();
```

---

## Enforcement Decision Guide

| Scenario | Recommended Level |
|----------|-------------------|
| Style preference | CLAUDE.md |
| Complex workflow | Slash Command |
| File operations | Hook |
| Data integrity | DB Constraint |
| Quality assurance | Reviewer Agent |

---

## Related Documents

- `docs/CLAUDE_GOVERNANCE_SYSTEM_PLAN.md` - Full governance plan
- `docs/DATA_GATEWAY_MASTER_PLAN.md` - Data quality system
- `.claude/hooks.json` - Hook configuration
- `claude.column_registry` - Valid values registry

---

**Version**: 1.1
**Updated**: 2025-12-06
**Maintained by**: Claude Family Infrastructure
