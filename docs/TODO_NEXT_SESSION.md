# Next Session TODO

**Last Updated**: 2025-12-20
**Last Session**: Fixed startup commands, orchestrator timeouts, enforcement logging, MCP usage tracking

## Completed This Session

- Fixed Unix-style `wc -l` command in session-resume.md (was breaking on Windows)
- Fixed orchestrator timeout schema: max was 600s but specs go up to 1800s (server.py)
- Implemented enforcement_log writes in process_router.py (was 0 rows)
- Fixed MCP usage tracking: removed broken `mcp__*` wildcard matcher, now uses no-matcher approach
- Previous: Added 14 regex triggers for slash commands, fixed agent timeouts

---

## Next Steps (Priority Order)

1. **Create MCW dashboard** - Data exists but no visualization
2. **Verify enforcement_log is populating** - Check after a few sessions
3. **Verify MCP usage logging works** - Check claude.mcp_usage after next session
4. **Agent success rate monitoring** - Was 0% recently, check if fixes helped

---

## Notes for Next Session

- Observability fixes completed:
  - Orchestrator now allows timeouts up to 1800s (was capped at 600)
  - enforcement_log now logs process/standard/knowledge injection
  - MCP usage hook fixed (removed invalid `mcp__*` glob pattern)
  - session-resume.md fixed for Windows compatibility
- Task breakdown pattern recommended:
  1. Use planner-sonnet first to break down complex tasks
  2. Spawn multiple lightweight-haiku/coder-haiku in parallel
  3. Use reviewer-sonnet to validate combined work
- Don't use researcher-opus for large tasks (17% success rate)

---

## Key Fixes This Session

| Fix | Details |
|-----|---------|
| session-resume.md | Removed `wc -l` (Unix only), platform-agnostic now |
| server.py timeout | max 600 → 1800 (matches agent specs) |
| enforcement_log | Added `log_enforcement()` function, logs 3 types |
| MCP usage hook | Removed broken `mcp__*` matcher, logs all then filters |

---

**Version**: 3.6
**Status**: Observability fixes deployed, pending verification
