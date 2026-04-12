# Session Start

Start a new work session by loading context from the database.

## Steps

1. Call `start_session(project)` to load all session context (todos, features, messages, previous state)
2. Review what it returns — active features, pending messages, last session summary
3. If there are pending messages, check them with `check_inbox(project_name)`
4. Call `get_build_board(project)` to see what work is ready
5. If resuming previous work, call `get_work_context(scope='current')` for active task details

## Notes

- Session logging is automatic via hooks — no manual SQL needed
- All config regenerates from DB on session start (self-healing)
- Use `recall_memories("topic")` and `recall_entities("topic")` to load knowledge
- Use `get_secret(key, project)` to retrieve stored credentials
- Use `unstash("component")` to reload working notes from prior sessions