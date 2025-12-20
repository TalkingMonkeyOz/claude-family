# Next Session TODO

**Last Updated**: 2025-12-20
**Last Session**: Fixed observability - PostToolUse hook, timeout source, mcp_usage_logger

## Completed This Session

- **Fixed PostToolUse hook** - added required `matcher` property (`mcp__.*`)
- **Fixed timeout source** - `recommend_agent()` now uses `get_spec_timeout()` from agent_specs.json
- **Fixed mcp_usage_logger.py** - correct input format (`tool_response` not `tool_output`), UUID validation
- Verified enforcement_log is working (10+ entries today)
- Checked agent success rates (58-83%, all failures are timeouts)

---

## Next Steps (Priority Order)

1. **Restart Claude Code** - hooks.json changes require restart to take effect
   - Verify PostToolUse hook fires after restart
   - Check `claude.mcp_usage` for new entries

2. **Monitor agent success rates** - should improve with new 600s+ timeouts
   - Check in a few days: `SELECT agent_type, success, COUNT(*) FROM claude.agent_sessions WHERE spawned_at > NOW() - INTERVAL '3 days' GROUP BY 1, 2;`

3. **Check Claude Family Manager progress** - Phase 1 scaffold should be underway
   - Switch to `C:\Projects\claude-family-manager` project
   - Review Phase 1 status

---

## Key Learnings

| Learning | Details |
|----------|---------|
| PostToolUse requires matcher | Even for "match all", must include `"matcher": "*"` or `"matcher": "mcp__.*"` |
| Dual timeout sources | `recommend_agent()` was hardcoding timeouts, overriding agent_specs.json |
| PostToolUse input format | Uses `tool_response` not `tool_output`, includes `session_id` and `cwd` |

---

## Files Changed (Uncommitted)

| File | Change |
|------|--------|
| `mcp-servers/orchestrator/server.py` | Added `get_spec_timeout()`, replaced 14 hardcoded timeouts |
| `.claude/hooks.json` | Fixed PostToolUse hook config |
| `scripts/mcp_usage_logger.py` | Fixed input format, UUID validation, project extraction |

---

**Version**: 3.8
**Status**: Observability fixes complete, need restart to verify
