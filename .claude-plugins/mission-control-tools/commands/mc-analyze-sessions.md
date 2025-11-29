# /mc-analyze-sessions

Analyze Claude Family session history and productivity metrics for the last 7 days.

## What This Does

Generates detailed analytics on session activity:
- **Session Counts** by project and identity
- **Time Spent** with total hours calculation
- **Project Distribution** showing effort allocation
- **Daily Activity** trends
- **Session Duration** statistics
- **Productivity Metrics** for team capacity planning

## Usage

```
/mc-analyze-sessions
```

Optional parameters (interactive):
- **Days** - Number of days to analyze (default: 7)
- **Project Filter** - Analyze specific project only (optional)
- **Identity Filter** - Analyze specific identity only (optional)

## Queries

Analyzes data from `claude_family.session_history` table:

```sql
-- Session counts by project (last 7 days)
SELECT 
  project_name,
  COUNT(*) as session_count,
  SUM(EXTRACT(EPOCH FROM (session_end - session_start))/3600) as total_hours
FROM claude_family.session_history
WHERE session_end >= NOW() - INTERVAL '7 days'
GROUP BY project_name
ORDER BY total_hours DESC;

-- Daily trends
SELECT 
  DATE(session_start) as date,
  COUNT(*) as sessions,
  SUM(EXTRACT(EPOCH FROM (session_end - session_start))/3600) as hours
FROM claude_family.session_history
WHERE session_end >= NOW() - INTERVAL '7 days'
GROUP BY DATE(session_start)
ORDER BY date DESC;

-- By identity
SELECT 
  identity,
  COUNT(*) as sessions,
  SUM(EXTRACT(EPOCH FROM (session_end - session_start))/3600) as total_hours,
  AVG(EXTRACT(EPOCH FROM (session_end - session_start))/3600) as avg_hours
FROM claude_family.session_history
WHERE session_end >= NOW() - INTERVAL '7 days'
GROUP BY identity
ORDER BY total_hours DESC;
```

## Example Output

```
╔════════════════════════════════════════════════════════════════╗
║         SESSION ANALYTICS (Last 7 Days)                       ║
║                                                                ║
║  SESSIONS BY PROJECT                                          ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ Project        │ Sessions │ Hours   │ Avg Duration    │  ║
║  ├─────────────────────────────────────────────────────────┤  ║
║  │ nimbus         │    18    │  42.5h  │ 2h 22m          │  ║
║  │ claude-family  │     8    │  18.2h  │ 2h 17m          │  ║
║  │ ato            │    12    │  28.7h  │ 2h 23m          │  ║
║  │ personal       │     5    │   9.1h  │ 1h 49m          │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  TOTAL EFFORT: 98.5 hours across 43 sessions                  ║
║  Average Session: 2h 18m                                      ║
║                                                                ║
║  SESSIONS BY IDENTITY                                         ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ Identity              │ Sessions │ Hours  │ % Total     │  ║
║  ├─────────────────────────────────────────────────────────┤  ║
║  │ claude-code-unified   │    43    │ 98.5h  │   100%      │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  DAILY ACTIVITY (Last 7 Days)                                 ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ Date       │ Sessions │ Hours  │ Avg Duration        │  ║
║  ├─────────────────────────────────────────────────────────┤  ║
║  │ 2025-10-23 │    8     │ 18.3h  │ 2h 18m              │  ║
║  │ 2025-10-22 │    7     │ 16.1h  │ 2h 18m              │  ║
║  │ 2025-10-21 │    9     │ 20.4h  │ 2h 16m              │  ║
║  │ 2025-10-20 │    6     │ 14.2h  │ 2h 22m              │  ║
║  │ 2025-10-19 │    7     │ 16.5h  │ 2h 20m              │  ║
║  │ 2025-10-18 │    3     │   7.0h  │ 2h 20m              │  ║
║  │ 2025-10-17 │    3     │   6.0h  │ 2h 00m              │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  PRODUCTIVITY INSIGHTS                                        ║
║  • Most Active Project: nimbus (42.5h, 18 sessions)           ║
║  • Busiest Day: 2025-10-23 (18.3h, 8 sessions)               ║
║  • Avg Team Capacity: 14 hours/day                            ║
║  • Session Consistency: 2h 16m - 2h 22m (very consistent)    ║
╚════════════════════════════════════════════════════════════════╝
```

## Filters

Filter results by:
- **Project Name** - Analyze specific project
- **Date Range** - Custom date ranges
- **Identity** - Specific Claude instance

Example with filters:
```
/mc-analyze-sessions
Analyzing: last 7 days
Projects: nimbus, claude-family (filter out 'ato', 'personal')
```

## Insights Provided

1. **Effort Distribution** - Which projects get most time
2. **Team Velocity** - Sessions/hours per day
3. **Session Quality** - Duration consistency indicators
4. **Capacity Planning** - Available hours per project
5. **Trend Analysis** - Increasing/decreasing activity
6. **Productivity Ratio** - Sessions per hour (efficiency)

## See Also

- `/mc-dashboard` - Real-time status overview
- `/mc-spawn-worker` - Launch specialized agents
- `/feedback-check` - View project feedback and issues
