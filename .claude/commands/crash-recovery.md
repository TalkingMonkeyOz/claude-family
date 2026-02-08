**CRASH RECOVERY - Recover Context from Lost/Crashed Sessions**

Use this when a session ended unexpectedly (crash, compaction, timeout) and you need to recover context.

---

## Execute These Steps

### Step 1: Identify Project
Use the current working directory basename as `{project_name}`.

### Step 2: Check Session Facts (Your Notepad)
Use the MCP tool `mcp__project-tools__recall_previous_session_facts` with `n_sessions=3` to retrieve stored facts from recent sessions.

Display any recovered facts grouped by category (credential, config, decision, note).

### Step 3: Find Unclosed Sessions
```sql
SELECT
    session_id::text,
    session_start,
    EXTRACT(EPOCH FROM (NOW() - session_start))/3600 as hours_ago
FROM claude.sessions
WHERE project_name = '{project_name}'
  AND session_end IS NULL
ORDER BY session_start DESC
LIMIT 5;
```

### Step 4: Get Last Completed Session
```sql
SELECT
    session_id::text,
    session_start,
    session_end,
    session_summary,
    tasks_completed
FROM claude.sessions
WHERE project_name = '{project_name}'
  AND session_end IS NOT NULL
ORDER BY session_end DESC
LIMIT 1;
```

### Step 5: Check In-Progress Work Items
```sql
-- In-progress todos
SELECT 'TODO' as type, content as description, priority
FROM claude.todos t
JOIN claude.projects p ON t.project_id = p.project_id
WHERE p.project_name = '{project_name}'
  AND t.status = 'in_progress'
  AND t.is_deleted = false

UNION ALL

-- In-progress build tasks
SELECT 'TASK' as type, bt.task_name as description, 2 as priority
FROM claude.build_tasks bt
JOIN claude.features f ON bt.feature_id = f.feature_id
JOIN claude.projects p ON f.project_id = p.project_id
WHERE p.project_name = '{project_name}'
  AND bt.status = 'in_progress'

UNION ALL

-- In-progress features
SELECT 'FEATURE' as type, f.feature_name as description, 1 as priority
FROM claude.features f
JOIN claude.projects p ON f.project_id = p.project_id
WHERE p.project_name = '{project_name}'
  AND f.status = 'in_progress'

ORDER BY priority;
```

### Step 6: List Recent Transcript Files
Run via Bash:
```bash
ls -lt ~/.claude/projects/C--Projects-{project_name_escaped}/*.jsonl 2>/dev/null | head -5
```

Note: The most recent .jsonl file contains the conversation transcript. If needed, you can read the summary at the end of this file.

### Step 7: Check for TODO Files
```bash
ls -la docs/TODO*.md 2>/dev/null || echo "No TODO files found"
```

### Step 8: Check Git Status
```bash
git status --short
git log --oneline -5
```

---

## Display Format

```
+======================================================================+
|  CRASH RECOVERY - {project_name}                                      |
+======================================================================+

## SESSION FACTS RECOVERED
(facts from mcp__project-tools__recall_previous_session_facts)
  [decision] key: value
  [config] key: value
  ...

## UNCLOSED SESSIONS ({count})
  - {session_id} started {hours_ago}h ago (likely crashed)
  - ...

## LAST COMPLETED SESSION
  Ended: {session_end}
  Summary: {session_summary}
  Completed: {tasks_completed}

## IN-PROGRESS WORK ({count} items)
  FEATURE: {description}
  TASK: {description}
  TODO: {description}

## TRANSCRIPT FILES
  Most recent: {filename} ({size}, {modified})
  To read context: Read the last 500 lines of the .jsonl file

## UNCOMMITTED CHANGES
  {git status output}

## RECENT COMMITS
  {git log output}

+======================================================================+
```

---

## Recovery Actions

After reviewing the recovered context:

1. **Session Facts Present**: Use them to restore key decisions/configs
2. **Unclosed Sessions**: These were likely crashes - note the session_id
3. **In-Progress Work**: Continue where you left off
4. **Need More Detail**: Read the transcript file:
   ```bash
   tail -500 ~/.claude/projects/C--Projects-{project}/*.jsonl | head -200
   ```

---

## Notes

- **Transcript files** are JSONL format with conversation turns
- **Session facts** are automatically injected but may not survive compaction
- **Unclosed sessions** indicate crashes (no /session-end was run)
- **In-progress items** show what was being worked on

---

**Version**: 1.0
**Created**: 2026-02-03
**Updated**: 2026-02-03
**Location**: .claude/commands/crash-recovery.md
