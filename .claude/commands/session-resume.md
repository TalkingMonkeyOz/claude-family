**QUICK SESSION RESUME - Context at a Glance**

Display last session context in a compact, scannable format.

---

## Execute This Query

```sql
-- Get last session summary and recent work
WITH last_session AS (
    SELECT
        session_start::date as date,
        summary,
        outcome,
        project_name
    FROM claude.sessions
    WHERE summary IS NOT NULL
    ORDER BY session_start DESC
    LIMIT 1
),
pending_todos AS (
    SELECT file_path, description
    FROM claude.documents
    WHERE doc_type = 'TODO'
    AND is_core = true
    LIMIT 1
)
SELECT
    '📅 Last: ' || ls.date || ' (' || ls.project_name || ')' as header,
    ls.summary,
    ls.outcome
FROM last_session ls;
```

---

## Then Read TODO File

```bash
cat C:/Projects/claude-family/docs/TODO_NEXT_SESSION.md | head -60
```

---

## Display Format (Copy This Structure)

```
╔══════════════════════════════════════════════════════════════╗
║  SESSION RESUME - {project_name}                             ║
╠══════════════════════════════════════════════════════════════╣
║  📅 Last Session: {date}                                     ║
║  📋 Summary: {one-line summary}                              ║
║  ✅ Outcome: {completed/partial/blocked}                     ║
╠══════════════════════════════════════════════════════════════╣
║  NEXT STEPS (from TODO_NEXT_SESSION.md):                     ║
║  1. {first priority item}                                    ║
║  2. {second priority item}                                   ║
║  3. {third priority item}                                    ║
╠══════════════════════════════════════════════════════════════╣
║  UNCOMMITTED: {count} files | AGENTS: {count} available      ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Quick Stats (Run in Parallel)

```bash
# Uncommitted changes
cd /c/Projects/claude-family && git status --short | wc -l

# Active agents
# Use: mcp__orchestrator__list_agent_types and count
```

---

**Usage**: Run `/session-resume` at start of any session for instant context.
**Time**: ~5 seconds (vs 2+ minutes for full /session-start)
