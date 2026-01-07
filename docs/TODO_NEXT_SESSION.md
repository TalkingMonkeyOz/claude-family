# Next Session TODO

**Last Updated**: 2026-01-07
**Last Session**: Fixed agent status finalization bug - agents now properly show 'completed' status

---

## Completed This Session

- [x] Tested agent coordination end-to-end (spawn, status reporting, commands)
- [x] Found bug: agent_status not updated to 'completed' when agents finish
- [x] Fixed: Added `finalize_agent_status()` to db_logger.py
- [x] Fixed: Integrated call in orchestrator_prototype.py after log_completion()
- [x] Acknowledged pending messages (commands inventory, schema verification)

---

## Priority 1: Verify Agent Status Fix (NEEDS RESTART)

- [ ] Restart Claude Code to reload MCP servers with fix
- [ ] Spawn a test agent
- [ ] Verify agent_status shows 'completed' at 100% when done
- [ ] Clean up any stale agent_status records

---

## Priority 2: Missing Standards

- [ ] Add sql-postgres standard to `claude.coding_standards`
- [ ] Verify all `context_rules.inject_standards` have matching DB entries
- [ ] Add winforms standard content to database

---

## Priority 3: Session Handoff Improvements

- [ ] Fix /session-resume to query database instead of TODO file
- [ ] Or: Auto-update TODO_NEXT_SESSION.md in /session-end workflow

---

## Priority 4: Expand Native Instructions

- [ ] Add rust.instructions.md to ~/.claude/instructions/
- [ ] Add azure.instructions.md (Bicep, Functions, Logic Apps)
- [ ] Add docker.instructions.md

---

## Backlog

- [ ] Implement forbidden_patterns in standards_validator.py
- [ ] Implement required_patterns checks
- [ ] Review other projects for duplicate session commands

---

## Key Learnings (This Session)

1. **agent_status vs async_tasks**: Two separate tables that both need updating
2. **Orchestrator-side finalization is more reliable** than expecting agents to do it
3. **MCP server restart required** to pick up code changes in orchestrator
4. **Coordination protocol** tells agents to report progress, but not to finalize

---

## Files Modified This Session

- `mcp-servers/orchestrator/db_logger.py` - Added finalize_agent_status() method
- `mcp-servers/orchestrator/orchestrator_prototype.py` - Call finalize after log_completion

---

**Version**: 11.0
**Created**: 2026-01-02
**Updated**: 2026-01-07
**Location**: docs/TODO_NEXT_SESSION.md
