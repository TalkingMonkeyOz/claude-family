# Mission Control Tools

Mission Control dashboard and team management plugin for Claude Code. Provides comprehensive oversight, agent spawning, and analytics for the Claude Family infrastructure.

## Features

### 🎯 Dashboard (`/mc-dashboard`)
Real-time overview of Claude Family operations:
- **Active Sessions** - Currently running Claude instances with details
- **24-Hour Summary** - Sessions completed, time spent, projects touched
- **Project Distribution** - Session counts and activity per project
- **Team Status** - Quick view of what the team is working on

### 🚀 Spawn Worker (`/mc-spawn-worker`)
Launch specialized agents to handle tasks:
- **12+ Agent Types** - Coder, reviewer, tester, debugger, security analyst, architect, etc.
- **Task Customization** - Specify exactly what you want the agent to do
- **Workspace Control** - Run agents in specific directories
- **Timeout Configuration** - Set max execution time
- **Isolated Execution** - Agents run in separate processes with proper MCP setup

### 📊 Analytics (`/mc-analyze-sessions`)
Deep dive into session history and productivity:
- **Session Counts** - By project, identity, date
- **Time Metrics** - Total hours, average duration, daily trends
- **Productivity Insights** - Capacity planning, velocity metrics, consistency analysis
- **Flexible Filtering** - Analyze by project, date range, or identity
- **Trend Analysis** - Identify patterns and team dynamics

## Quick Start

```bash
# View team status
/mc-dashboard

# Spawn a code reviewer
/mc-spawn-worker
# → Select: reviewer-sonnet
# → Task: Review authentication module
# → Workspace: C:\Projects\nimbus

# Analyze last 7 days of work
/mc-analyze-sessions
```

## Commands

| Command | Purpose | Typical Use |
|---------|---------|-------------|
| `/mc-dashboard` | Team status overview | Daily standup, quick check-in |
| `/mc-spawn-worker` | Launch specialized agent | Code review, testing, debugging |
| `/mc-analyze-sessions` | Session analytics | Weekly/monthly reports, capacity planning |

## Database Integration

Uses PostgreSQL schemas:
- `claude_family.session_history` - All session records
- `claude_family.session_metadata` - Detailed session info
- `claude_family.agent_executions` - Agent run history

## Available Agent Types

### Lightweight (Haiku)
- `coder-haiku` - General coding
- `python-coder-haiku` - Python development
- `tester-haiku` - Test writing
- `debugger-haiku` - Bug fixing
- `web-tester-haiku` - Web testing
- `nextjs-tester-haiku` - Next.js testing

### Advanced (Sonnet)
- `reviewer-sonnet` - Code review
- `security-sonnet` - Security analysis
- `analyst-sonnet` - Data analysis
- `planner-sonnet` - Architecture planning
- `test-coordinator-sonnet` - Test coordination
- `refactor-coordinator-sonnet` - Refactoring

### Specialized (Opus)
- `architect-opus` - System design
- `security-opus` - Advanced security
- `researcher-opus` - Research

## Architecture

```
mission-control-tools/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── commands/
│   ├── mc-dashboard.md          # Dashboard command
│   ├── mc-spawn-worker.md       # Worker spawn command
│   └── mc-analyze-sessions.md   # Analytics command
└── README.md                    # This file
```

## Usage Patterns

### Daily Standup
```bash
/mc-dashboard
# Check active sessions, recent completions, project status
```

### Code Review Workflow
```bash
/mc-spawn-worker
# Agent: reviewer-sonnet
# Task: Review PR #123
# Result: Detailed review with findings
```

### Weekly Retrospective
```bash
/mc-analyze-sessions
# Filter: last 7 days
# Analyze effort distribution, productivity, trends
```

### Bug Triage
```bash
/mc-spawn-worker
# Agent: debugger-haiku
# Task: Investigate production error in logs
# Result: Root cause analysis and fix
```

## Examples

### Example 1: Launch a Security Audit

```
/mc-spawn-worker

Spawning worker...
Agent Type: security-sonnet
Task: Audit authentication system for vulnerabilities
Workspace: C:\Projects\nimbus
Timeout: 600 seconds

Agent spawned: security-opus-uuid-12345
Status: Running...
[... agent output ...]
Status: Complete ✓

Results:
- 3 vulnerabilities found (2 critical, 1 moderate)
- SQL injection risk in login query
- Missing CSRF token validation
- Recommendations provided
```

### Example 2: View Team Dashboard

```
/mc-dashboard

╔════════════════════════════════════════════════════════════════╗
║              MISSION CONTROL DASHBOARD                         ║
║                                                                ║
║  ACTIVE SESSIONS (3)                                          ║
║  • claude-code-unified / nimbus (2m ago)                      ║
║  • claude-code-unified / claude-family (15m ago)              ║
║  • claude-code-unified / ato (1h ago)                         ║
║                                                                ║
║  24-HOUR SUMMARY                                              ║
║  • Completed: 12 sessions                                     ║
║  • Total Duration: 24.5 hours                                 ║
║  • Avg Session: 2h 2m                                         ║
║                                                                ║
║  PROJECT DISTRIBUTION                                         ║
║  • nimbus: 8 sessions (18.5h)                                 ║
║  • claude-family: 4 sessions (9.2h)                           ║
║  • ato: 3 sessions (7.1h)                                     ║
╚════════════════════════════════════════════════════════════════╝
```

### Example 3: Analytics Report

```
/mc-analyze-sessions

SESSION ANALYTICS (Last 7 Days)

SESSIONS BY PROJECT
├─ nimbus: 18 sessions (42.5 hours)
├─ claude-family: 8 sessions (18.2 hours)
├─ ato: 12 sessions (28.7 hours)
└─ personal: 5 sessions (9.1 hours)

TOTAL: 43 sessions, 98.5 hours
Average Session: 2h 18m
Most Active: nimbus
Busiest Day: 2025-10-23 (18.3h, 8 sessions)
```

## Related Commands

- `/session-start` - Start a new session (logs to database)
- `/session-end` - End current session (captures summary)
- `/team-status` - Quick team overview
- `/feedback-check` - View project feedback/issues
- `/feedback-create` - Create new feedback item

## Integration Points

### PostgreSQL
- Reads `claude_family.session_history` for all data
- No writes (read-only analytics)
- Queries filtered by date and optional project/identity

### Orchestrator
- Uses `mcp__orchestrator__spawn_agent()` for worker launching
- Uses `mcp__orchestrator__get_active_sessions()` for real-time status

### File System
- Reads workspace directories for agent execution
- No state persistence (stateless operations)

## Performance

- Dashboard: < 1 second (quick SQL queries)
- Worker spawn: < 5 seconds (subprocess launch)
- Analytics: 1-3 seconds (7-day data aggregation)

## Troubleshooting

### Dashboard shows no sessions
- Check PostgreSQL connection
- Verify `session_start` was run on current session
- Query directly: `SELECT COUNT(*) FROM claude_family.session_history`

### Worker fails to spawn
- Verify workspace directory exists
- Check agent type is valid with `/list-agent-types`
- Ensure MCP postgres and orchestrator servers are running

### Analytics missing data
- Sessions must have both `session_start` and `session_end`
- Incomplete sessions not included in duration calculations
- Check database contains recent sessions

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-23 | Initial release with dashboard, spawn, analytics |

## Authors

Claude Family Infrastructure Team

## License

Internal use only - Claude Family projects

---

**Last Updated**: 2025-10-23
**Maintained By**: Claude Family Infrastructure
