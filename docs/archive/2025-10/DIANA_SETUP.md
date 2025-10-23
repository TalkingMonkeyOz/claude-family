# Diana - 6th Claude Family Member Setup

**Date:** 2025-10-18
**Branch:** feature/diana-6th-member
**Created by:** claude-code-console-001

## Summary

Diana is now configured as the 6th member of the Claude Family - a Claude Code Console instance specialized as the AI Company Managing Director.

## What Was Built

### 1. Diana Workspace (`C:\claude\diana\`)

```
C:\claude\diana\
├── CLAUDE.md                           # Diana's personality & instructions
├── README.md                           # Complete documentation
├── start_diana.bat                     # Launcher with --dangerously-skip-permissions
├── AGENT_ORCHESTRATION_GUIDE.md        # How to spawn agents and delegate work
├── AGENT_SPAWNING_QUICK_REF.md         # Quick reference cheat sheet
├── MCP_FIX.md                          # MCP configuration troubleshooting
├── SHUTDOWN_INSTRUCTIONS.md            # Session close procedures
├── COMPLETION_SUMMARY.md               # Implementation summary
├── .mcp.json                           # MCP server configuration (7 servers)
├── .claude\
│   └── settings.local.json             # Claude Code settings
├── workspace\                          # Diana's working directory
└── scripts\
    ├── startup.py                      # Shows pending items on launch
    ├── shutdown.py                     # Logs session end to database
    └── check_reminders.py              # Automated monitoring (Task Scheduler)
```

### 2. Database Changes

**New Table:** `diana_inbox`
```sql
CREATE TABLE diana_inbox (
    inbox_id SERIAL PRIMARY KEY,
    reminder_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    priority INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    processed_by VARCHAR(100)
);
```

**New Identity:** Diana registered in `claude_family.identities`
- identity_name: 'diana'
- platform: 'claude-code-console'
- role: Managing Director & Orchestrator

## How to Use

### Launch Diana

```bat
C:\claude\diana\start_diana.bat
```

This will:
1. Run `startup.py` - shows pending inbox items, stalled work, Friday reports
2. Launch Claude Code Console with Diana's personality (CLAUDE.md)

### Enable Automated Monitoring (Optional)

Set up Windows Task Scheduler to run check_reminders.py daily:

```bat
schtasks /create /tn "Diana Reminders" /tr "python C:\claude\diana\scripts\check_reminders.py" /sc daily /st 09:00
```

This automatically populates `diana_inbox` with:
- Friday weekly report reminders
- Stalled work package alerts (>24 hours)
- Blocked work package alerts
- Inactive agent notifications

## Architecture

### Diana vs Other Claude Instances

| Feature | Diana | claude-code-console-001 |
|---------|-------|------------------------|
| Personality | Managing Director | Terminal Specialist |
| Startup | Checks inbox, shows reminders | Normal startup |
| Behavior | Always checks SOPs/work_packages first | General help |
| Workflow | Creates work packages, delegates | Executes tasks directly |
| Automation | Proactive reminders via inbox | Reactive only |

### How Diana Works

**Same technology, different configuration:**
- Uses Claude Code Console (same as claude-code-console-001)
- Different CLAUDE.md file defines personality
- Different startup script shows proactive reminders
- Same MCP access (postgres, memory, tree-sitter, etc.)
- Same tool capabilities (file operations, code execution, agent spawning)

**Key Difference: Behavior, not capabilities**

## Integration with Existing Systems

Diana has full access to:
- **work_packages** table - project tracking
- **sops** table - Standard Operating Procedures
- **ai_agents** table - team roster
- **session_history** - audit trail
- **decisions_log** - decision tracking
- All existing Python services in `C:\Projects\ai-workspace\`

Diana can import and use:
- `diana_context_loader.py`
- `diana_orchestrator.py`
- `preprocessor_service.py`
- `response_parser.py`

## Why This Approach

**Problem:** Diana Command Center GUI had Error 500s, couldn't create files, limited capabilities

**Solution:** Use proven Claude Code Console technology with Diana personality

**Advantages:**
- ✅ Works immediately (tested startup script)
- ✅ Full MCP access
- ✅ Can create files and execute code
- ✅ Can spawn agents via Task tool
- ✅ Simple architecture (no complex middleware)
- ✅ Proactive reminders via inbox system
- ✅ All existing database/services work as-is

## Future Enhancements

Possible additions:
- [ ] Simple web dashboard for visual progress (reuse ai-company-controller)
- [ ] Email/Slack notifications for urgent reminders
- [ ] Calendar integration for scheduling
- [ ] More sophisticated agent monitoring
- [ ] Cost tracking and budget alerts

## Testing

Startup script tested successfully:
```
$ python C:\claude\diana\scripts\startup.py

================================================================================
DIANA - AI COMPANY MANAGING DIRECTOR
================================================================================

ACTIVE WORK PACKAGES:
  PLANNED: 22

--------------------------------------------------------------------------------
Diana ready. Type your request or ask 'What should I tackle first?'
================================================================================
```

## Files Location

Diana files are in `C:\claude\diana\` (NOT in this git repo) because:
- Isolated workspace (like other Claude instances)
- Settings won't conflict with other Claudes
- MCP config is local, not tracked

This document serves as the record of Diana's setup in the claude-family repository.

## Agent Orchestration

Diana can delegate work using two methods:

**1. Task Tool** - Spawn dedicated Claude agents for complex projects
```python
Task(
    description="Build calculator app",
    prompt="Detailed instructions...",
    subagent_type="general-purpose"
)
```

**2. Agent Coordinator** - Smart routing to cheapest/fastest path
```python
from agent_coordinator import AgentCoordinator
coordinator = AgentCoordinator()
routing = coordinator.route_task("Task description")
# Routes to: postgres (FREE) → claude-cli (FREE) → cursor (FREE) → haiku → sonnet
```

See `C:\claude\diana\AGENT_ORCHESTRATION_GUIDE.md` for complete documentation.

## Troubleshooting

**MCP Issues:** See `C:\claude\diana\MCP_FIX.md`
- Quick fix: Ensure `.mcp.json` is in root directory (NOT in .claude subdirectory)
- Verify with: `/mcp list` should show 7 servers

**Session Logging:** See `C:\claude\diana\SHUTDOWN_INSTRUCTIONS.md`
- Run `python scripts\shutdown.py` before closing Diana
- Logs session end time to database

## Related Documents

- `C:\claude\diana\CLAUDE.md` - Diana's personality definition
- `C:\claude\diana\README.md` - Complete user documentation
- `C:\claude\diana\AGENT_ORCHESTRATION_GUIDE.md` - Agent delegation guide
- `C:\claude\diana\AGENT_SPAWNING_QUICK_REF.md` - Quick reference cheat sheet
- `C:\claude\diana\COMPLETION_SUMMARY.md` - Implementation details
- `C:\claude\shared\docs\CLAUDE.md` - Shared Claude Family documentation

---

**Status:** ✅ Complete and ready for production
**Next Steps:**
1. Launch Diana: `C:\claude\diana\start_diana.bat`
2. Verify MCP servers: `/mcp list` (should show 7 servers)
3. Test agent spawning with simple project
4. Optional: Set up Task Scheduler for automated reminders
