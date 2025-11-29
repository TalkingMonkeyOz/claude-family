# claude-family-core Plugin

Core coordination and session management for Claude Family instances.

## Installation

Copy this plugin to your project or reference it from a central location:

```bash
# Option 1: Copy to project
cp -r C:/claude/plugins/claude-family-core /your/project/.claude-plugins/

# Option 2: Symlink (recommended for updates)
ln -s C:/claude/plugins/claude-family-core /your/project/.claude-plugins/claude-family-core
```

## Features

### Commands

| Command | Description |
|---------|-------------|
| `/session-start` | Initialize session with context loading |
| `/session-end` | Close session with summary logging |
| `/inbox-check` | Check messages from other Claudes |
| `/feedback-check` | View open feedback items |
| `/feedback-create` | Create new feedback item |
| `/team-status` | View active Claude instances |
| `/broadcast` | Send message to all Claudes |

### Hooks

- **SessionStart**: Auto-runs startup script on session begin
- **PostToolUse (check_inbox)**: Reminder to acknowledge messages

### MCP Servers

Bundled servers:
- `postgres` - Database access (ai_company_foundation)
- `memory` - Persistent knowledge graph
- `orchestrator` - Agent spawning and messaging
- `filesystem` - File operations

### Agents

- `coordinator` - Team coordination and status synthesis

## Configuration

### Database Connection

The plugin expects PostgreSQL at:
```
postgresql://postgres:postgres@localhost:5432/ai_company_foundation
```

Modify `.mcp.json` if your connection differs.

### Required Schemas

- `claude_family` - Identities, sessions, knowledge
- `claude_pm` - Feedback/issue tracking

## Usage

After installation, commands are available via `/command-name`.

The SessionStart hook will automatically run on session begin, providing:
- Working directory detection
- Project identification
- Reminder to run full `/session-start`

## Version

1.0.0

## Author

Claude Family
