# Next Session TODO - HOOKS FIX COMPLETE

**Last Updated**: 2026-01-02 23:25
**Last Session**: Fixed hooks configuration bug

---

## RESOLVED: Hooks Not Working

**Root Cause**: `generate_project_settings.py` was writing hooks to `.claude/hooks.json`, but Claude Code only reads hooks from:
- `~/.claude/settings.json` (global)
- `.claude/settings.json` (project, shared)
- `.claude/settings.local.json` (project, local)

**The file `hooks.json` is NOT supported by Claude Code!**

**Fix Applied**:
1. Updated `generate_project_settings.py` to put hooks INTO `settings.local.json`
2. Script now auto-deletes legacy `hooks.json` files
3. Updated vault documentation (Config Management SOP, Claude Hooks)

**Note**: The cache bloat hypothesis from 2026-01-01 was a red herring. The hooks weren't working because they were in the wrong file.

---

## Completed This Session

- [x] Researched Claude Code hooks documentation (via claude-code-guide agent)
- [x] Identified root cause: hooks.json not supported
- [x] Fixed `generate_project_settings.py` to merge hooks into settings.local.json
- [x] Regenerated claude-family config (hooks.json deleted, settings.local.json updated)
- [x] Updated Config Management SOP (removed hooks.json references)
- [x] Updated Claude Hooks document (added fix, corrected config flow)

---

## Next Steps

1. **RESTART Claude Code** to load the new settings.local.json with hooks
2. **Verify hooks work** after restart:
   ```bash
   # Make an edit, then check hooks.log for fresh timestamps
   tail -10 ~/.claude/hooks.log
   ```
3. **Commit these changes** (script fix + documentation updates)

---

## Files Changed

| File | Change |
|------|--------|
| `scripts/generate_project_settings.py` | Fixed to put hooks in settings.local.json |
| `knowledge-vault/40-Procedures/Config Management SOP.md` | Removed hooks.json references |
| `knowledge-vault/Claude Family/Claude Hooks.md` | Added fix, updated config flow |
| `.claude/settings.local.json` | Now contains hooks (regenerated) |
| `.claude/hooks.json` | DELETED (was ignored by Claude Code) |

---

**Version**: 2.0
**Created**: 2026-01-02
**Updated**: 2026-01-02
**Location**: docs/TODO_NEXT_SESSION.md
