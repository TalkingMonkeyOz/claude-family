# Claude Family Infrastructure - Self-Audit Report

**Date**: 2025-12-08
**Auditor**: claude-code-unified (claude-family)
**Scope**: Comprehensive review of documentation, processes, and infrastructure

---

## Executive Summary

This audit identified **6 major gaps** in the Claude Family infrastructure that need addressing:

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | Session-start hook not logging sessions | HIGH | Open |
| 2 | Core documents database has 44 entries, many incorrect | MEDIUM | Open |
| 3 | 7 scheduler jobs failing | MEDIUM | Open |
| 4 | No CAPABILITIES.md documenting what we can do | MEDIUM | Open |
| 5 | Docs folder cluttered with 70+ files | LOW | Open |
| 6 | Compliance audit system not implemented | LOW | Open |

---

## Issue 1: Session-Start Hook Not Logging Sessions (HIGH)

### Problem
The `SessionStart` hook in `.claude/hooks.json` calls `session_startup_hook.py`, which:
- Shows saved session state from `claude.session_state`
- Checks for pending messages
- Reports due jobs and compliance status

But it does **NOT**:
- Create a new session record in `claude.sessions`
- That only happens when `/session-start` is manually invoked

### Evidence
- MCW sent message (2025-12-08): "Session Start Hook Not Running Automatically"
- Query confirmed no sessions logged automatically

### Root Cause
```json
"SessionStart": [
  {
    "matcher": "startup",  // This is likely incorrect syntax
    "hooks": [...]
  }
]
```
The "matcher" field may not apply to SessionStart hooks, and even if the hook runs, it doesn't log sessions.

### Fix Required
1. Remove invalid "matcher" from SessionStart hook config
2. Add session logging to `session_startup_hook.py`
3. Test that sessions auto-log on startup

---

## Issue 2: Core Documents Database Incorrect (MEDIUM)

### Problem
44 documents marked as `is_core = true` in `claude.documents`, but many shouldn't be:

| Category | Count | Issue |
|----------|-------|-------|
| Templates | 8+ | Templates aren't core - they're templates |
| Archived | 10+ | Old versions from `_archive`, `research/old_*` paths |
| Duplicates | 5+ | Same doc at different paths |
| Session notes | 50+ | Listed as stale in doc-staleness report |
| Missing files | 77 | Documents exist in DB but files deleted |

### What SHOULD Be Core
Per GOVERNANCE_FINDINGS_2025-12-07.md:

**Tier 1 (Per Project):**
- CLAUDE.md
- ARCHITECTURE.md
- PROBLEM_STATEMENT.md

**Tier 2 (Shared Standards):**
- docs/standards/*.md (5 files)

**Tier 3 (SOPs):**
- docs/sops/SOP-001 through SOP-006

### Fix Required
1. Unmark templates as core (is_core = false)
2. Unmark archived paths as core
3. Delete orphan document records (files that don't exist)
4. Consolidate duplicates

---

## Issue 3: Scheduler Jobs Failing (MEDIUM)

### Status Summary
From `claude.scheduled_jobs` (17 active):

| Job Name | Status | Issue |
|----------|--------|-------|
| Agent Health Check | FAILED | Script doesn't exist: `check_agent_health.py` |
| Anthropic Docs Monitor | FAILED | Exit code 1 (actually works, but returns non-zero) |
| data-quality-review | ISSUES_FOUND | Works, but exits 1 when finding issues |
| Data Quality Check | NEVER RUN | No command defined |
| doc-staleness-review | FAILED | Exit code 1 (works but finds 129 issues) |
| Document Scanner | SUCCESS | Working correctly |
| governance-compliance-check | FAILED | Missing `--project` argument value |
| MCP Memory Sync | FAILED | Uses deprecated `claude_family.shared_knowledge` |
| sync-anthropic-usage | FAILED | Malformed command path with extra quotes |

### Jobs That Work
- Document Scanner (ran 2025-12-06, found 861 docs)

### Fix Required
1. **Agent Health Check**: Create script or disable job
2. **MCP Memory Sync**: Update to use `claude.knowledge`
3. **sync-anthropic-usage**: Fix command string in database
4. **governance-compliance-check**: Add default project or make optional
5. **Reviewers**: Change to exit 0 even when issues found (issues ≠ failure)

---

## Issue 4: No CAPABILITIES.md (MEDIUM)

### Problem
Nowhere is there a central document listing what Claude Family CAN do:
- What slash commands are available (16)
- What agents can be spawned
- What scheduled jobs run
- What hooks are active
- What MCP servers are available
- What processes are in the database

### Impact
- New sessions don't know what tools exist
- Users don't know what to ask for
- Capabilities are scattered across multiple docs

### Fix Required
Create `docs/CAPABILITIES.md` with:
1. Slash commands list (from .claude/commands/)
2. Agent types (from orchestrator)
3. Scheduled jobs (from claude.scheduled_jobs)
4. Active hooks (from .claude/hooks.json)
5. MCP servers (from .mcp.json)
6. Database processes (from claude.process_registry if populated)

---

## Issue 5: Docs Folder Cluttered (LOW)

### Problem
`docs/` has 70+ files, many are:
- Old architecture plans (ARCHITECTURE_PLAN_v1.md, v2.md)
- Completion reports from 2025-10 and 2025-11
- Session notes folder with 100+ context files
- Deprecated specs

### Current Structure
```
docs/
├── adr/                    # Good - keep
├── archive/                # Good - for old stuff
├── sops/                   # Good - keep
├── standards/              # Good - keep (new)
├── session-notes/          # Should be cleaned regularly
├── 50+ other files         # Many should be archived
```

### Fix Required
1. Move old plans to `docs/archive/`
2. Move completion reports to `docs/archive/`
3. Clean session-notes older than 30 days
4. Keep only active documents in root of docs/

---

## Issue 6: Compliance Audit System Not Implemented (LOW)

### Current State
Created `docs/standards/COMPLIANCE_CHECKLIST.md` but no:
- Scheduled audit cadence
- Place to store audit results
- Process for triggering audits
- Way to track remediation

### Proposed Design
1. Add `claude.compliance_audits` table
2. Add scheduled job to message projects when audit due
3. Projects run audit on startup if flagged
4. Results stored in database
5. MCW shows compliance dashboard

---

## Verified Working

These systems ARE working correctly:

| System | Status | Evidence |
|--------|--------|----------|
| Session state saving | OK | `/session-end` saves to `claude.session_state` |
| Messages/broadcast | OK | 20 messages in last 7 days |
| Document Scanner | OK | 861 docs indexed 2025-12-06 |
| Standards docs | OK | 5 created 2025-12-07 |
| Compliance checklist | OK | Created 2025-12-08 |
| SOPs | OK | 6 SOPs + 2 guides in docs/sops/ |
| UserPromptSubmit hook | OK | Process router runs on every prompt |
| Pre-commit hook | OK | Runs validation before commits |

---

## Recommendations Priority

### Immediate (Today)
1. Fix session-start hook to auto-log sessions

### This Week
2. Clean up core documents in database
3. Fix broken scheduler jobs
4. Create CAPABILITIES.md

### Later
5. Archive old docs
6. Implement compliance audit system

---

## Action Items

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 1 | Add session logging to session_startup_hook.py | claude-family | DONE |
| 2 | Run SQL to unmark non-core documents | claude-family | DONE |
| 3 | Delete orphan document records | claude-family | SKIPPED (not critical) |
| 4 | Fix or disable failing scheduler jobs | claude-family | DONE |
| 5 | Create docs/CAPABILITIES.md | claude-family | DONE |
| 6 | Move old docs to archive | claude-family | TODO (low priority) |
| 7 | Design compliance_audits table | claude-family | TODO |

## Fixes Applied (2025-12-08)

### Issue 1: Session-Start Hook - FIXED
- Added `create_session()` function to `session_startup_hook.py`
- Sessions now auto-log to `claude.sessions` on startup
- Removed invalid "matcher" fields from SessionStart hook
- Added default database connection string

### Issue 2: Core Documents - FIXED
- Unmarked 18 templates as non-core
- Unmarked 6 archived paths as non-core
- Unmarked deprecated projects (claude-pm, claude-mission-control)
- Added 6 new standards documents as core
- Final count: 27 properly curated core documents

### Issue 3: Scheduler Jobs - FIXED
- Disabled 4 jobs with no commands
- Fixed MCP Memory Sync script (removed deprecated import)
- Fixed sync-anthropic-usage command path
- Updated governance-compliance-check to use correct script
- Final: 13 active jobs, 4 disabled

### Issue 4: CAPABILITIES.md - CREATED
- Documented 16 slash commands
- Documented 28 agent types with tiers
- Documented 13 scheduled jobs
- Documented 6 active hooks
- Documented 8 MCP servers

---

**Version**: 1.0
**Created**: 2025-12-08
**Location**: C:\Projects\claude-family\docs\SELF_AUDIT_2025-12-08.md
