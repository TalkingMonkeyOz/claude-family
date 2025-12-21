# Next Session TODO

**Last Updated**: 2025-12-21
**Last Session**: MCW schema migration completed

## Completed This Session

- **P1: Agent Specs Reloaded** - Called `reload_agent_specs` MCP tool
  - All 14 agents now have 600s timeouts active

- **P2: MCW Schema Migration** - Migrated claude-mission-control to `claude.*` schema
  - 121 replacements across 19 files
  - All `claude_family.*` → `claude.*` with correct table names
  - All `claude_pm.*` → `claude.*` with correct table names
  - **Exception**: `procedures.py` reverted to use `claude_family.procedure_registry` (different schema than `claude.process_registry`)
  - All 9 database modules tested and passing

- **P4: Knowledge Vault Synced** - 1 new file synced

---

## Next Steps (Priority Order)

1. **Test MCW End-to-End** - Run the app and verify all tabs work with new schema
   - Location: `C:\Projects\claude-mission-control`
   - Run: `python src/main.py` or `run.bat`

2. **Drop Deprecated Views (Optional)** - Once MCW confirmed working
   - Views in `claude_family` and `claude_pm` schemas can be dropped
   - Keep tables: `claude_family.procedure_registry`, `claude_pm.project_feedback_comments`

3. **P3: Fix Roslyn MSBuild issue** - Environment issue on some machines
   - Low priority - only affects machines without Visual Studio

---

## Key Learnings

| Learning | Details |
|----------|---------|
| Views provide backwards compat | Deprecated schemas have views pointing to `claude.*` tables |
| Table name changes | `session_history` → `sessions`, `project_workspaces` → `workspaces`, etc. |

---

**Version**: 11.0
**Status**: MCW migrated to claude.* schema, needs E2E testing
