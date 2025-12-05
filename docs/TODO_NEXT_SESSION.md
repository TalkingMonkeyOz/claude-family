# TODO - Next Session

**Updated:** 2025-12-04 (evening)
**For:** claude-code-unified
**Project:** claude-family

---

## ✅ COMPLETED TODAY (2025-12-04)

### Claude Governance System - ALL 6 PHASES DONE

**Phase A: Core Documents**
- [x] Created PROBLEM_STATEMENT.md for claude-family
- [x] Created ARCHITECTURE.md for claude-family
- [x] Updated CLAUDE.md to governance standard
- [x] Added `phase` column to projects table
- [x] Created governance views (v_project_governance, v_core_documents, v_project_work_summary)

**Phase B: Templates & Actions**
- [x] Created `claude.actions` table (6 actions)
- [x] Created CLAUDE.template.md
- [x] Created PROBLEM_STATEMENT.template.md
- [x] Created ARCHITECTURE.template.md
- [x] Created /project-init slash command
- [x] Created /check-compliance slash command
- [x] Created /retrofit-project slash command

**Phase C: Enforcement**
- [x] Created validate_claude_md.py (pre-tool hook)
- [x] Updated session_startup_hook.py with compliance check
- [x] Added DB triggers for feedback_type, project status/phase
- [x] Created ENFORCEMENT_HIERARCHY.md SOP

**Phase D: MCW Integration**
- [x] Sent message to MCW with integration details
- [x] Created MCW_GOVERNANCE_API_SPEC.md

**Phase E: Retrofit Projects**
- [x] claude-family → 100% compliant
- [x] ATO-Tax-Agent → 100% compliant (added PROBLEM_STATEMENT.md)
- [x] mission-control-web → 100% compliant (added PROBLEM_STATEMENT.md)
- [x] nimbus-user-loader → 100% compliant (added PROBLEM_STATEMENT.md)

**Phase F: Auto-Reviewers**
- [x] Created `claude.reviewer_specs` table
- [x] Created `claude.reviewer_runs` table
- [x] Created reviewer_doc_staleness.py
- [x] Created reviewer_data_quality.py
- [x] Added 3 reviewer jobs to scheduled_jobs
- [x] Created /review-docs and /review-data commands

---

## PENDING ITEMS

### Outstanding (from DB)
- 3 pending messages (check with /inbox-check)
- 12 new feedback items
- 14 scheduled jobs due to run

### Priority 5: Cleanup (Dec 8, 2025 - Reminder Set)
- [ ] Remove backward-compat views
- [ ] Drop old schemas: `claude_family`, `claude_pm`, `claude_mission_control`
- **Note**: Reminder already set for Dec 8

### Nice to Have
- [ ] Clean up test data found by data-quality reviewer (19 issues)
- [ ] Run doc-staleness review to update old docs

---

## Current State Summary

**Governance System:**
- All 4 projects at 100% compliance
- Templates ready for new projects
- Enforcement hooks active
- Auto-reviewers scheduled

**New Database Objects:**
- `claude.actions` - 6 governance actions
- `claude.reviewer_specs` - 4 reviewer definitions
- `claude.reviewer_runs` - Execution history
- `claude.projects.phase` - New column
- 3 new views for governance

**New Files:**
- 3 templates in `templates/`
- 5 slash commands in `.claude/commands/`
- 2 reviewer scripts in `scripts/`
- 3 documentation files in `docs/`

---

## Quick Reference

```sql
-- Check governance compliance
SELECT project_name, compliance_pct FROM claude.v_project_governance;

-- Check reviewer runs
SELECT reviewer_type, started_at, issues_found FROM claude.reviewer_runs ORDER BY started_at DESC LIMIT 5;

-- Check available actions
SELECT action_name, display_name FROM claude.actions WHERE available_in_mcw = true;

-- Check scheduled jobs
SELECT job_name, schedule, last_run FROM claude.scheduled_jobs WHERE is_active = true;
```

---

**Last Verified:** 2025-12-04 evening session
