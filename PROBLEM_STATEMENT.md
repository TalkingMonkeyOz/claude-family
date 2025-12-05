# Problem Statement - Claude Family Infrastructure

**Project**: claude-family
**Created**: 2025-12-04
**Status**: Active

---

## The Problem

When building software with AI coding assistants (Claude), users face several challenges:

### 1. Inconsistent Project Structure
- Each project has different file organization
- Documentation scattered or missing
- No standard for what files should exist

### 2. AI Works Ad-Hoc
- Claude instances don't follow consistent procedures
- No enforcement of coding standards
- Work tracking scattered across multiple systems
- Same mistakes repeated across sessions

### 3. Knowledge Loss Between Sessions
- Context lost when session ends
- No reliable way to resume where left off
- Previous decisions not documented
- User must re-explain requirements

### 4. Data Quality Issues
- Database tables filled with inconsistent values
- Test data mixed with production data
- No validation on what gets written
- Multiple tables for similar purposes (confusion)

### 5. Documentation Drift
- Architecture docs become stale
- Multiple versions with unclear "current"
- No alerts when docs need updating
- Core docs buried among hundreds of files

---

## Who Has This Problem

**Primary**: John (User) - Non-coder building software with Claude
**Secondary**: Claude instances - Need structure to work effectively
**Tertiary**: Future users of Claude Family framework

---

## Current Solution (Before This Project)

- Manual creation of project files
- Hope Claude reads CLAUDE.md
- Manually track work in various tables
- Periodically clean up data
- Re-explain context each session

**Problems with current approach**:
- Time-consuming
- Error-prone
- Inconsistent results
- User frustration

---

## Proposed Solution

A **Claude Governance System** that provides:

### 1. Project Templates
- Standard folder structure
- Required documents (CLAUDE.md, PROBLEM_STATEMENT.md, ARCHITECTURE.md)
- `/project-init` command to create everything

### 2. Enforced Procedures
- Hooks that BLOCK invalid actions
- Database constraints reject bad data
- Phase gates require approval before proceeding
- Auto-reviewer agents check quality

### 3. Knowledge Persistence
- Session state saved to database
- CLAUDE.md updated each session
- Architecture decisions recorded as ADRs
- Activity feed shows what happened

### 4. Data Quality
- column_registry defines valid values
- CHECK constraints enforce at database level
- Clear rules: "ideas go here, bugs go there"
- Automated cleanup of test data

### 5. Living Documentation
- Staleness alerts when docs old
- Version tracking (is_current_version flag)
- Architecture as map to sub-docs
- MCW shows document health

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Projects with required docs | ~25% | 100% |
| Invalid data blocked | 0% | 100% |
| Session context preserved | Partial | Full |
| Doc staleness alerts | None | Automated |
| Time to start new project | ~1 hour | 15 min |
| Procedures followed | Ad-hoc | Enforced |

---

## Constraints

1. **Must work with Claude Code** - Use CLAUDE.md, hooks, slash commands
2. **PostgreSQL backend** - All state in `claude` schema
3. **MCW for visibility** - UI in Mission Control Web
4. **Non-breaking** - Retrofit existing projects gradually
5. **Simple for user** - John shouldn't need to understand internals

---

## Out of Scope

- Multi-user collaboration (single user for now)
- Cloud deployment (local development only)
- Mobile access (desktop only)
- Real-time sync between instances (message-based coordination)

---

## Related Documents

- `ARCHITECTURE.md` - System design
- `docs/CLAUDE_GOVERNANCE_SYSTEM_PLAN.md` - Implementation plan
- `docs/DATA_GATEWAY_MASTER_PLAN.md` - Data quality system
- `docs/sop/` - Standard operating procedures

---

**Version**: 1.0
**Updated**: 2025-12-04
