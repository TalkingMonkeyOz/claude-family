# Next Session TODO

**Last Updated**: 2025-12-20
**Last Session**: Observability fixes - added slash command regex triggers, documented task breakdown pattern

## Completed This Session

- Added 14 regex triggers (IDs 55-68) for slash commands to bypass slow LLM classification
- Increased doc-keeper-haiku timeout from 300s to 600s in agent_specs.json
- Fixed process_triggers sequence (was out of sync at 45, now at 54)
- Documented task breakdown pattern in Observability.md (planner→haiku swarm→reviewer)
- Updated Observability.md with fixes and marked action items complete
- Previous session: Fixed ATO MCP token budget, created doc-keeper agent, improved vault interlinking

---

## Next Steps (Priority Order)

1. **Verify orchestrator uses spec timeouts** - Failures showed different timeouts than specs; need to check orchestrator code
2. **Implement enforcement_log writes** - Table has 0 rows, violations not being logged
3. **Add MCP usage tracking** - mcp_usage_stats table barely used (2 rows)
4. **Create MCW dashboard** - Data exists but no visualization

---

## Notes for Next Session

- Observability analysis showed:
  - Agent success rate declining: 75% → 54% → 0% over 3 weeks
  - 100% of recent failures were timeouts
  - LLM classification was 81% (slow path) - fixed with regex triggers
- Task breakdown pattern recommended:
  1. Use planner-sonnet first to break down complex tasks
  2. Spawn multiple lightweight-haiku/coder-haiku in parallel
  3. Use reviewer-sonnet to validate combined work
- Don't use researcher-opus for large tasks (17% success rate)

---

## Key Fixes This Session

| Fix | Details |
|-----|---------|
| Slash command triggers | 14 regex patterns, priority 1, ~600x faster |
| Agent timeout | doc-keeper-haiku 300→600s |
| Sequence fix | process_triggers trigger_id seq reset |

---

**Version**: 3.5
**Status**: Observability system improved, ready for verification
