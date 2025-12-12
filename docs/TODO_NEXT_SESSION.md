# Next Session TODO

**Last Updated**: 2025-12-13
**Last Session**: Fixed MCP configs, hook injection, session commands

## Completed This Session
- Fixed Windows npx wrapper issue in nimbus-import `.mcp.json` (cmd /c npx)
- Fixed `~/.claude.json` project-specific MCP config for nimbus-import
- Simplified nimbus-import MCP config (removed duplicates of global servers)
- Copied 6 essential slash commands to global `~/.claude/commands/`
- Fixed `/session-end` to include TODO file creation as Step 1
- **CRITICAL FIX**: Fixed `process_router.py` hook response format
  - Changed `systemPrompt` → `hookSpecificOutput.additionalContext`
  - This was why process guidance wasn't being injected!
- Acknowledged 2 pending messages (hook issues from nimbus-import)
- Cleaned up 4 unclosed sessions (108hr, 83hr, 79hr, 7hr old)

## Next Steps
1. **Verify hook fix in other projects** - Test that `<process-guidance>` tags now appear in nimbus-import, ATO-Tax-Agent, etc.
2. **Sync session-end.md to all locations** - Global version updated, but project-level versions may have old schema references (`claude_family.session_history` → `claude.sessions`)
3. **Run overdue jobs** - Link Checker and Orphan Document Report (8 days overdue)
4. **Test MCW** - MCW was unresponsive in previous sessions, verify it works
5. **Remove backward-compat views** - Due reminder from startup: legacy views can be dropped

## Notes for Next Session
- The global `~/.claude/mcp.json` is the source of truth for shared MCP servers
- Project `.mcp.json` should only contain project-specific servers (like mui-mcp)
- Hook response format: `{"hookSpecificOutput": {"hookEventName": "...", "additionalContext": "..."}}`
- Session startup hook intermittently fails - may need absolute Python path

## Key Pattern Discovered
**Claude Code Hook Response Format:**
```json
// WRONG (doesn't work):
{"systemPrompt": "..."}

// CORRECT:
{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}
```
