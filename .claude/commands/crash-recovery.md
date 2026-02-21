**CRASH RECOVERY - Recover Context from Lost/Crashed Sessions**

Use this when a session ended unexpectedly (crash, compaction, timeout) and you need to recover context.

---

## Execute These Steps

### Step 1: Call the MCP Tool

Use the MCP tool `mcp__project-tools__recover_session` with no arguments (auto-detects project from cwd).

This single call returns ALL recovery context:
- Session facts from recent sessions
- Crashed sessions (with continuation re-fires filtered out)
- Last completed session summary
- In-progress work items (todos, build tasks, features)
- Crash analysis (transcript parsing for crash signals)
- Git status (uncommitted changes, recent commits)
- Suggested recovery actions

### Step 2: Display the Results

Format the MCP tool response as follows:

```
+======================================================================+
|  CRASH RECOVERY - {project}                                          |
+======================================================================+

## SESSION FACTS RECOVERED ({session_facts.count})
  [type] key: value (truncated to 200 chars)
  ...

## CRASHED SESSIONS ({crashed_sessions.count}, {refires_filtered} re-fires filtered)
  - {session_id} started {hours_ago}h ago
  ...

## CRASH ANALYSIS
  Type: {crash_analysis.crash_type}
  Max tokens: {crash_analysis.max_input_tokens}
  Transcript: {crash_analysis.transcript_file} ({file_size_kb}KB, {total_entries} entries)
  Last user message: {crash_analysis.last_user_message}
  Last assistant action: {crash_analysis.last_assistant_action}
  Signals: output_tokens=1 x{count}, stop_reason=None x{count}

## LAST COMPLETED SESSION
  Ended: {last_completed_session.ended}
  Summary: {last_completed_session.summary}
  Completed: {last_completed_session.tasks_completed}

## IN-PROGRESS WORK ({in_progress_work.count} items)
  {type}: {description}
  ...

## GIT STATUS
  Uncommitted: {git_status.uncommitted_changes}
  Recent commits: {git_status.recent_commits}

## RECOVERY ACTIONS
  - {action}
  ...

+======================================================================+
```

### Step 3: Follow Recovery Actions

The `recovery_actions` list tells you what to do next:
- **Session facts recovered** → Key decisions/configs are available
- **Crashed sessions found** → Review crash analysis for root cause
- **In-progress work** → Continue where you left off
- **Uncommitted changes** → Review and commit if appropriate
- **CLI crash detected** → Not a context issue, work may be complete
- **Context exhaustion** → Consider smaller tasks or checkpointing

---

**Version**: 2.0
**Created**: 2026-02-03
**Updated**: 2026-02-21
**Location**: .claude/commands/crash-recovery.md
