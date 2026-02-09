# Working Memory Rules

## Session Facts = Your Notepad

Use `store_session_fact` to persist important context that survives compaction.

| When This Happens | Do This |
|-------------------|---------|
| User gives credential/key | `store_session_fact("key", "...", "credential", is_sensitive=True)` |
| User tells you config/endpoint | `store_session_fact("url", "...", "config")` |
| A decision is made | `store_session_fact("decision_X", "...", "decision")` |
| You discover something important | `store_session_fact("finding_X", "...", "note")` |

**Valid types:** credential, config, endpoint, decision, note, data, reference

Use `list_session_facts()` to see your notepad at any time.

## Config Files are Generated

- `.claude/settings.local.json` regenerates from DB on SessionStart
- NEVER manually edit it - changes will be overwritten
- To change permanently: update DB, run `generate_project_settings.py`
