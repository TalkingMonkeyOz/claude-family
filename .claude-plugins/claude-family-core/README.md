# claude-family-core Plugin

Core coordination and session management for Claude Family instances.

## Quick Install

Run the install script from your project directory:

```bash
python C:/Projects/claude-family/scripts/install_plugin.py
```

Or manually:

```bash
# 1. Copy commands to your project
cp C:/Projects/claude-family/.claude-plugins/claude-family-core/commands/*.md /your/project/.claude/commands/

# 2. Copy hooks.json (or merge with existing)
cp C:/Projects/claude-family/.claude/hooks.json /your/project/.claude/hooks.json

# 3. Copy startup script
mkdir -p /your/project/.claude-plugins/claude-family-core/scripts
cp C:/Projects/claude-family/.claude-plugins/claude-family-core/scripts/session_startup_hook.py /your/project/.claude-plugins/claude-family-core/scripts/
```

## Features

### Commands

| Command | Description |
|---------|-------------|
| `/session-start` | Initialize session with context loading, check for previous state |
| `/session-end` | Save session state (todo list, focus) and log summary |
| `/inbox-check` | Check messages from other Claude instances |
| `/feedback-check` | View open feedback items for current project |
| `/feedback-create` | Create new feedback item |
| `/team-status` | View active Claude instances and their work |
| `/broadcast` | Send message to all Claude instances |

### Hooks

- **SessionStart (startup)**: Auto-loads previous session state, checks for messages
- **SessionStart (resume)**: Same as startup, for session resume
- **SessionEnd**: Prompts to save session state
- **PostToolUse (check_inbox)**: Reminder to acknowledge important messages

### Session State Persistence

The plugin saves your work state between sessions:
- Todo list (from TodoWrite tool)
- Current focus/task description
- Files modified
- Pending actions

On next session start, this context is automatically restored.

## Database Requirements

PostgreSQL database: `ai_company_foundation`

Required schemas:
- `claude_family` - Identities, sessions, knowledge, session_state
- `claude_pm` - Feedback/issue tracking

Required tables:
- `claude_family.session_history` - Session logs
- `claude_family.session_state` - Persisted todo/focus between sessions
- `claude_family.instance_messages` - Inter-Claude messaging
- `claude_family.identities` - Claude identity registry
- `claude_pm.project_feedback` - Feedback items

## File Structure

```
.claude-plugins/claude-family-core/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── commands/
│   ├── session-start.md     # Session initialization
│   ├── session-end.md       # Session close + state save
│   ├── inbox-check.md       # Check messages
│   ├── broadcast.md         # Send to all Claudes
│   ├── feedback-check.md    # View feedback
│   ├── feedback-create.md   # Create feedback
│   └── team-status.md       # View team activity
├── hooks/
│   └── hooks.json           # Hook definitions
├── scripts/
│   └── session_startup_hook.py  # Auto-run on session start
├── agents/
│   └── coordinator/
│       └── AGENT.md         # Coordinator agent definition
└── README.md
```

## Version

1.0.0 (2025-11-30)

## Author

Claude Family (claude-code-unified)
