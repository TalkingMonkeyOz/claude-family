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
├── CLAUDE.md                    # Diana's personality & instructions
├── README.md                    # Documentation
├── start_diana.bat              # Launcher
├── .mcp.json                    # MCP server configuration (copied from claude-console-01)
├── workspace\                   # Diana's working directory
└── scripts\
    ├── startup.py               # Shows pending items on launch
    └── check_reminders.py       # Automated monitoring
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

## Related Documents

- `C:\claude\diana\CLAUDE.md` - Diana's personality definition
- `C:\claude\diana\README.md` - User documentation
- `C:\claude\shared\docs\CLAUDE.md` - Shared Claude Family documentation

---

**Status:** ✅ Complete and tested
**Next Steps:** User can launch Diana and test workflow
