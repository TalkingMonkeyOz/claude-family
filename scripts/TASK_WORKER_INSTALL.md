# Task Worker Scheduler Installation

F224 Local Task Queue — Phase 1 worker daemon launcher.

## Overview

The task_worker daemon is an autonomous process that dequeues and executes tasks from `claude.task_queue`. It must be running at all times to process work items.

Two mechanisms ensure availability:

1. **Windows Task Scheduler** (primary): At-logon entry spawns the daemon
2. **SessionStart watchdog** (failsafe): On Claude session start, if the daemon is dead, respawn it

## Quick Install

```powershell
pwsh -File scripts\setup_task_worker_scheduler.ps1
```

No admin privileges required. Task runs as the current user with limited privileges.

## Verification

```powershell
# Check if task is registered
Get-ScheduledTask -TaskName 'ClaudeFamily-TaskWorker'

# View logs (follow last 20 lines)
Get-Content ~/.claude/logs/task-worker-claude-family.log -Tail 20

# Check PID file (current running process)
Get-Content ~/.claude/task-worker-claude-family.pid

# Health ping (if running on expected port, usually 9901 for claude-family)
curl http://127.0.0.1:9901/health
```

## Configuration

Task-worker behavior is controlled by environment variables in `scripts/cf_constants.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CF_SCRIPT_WORKER_COUNT` | 2 | Worker threads for script-type tasks |
| `CF_AGENT_WORKER_COUNT` | 4 | Worker threads for agent-type tasks |
| `CF_DEFAULT_LEASE_SECS` | 300 | Task lease duration (5 min) |
| `CF_DEFAULT_DRAIN_DEADLINE_SECS` | 60 | Grace period on SIGTERM |

To override: set in environment before Task Scheduler runs, or edit `cf_constants.py`.

## Uninstall

```powershell
Unregister-ScheduledTask -TaskName 'ClaudeFamily-TaskWorker' -Confirm:$false
```

## How It Works

### Startup Flow

1. **Windows logon** → Task Scheduler triggers "ClaudeFamily-TaskWorker" task
2. **Task action**: `pythonw.exe scripts\task_worker.py claude-family C:\Projects\claude-family`
3. **daemon_helper.py**: Allocates port (hashed slot, range 9900-9999), writes PID file
4. **task_worker.py**: Starts HTTP server, listens for /health + commands
5. **Idle timeout**: Auto-exits after 30 min with no new tasks dequeued

### SessionStart Watchdog

When Claude starts a new session:

1. `session_startup_hook_enhanced.py` runs (SessionStart hook)
2. Watchdog checks task-worker PID file: is the process alive?
3. If dead → **respawn** via `watchdog_respawn("task-worker", "claude-family", "scripts.task_worker")`
   - Spawn in background subprocess (does not block hook)
   - Task Scheduler will also re-spawn at next logon
4. If alive → log "already running" and continue

**Fail-open**: If watchdog encounters an exception, it logs a warning and continues. The SessionStart hook never breaks due to a daemon watchdog failure.

### Crash Recovery

If task_worker crashes:

1. **Immediate**: SessionStart hook respawns it (within 30s of next session)
2. **At next logon**: Task Scheduler re-spawns it
3. **Per-task recovery**: Leases expire after 5 min, task re-queued to dead-letter or retried

## Logs

All logs go to `~/.claude/logs/task-worker-claude-family.log` (rotating, 10MB chunks, 5 backups).

```bash
# Tail live logs (PowerShell)
Get-Content ~/.claude/logs/task-worker-claude-family.log -Wait

# Or use tail on WSL
tail -f ~/.claude/logs/task-worker-claude-family.log
```

## Lifecycle Commands

```powershell
# View task details
Get-ScheduledTask -TaskName 'ClaudeFamily-TaskWorker' | Get-ScheduledTaskInfo

# Run task now (for testing)
Start-ScheduledTask -TaskName 'ClaudeFamily-TaskWorker'

# Stop task (graceful shutdown with 60s drain deadline)
Stop-ScheduledTask -TaskName 'ClaudeFamily-TaskWorker'

# Edit task properties
$task = Get-ScheduledTask -TaskName 'ClaudeFamily-TaskWorker'
$task.Triggers  # View triggers
$task.Actions   # View actions
$task.Settings  # View settings
```

## Troubleshooting

### Task runs but daemon doesn't appear in logs

- Check pythonw.exe PATH — may need full path `/usr/bin/python3` or `C:\Python\pythonw.exe`
- Verify project path exists: `C:\Projects\claude-family`
- Check Task Scheduler → View → Event Viewer for errors

### Port collision (9901 taken)

- Daemon automatically scans for free port in range 9900-9999
- Check PID file to see actual bound port: `cat ~/.claude/task-worker-claude-family.pid`
- If all slots full, you have 100+ projects or other services using the range — edit `port_range_start` in `task_worker.py`

### Daemon exits immediately

- Check logs: `tail -f ~/.claude/logs/task-worker-claude-family.log`
- Verify `cf_constants.py` is present and importable
- Verify `daemon_helper.py` is present and importable

### SessionStart hook fails to respawn

- Watchdog failures are logged as warnings, not errors — hook continues
- Check `~/.claude/logs/hooks.log` for details
- Run manual respawn: `python -m scripts.task_worker claude-family C:\Projects\claude-family`

## Integration

The task_worker is fully integrated with:

- **F224 Task Queue System**: Dequeues from `claude.task_queue`, writes to `claude.job_executions`
- **Session Startup Hook**: Monitors + respawns via watchdog
- **Task Lifecycle BPMN**: Lease expiry, heartbeat, graceful shutdown

See `workfiles/task-queue-design/full-design-2026-05-02.md` for full design.

## References

- **Design**: F224 full-design workfile
- **Daemon Helper**: `scripts/daemon_helper.py` (shared infrastructure)
- **Constants**: `scripts/cf_constants.py` (pool sizes, timeouts)
- **Task Scheduler Setup**: `scripts/setup_task_worker_scheduler.ps1` (this installer)
- **SessionStart Hook**: `scripts/session_startup_hook_enhanced.py` (respawn logic)
