# Next Session TODO

**Last Updated**: 2025-12-13
**Last Session**: Comprehensive orchestrator review and cleanup

## Completed This Session
- Full MCP orchestrator analysis (98 sessions, usage data, success rates)
- **Reduced agents from 31 to 13** (58% reduction in dead code)
- Fixed Decimal JSON serialization bug in server.py get_mcp_stats
- Fixed check-messages.md (mcp__messaging__ -> mcp__orchestrator__)
- Simplified global session-start.md (removed old schema refs)
- Deleted 6 duplicate slash commands from project folder
- Re-added essential tester agents: tester-haiku, web-tester-haiku, ux-tax-screen-analyzer
- Pushed all changes to remote

## Key Findings from Analysis

### Agent Usage Stats (Top 5):
| Agent | Sessions | Success Rate | Issue |
|-------|----------|--------------|-------|
| coder-haiku | 28 | 46% | Investigate failures |
| python-coder-haiku | 25 | 80% | Good |
| lightweight-haiku | 12 | 83% | Good |
| reviewer-sonnet | 8 | 50% | Moderate |
| researcher-opus | 5 | 20% | Expensive failures |

### Agents Kept (13):
- coder-haiku, python-coder-haiku, lightweight-haiku
- reviewer-sonnet, security-sonnet, analyst-sonnet
- architect-opus, planner-sonnet, researcher-opus
- research-coordinator-sonnet
- tester-haiku, web-tester-haiku, ux-tax-screen-analyzer

### Agents Removed (18):
- All unused: debugger-haiku, nextjs-tester-haiku, screenshot-tester-haiku, etc.
- Local models: deepseek, qwen (0 usage)
- Most coordinators (0 usage)

## Next Steps
1. **Investigate coder-haiku 46% failure rate** - Why is the most-used agent failing half the time?
2. **Restart MCP servers** - Changes take effect on restart
3. **Test ux-tax-screen-analyzer** - Verify playwright integration works
4. **Consider removing researcher-opus** - 20% success at $3.63 per task is expensive
5. **Run overdue jobs** - Link Checker and Orphan Document Report still pending

## Notes for Next Session
- MCP orchestrator caches agent_specs.json at startup - restart needed for changes
- All projects share the same orchestrator via global ~/.claude/mcp.json
- Session commands now inherit from global ~/.claude/commands/ (no project duplicates)
- Messaging system IS being used (84 messages in DB)

## Architecture Note
```
Global Config (~/.claude/mcp.json)
  └── orchestrator MCP
        └── agent_specs.json (13 agents)
              ├── Coders: coder-haiku, python-coder-haiku, lightweight-haiku
              ├── Reviewers: reviewer-sonnet, security-sonnet
              ├── Research: analyst-sonnet, researcher-opus, research-coordinator-sonnet
              ├── Planning: architect-opus, planner-sonnet
              └── Testing: tester-haiku, web-tester-haiku, ux-tax-screen-analyzer
```
