# Next Session TODO

**Last Updated**: 2026-01-07
**Last Session**: Fixed agent status UPSERT - agents now properly show 'completed' even without orchestrator MCP

---

## Completed This Session

- [x] Verified agent status fix needed UPSERT, not just UPDATE
- [x] Root cause: lightweight-haiku has no orchestrator MCP → no status record created
- [x] Fixed `finalize_agent_status()` to use INSERT ... ON CONFLICT DO UPDATE
- [x] Added UNIQUE constraint on `agent_session_id` column
- [x] Updated orchestrator_prototype.py to pass agent_type parameter
- [x] Cleaned up stale agent_status records (manually ran UPSERT)
- [x] Acknowledged pending async task message

---

## Priority 1: Test UPSERT Fix (NEEDS RESTART)

- [ ] Restart Claude Code to reload orchestrator MCP with fix
- [ ] Spawn a lightweight-haiku test agent
- [ ] Verify agent_status shows 'completed' at 100% automatically
- [ ] Confirm both INSERT (new agent) and UPDATE (reporting agent) paths work

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

1. **UPSERT needed, not UPDATE**: Agents without orchestrator MCP can't create status records
2. **PostgreSQL ON CONFLICT**: Requires UNIQUE constraint on the conflict column
3. **lightweight-haiku limitation**: Only has filesystem MCP, no orchestrator access
4. **Two-phase fix**: Code change + database constraint needed together

---

## Files Modified This Session

- `mcp-servers/orchestrator/db_logger.py` - Changed finalize_agent_status() to use UPSERT
- `mcp-servers/orchestrator/orchestrator_prototype.py` - Pass agent_type to finalize_agent_status()

---

**Version**: 12.0
**Created**: 2026-01-02
**Updated**: 2026-01-07
**Location**: docs/TODO_NEXT_SESSION.md
