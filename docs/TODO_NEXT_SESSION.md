# Next Session TODO

**Last Updated**: 2025-12-21
**Last Session**: Agent timeout investigation, hot-reload implementation

## Completed This Session

- **Agent Timeout Investigation**
  - Root cause: Agent specs cached at MCP server startup
  - agent_specs.json changes (600s timeouts) weren't picked up
  - Old cached values (60/120/300s) causing timeouts

- **Hot-Reload Implemented**
  - Added `reload_specs()` method to `AgentOrchestrator`
  - Added `reload_agent_specs` MCP tool to orchestrator server
  - Now can reload specs without restarting Claude Code

- **Agent Metrics Reviewed**
  - coder-haiku: 41% → 83% success (improved after Dec 12)
  - lightweight-haiku: 60% → 100% success
  - python-coder-haiku: Degraded due to old cached timeouts

- **Committed Leftover Files**
  - 13 files from prior session (schema fixes, slash commands, knowledge)

---

## Next Steps (Priority Order)

1. **P1: Restart Claude Code & reload specs** - Pick up new hot-reload tool, then call `reload_agent_specs`
   - This will fix python-coder-haiku timeouts (600s instead of 300s)

2. **P2: Migrate claude-mission-control** - Update code to use `claude.*` instead of deprecated schemas
   - 64 files reference `claude_family.` or `claude_pm.`
   - BLOCKED: Can't drop deprecated tables until MCW migrated

3. **P3: Fix Roslyn MSBuild issue** - Some machines fail to locate MSBuild
   - Options: VS Build Tools install, explicit MSBuild path, or switch to OmniSharp

4. **P4: Sync knowledge vault** - Install psycopg2 in MCP venv, run sync_obsidian_to_db.py

---

## Key Learnings

| Learning | Details |
|----------|---------|
| MCP config cached at startup | Agent specs loaded once - need hot-reload for changes |
| Agent metrics improved | coder-haiku 41%→83% after Dec 12 config changes |
| Timeout root cause | Old cached values (60/120/300) vs spec values (600) |
| Use `ls` not `dir` | Git Bash on Windows uses Unix commands |

---

## Files Changed

| File | Change |
|------|--------|
| `mcp-servers/orchestrator/orchestrator_prototype.py` | Added `reload_specs()` method |
| `mcp-servers/orchestrator/server.py` | Added `reload_agent_specs` MCP tool |

---

**Version**: 9.0
**Status**: Hot-reload implemented, agent timeouts will be fixed after restart
