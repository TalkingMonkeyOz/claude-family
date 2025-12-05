# /mc-dashboard

Display Mission Control team status dashboard with active sessions, recent activity, and team metrics.

## What This Does

Shows a real-time overview of Claude Family operations:
- **Active Sessions**: Currently running Claude instances
- **Recent Activity**: Sessions completed in the last 24 hours
- **Team Metrics**: Session counts, project distribution
- **Session Details**: Identity, project, duration, status

## Usage

```
/mc-dashboard
```

## Output

The dashboard displays:

1. **Active Sessions** table showing:
   - Session ID
   - Identity (e.g., claude-code-unified)
   - Project Name
   - Start Time
   - Status

2. **24-Hour Summary**:
   - Total sessions completed
   - Active sessions count
   - Projects touched
   - Average session duration

3. **Project Distribution**:
   - Session count per project
   - Most active projects

## Technical Details

Queries the `claude.sessions` table:
- Active sessions: `session_end IS NULL`
- Recent sessions: `created_at >= NOW() - INTERVAL '24 hours'`
- Calls `mcp__orchestrator__get_active_sessions()` for real-time agent status

## Example Dashboard Output

```
╔════════════════════════════════════════════════════════════════╗
║              MISSION CONTROL DASHBOARD                         ║
║                                                                ║
║  ACTIVE SESSIONS (3)                                          ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ ID      │ Identity              │ Project        │ Started  │
║  ├─────────────────────────────────────────────────────────┤  ║
║  │ sess-1  │ claude-code-unified   │ nimbus         │ 2m ago   │
║  │ sess-2  │ claude-code-unified   │ claude-family  │ 15m ago  │
║  │ sess-3  │ claude-code-unified   │ ato            │ 1h ago   │
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  24-HOUR SUMMARY                                              ║
║  • Completed: 12 sessions                                     ║
║  • Active: 3 sessions                                         ║
║  • Total Duration: 24.5 hours                                 ║
║  • Avg Session: 2h 2m                                         ║
║                                                                ║
║  PROJECT DISTRIBUTION                                         ║
║  • nimbus: 8 sessions                                         ║
║  • claude-family: 4 sessions                                  ║
║  • ato: 3 sessions                                            ║
╚════════════════════════════════════════════════════════════════╝
```

## See Also

- `/mc-spawn-worker` - Launch a new agent
- `/mc-analyze-sessions` - Detailed session analytics
- `/team-status` - Quick team overview
