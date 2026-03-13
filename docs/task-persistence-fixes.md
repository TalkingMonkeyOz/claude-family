# Task Persistence Bug Fixes — 2026-03-14

Five hook script bugs fixed. All changes are in `.py` files only (no BPMN modified).

---

## Fixes Applied

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `scripts/session_end_hook.py` | "current transaction is aborted" error — prior helper failure left conn in aborted state, blocking the session UPDATE | Added `conn.rollback()` safety net at top of `auto_save_session()` try block, before calling any helpers |
| 2 | `scripts/task_sync_hook.py` | "could not determine data type of parameter $1" on auto-checkpoint INSERT | Added `::text` explicit casts to both parameters: `VALUES (%s::text, %s::text, NOW())` |
| 3 | `scripts/task_discipline_hook.py` | `INTERVAL '%s hours'` — psycopg2 does NOT substitute `%s` inside SQL string literals; DB received literal `'%s hours'` and failed to parse it | Replaced with `make_interval(hours => %s)` which accepts a proper parameter binding |
| 4 | `scripts/session_startup_hook_enhanced.py` | No cleanup of zombie sessions (open > 24h); accumulate in DB indefinitely | Added zombie cleanup block after `log_session_start()` using its own connection, non-fatal |
| 5 | `C:\claude\start-claude.bat` | `CLAUDE_CODE_TASK_LIST_ID` not set in launcher; only set in claude-family `.env` (project-specific) | Added `set CLAUDE_CODE_TASK_LIST_ID=%PROJECT_NAME%` before both WezTerm and direct launch paths |

---

## Notes

- `.env` at `C:\Projects\claude-family\.env` already has `CLAUDE_CODE_TASK_LIST_ID=claude-family` — correct for that project.
- Launcher fix ensures ALL projects get the shared task list ID, not just claude-family.
- WezTerm launch also re-sets the variable inside the spawned `cmd /k` string to survive process inheritance.
- Zombie cleanup SQL: `session_id != %s::uuid` guard excludes the session just created.

---

**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: C:\Projects\claude-family\docs\task-persistence-fixes.md
