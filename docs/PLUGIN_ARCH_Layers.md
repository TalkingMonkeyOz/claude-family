# Claude Family Plugin Architecture - Layer Specifications

See [[PLUGIN_ARCH_Overview]] for introduction and high-level architecture.

---

## Layer 1: claude-family-core Plugin

### Purpose:
Universal foundation for ALL Claude Family members. Provides coordination, session management, feedback system, and shared database access.

### Directory Structure:

```
claude-family-core/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── session-start.md
│   ├── session-end.md
│   ├── feedback-check.md
│   ├── feedback-create.md
│   ├── feedback-list.md
│   ├── inbox-check.md
│   ├── broadcast.md
│   └── team-status.md
├── hooks/
│   └── hooks.json
├── .mcp.json
├── agents/
│   └── coordinator/
│       └── AGENT.md
└── README.md
```

### Component Specifications:

#### 1. plugin.json
```json
{
  "name": "claude-family-core",
  "version": "1.0.0",
  "description": "Core coordination and session management for Claude Family",
  "author": "Claude Family",
  "required_claude_version": ">=0.8.0",
  "dependencies": [],
  "mcpServers": ["postgres", "orchestrator", "memory"]
}
```

#### 2. Session Management Commands

**`/session-start`** (commands/session-start.md)
```markdown
# Session Start

You are starting a new session. Execute the following:

1. Auto-detect your identity from hostname/environment
2. Auto-detect project from current working directory
3. Log session start to PostgreSQL:

```sql
INSERT INTO claude_family.sessions (identity_id, project_id, start_time, status)
VALUES (
  (SELECT identity_id FROM claude_family.identities WHERE identity_name = '<detected>'),
  (SELECT project_id FROM public.projects WHERE project_name = '<detected>'),
  NOW(),
  'active'
)
RETURNING session_id;
```

4. Load recent session context (last 3 sessions for this project)
5. Check inbox for messages from other Claudes
6. Display welcome message with context

Output format:
```
✅ Session Started
Identity: [name]
Project: [name]
Session ID: [uuid]

Recent Context:
- [Last session summary]

📬 Inbox: [N unread messages]
```
```

**`/session-end`** (commands/session-end.md)
```markdown
# Session End

You are ending your current session. Execute the following:

1. Find your active session:
```sql
SELECT session_id FROM claude_family.sessions
WHERE identity_id = (SELECT identity_id FROM claude_family.identities WHERE identity_name = '<your-identity>')
  AND status = 'active'
ORDER BY start_time DESC LIMIT 1;
```

2. Prompt user for session summary with template:

```
Please provide a brief summary of this session:

What was accomplished:
-

Key decisions made:
-

Issues encountered:
-

Next steps:
-
```

3. Update session record:
```sql
UPDATE claude_family.sessions
SET end_time = NOW(),
    status = 'completed',
    summary = '<user-provided-summary>',
    summary_embedding = <generate-embedding>
WHERE session_id = '<session-id>';
```

4. Log to shared_knowledge if significant learnings occurred

5. Display summary and goodbye message
```

**`/feedback-check`** (commands/feedback-check.md)
```markdown
# Feedback Check

Check open feedback items for current project.

```sql
SELECT
  feedback_id::text,
  feedback_type,
  title,
  description,
  status,
  created_at,
  (SELECT COUNT(*) FROM claude_pm.feedback_comments WHERE feedback_comments.feedback_id = project_feedback.feedback_id) as comment_count
FROM claude_pm.project_feedback
WHERE project_id = (SELECT project_id FROM public.projects WHERE project_name = '<current-project>')
  AND status IN ('new', 'in_progress')
ORDER BY
  CASE feedback_type
    WHEN 'bug' THEN 1
    WHEN 'change' THEN 2
    WHEN 'design' THEN 3
    WHEN 'question' THEN 4
  END,
  created_at DESC;
```

Display results in formatted table with emojis:
🐛 Bug | 🎨 Design | ❓ Question | 🔄 Change
```

**`/feedback-create`** (commands/feedback-create.md)
```markdown
# Create Feedback

Create a new feedback item for current project.

1. Prompt user for details:
```
Feedback Type (bug/design/question/change):
Title (brief description):
Description (detailed):
Related files/code (optional):
```

2. Insert into database:
```sql
INSERT INTO claude_pm.project_feedback (
  project_id, feedback_type, title, description,
  reporter_identity, status, created_at
)
VALUES (
  (SELECT project_id FROM public.projects WHERE project_name = '<current-project>'),
  '<type>',
  '<title>',
  '<description>',
  '<your-identity>',
  'new',
  NOW()
)
RETURNING feedback_id;
```

3. Confirm creation with ID
```

**`/inbox-check`** (commands/inbox-check.md)
```markdown
# Inbox Check

Check messages from other Claude instances.

Use orchestrator MCP:
```
mcp__orchestrator__check_inbox(
  project_name='<current-project>',
  session_id='<current-session>',
  include_broadcasts=true
)
```

Display messages in organized format:
- Direct messages first
- Broadcasts second
- Group by sender
- Show message type, priority, timestamp
```

**`/broadcast`** (commands/broadcast.md)
```markdown
# Broadcast Message

Send message to ALL active Claude instances.

1. Prompt user:
```
Message subject:
Message body:
Priority (urgent/normal/low):
```

2. Send via orchestrator:
```
mcp__orchestrator__broadcast(
  subject='<subject>',
  body='<body>',
  priority='<priority>',
  from_session_id='<current-session>'
)
```

3. Confirm delivery
```

**`/team-status`** (commands/team-status.md)
```markdown
# Team Status

Show all active Claude Family members and their current work.

```sql
SELECT
  i.identity_name,
  p.project_name,
  s.start_time,
  EXTRACT(EPOCH FROM (NOW() - s.start_time))/60 as minutes_active,
  LEFT(s.current_context, 100) as current_task
FROM claude_family.sessions s
JOIN claude_family.identities i ON s.identity_id = i.identity_id
JOIN public.projects p ON s.project_id = p.project_id
WHERE s.status = 'active'
ORDER BY s.start_time DESC;
```

Display as formatted table with status indicators.

Also query orchestrator:
```
mcp__orchestrator__get_active_sessions()
```

Merge results and show comprehensive team status.
```

#### 3. Hooks Configuration (hooks/hooks.json)

```json
{
  "hooks": [
    {
      "event": "tool-result",
      "matcher": {
        "tool": "mcp__orchestrator__check_inbox"
      },
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/mark-messages-read.sh"
    },
    {
      "event": "session-start",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/auto-session-start.sh"
    },
    {
      "event": "session-end",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/auto-session-end.sh"
    }
  ],
  "periodic": [
    {
      "interval": 300,
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/periodic-inbox-check.sh",
      "description": "Check inbox every 5 minutes"
    }
  ]
}
```

**Note:** Periodic hooks may not be supported yet - verify in Claude Code docs. If not, use tool-result trigger pattern.

#### 4. MCP Configuration (.mcp.json)

```json
{
  "mcpServers": {
    "postgres": {
      "command": "uvx",
      "args": ["mcp-server-postgres", "postgresql://localhost/ai_company_foundation"],
      "schemas": ["claude_family", "claude_pm", "public"],
      "env": {
        "PGDATABASE": "ai_company_foundation"
      }
    },
    "orchestrator": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-orchestrator"],
      "settings": {
        "messageStore": "postgresql://localhost/ai_company_foundation",
        "schema": "claude_family"
      }
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "settings": {
        "graphStore": "postgresql://localhost/ai_company_foundation",
        "schema": "claude_family"
      }
    }
  }
}
```

**Configuration Notes:**
- Verify exact MCP server package names (may differ)
- Adjust connection strings for actual database location
- Add authentication if needed

#### 5. Coordinator Agent (agents/coordinator/AGENT.md)

```markdown
# Coordinator Agent

You are a coordination specialist for the Claude Family. Your role:

1. **Message Routing:** Help route tasks to appropriate Claude instances
2. **Status Tracking:** Monitor team progress and identify blockers
3. **Context Synthesis:** Summarize recent work across all projects
4. **Conflict Resolution:** Identify when multiple Claudes are working on conflicting tasks

## Capabilities:

- Query all active sessions
- Read session summaries and context
- Send messages via orchestrator
- Access shared knowledge base
- Generate team status reports

## Usage Pattern:

User invokes you when they need:
- "What's the team working on?"
- "Who should handle this task?"
- "Summarize recent progress on Project X"
- "Are there any blockers I should know about?"

## Tools Available:

- postgres MCP (full claude_family schema access)
- orchestrator MCP (messaging, active sessions)
- memory MCP (shared knowledge graph)

## Output Format:

Always provide:
1. Clear summary of findings
2. Actionable recommendations
3. Next steps or suggested follow-ups
```

---

## Layer 2: Project Type Toolkit Plugins

### 2.1: web-dev-toolkit

```
web-dev-toolkit/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── deploy.md
│   ├── build.md
│   ├── test.md
│   ├── lint-fix.md
│   └── shadcn-add.md
├── .mcp.json (if TypeScript/ESLint MCPs exist)
└── README.md
```

**Key Commands:**

**`/shadcn-add`** - Interactive shadcn/ui component installer
```markdown
# Add shadcn/ui Component

1. Prompt user: "Which component? (button, table, card, dialog, etc.)"
2. Run: `npx shadcn-ui@latest add <component>`
3. Show installed component path
4. Provide usage example from shadcn docs
```

**`/deploy`** - Deploy web app
```markdown
# Deploy Web Application

1. Detect deployment platform (Vercel, Netlify, etc.)
2. Run build: `npm run build`
3. Run tests: `npm test`
4. If all pass, deploy: `vercel deploy --prod` or equivalent
5. Log deployment to session context
```

**`/build`** - Build with error handling
```markdown
# Build Application

1. Run: `npm run build`
2. Parse errors if any
3. Categorize: TypeScript errors, ESLint errors, build errors
4. Display organized error report
5. Offer to fix common errors automatically
```

### 2.2: python-dev-toolkit

```
python-dev-toolkit/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── pytest.md
│   ├── format.md
│   ├── type-check.md
│   └── venv-setup.md
└── .mcp.json
```

**Key Commands:**

**`/pytest`** - Run tests with coverage
```markdown
# Run Python Tests

1. Activate venv if exists
2. Run: `pytest --cov --cov-report=term-missing`
3. Parse results
4. Display: Pass/Fail counts, coverage %, missing coverage
5. Log results to session context
```

**`/format`** - Format code with black + isort
```markdown
# Format Python Code

1. Run: `black .`
2. Run: `isort .`
3. Run: `flake8 .`
4. Display changes made
5. Offer to commit if user wants
```

### 2.3: desktop-dev-toolkit

```
desktop-dev-toolkit/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── tauri-dev.md
│   ├── tauri-build.md
│   ├── electron-package.md
│   └── installer-create.md
└── README.md
```

---

## Layer 3: Project-Specific Plugins

### 3.1: mission-control-tools

```
mission-control-tools/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── mc-dashboard.md
│   ├── mc-sync-instances.md
│   ├── mc-spawn-worker.md
│   └── mc-analyze-sessions.md
├── .mcp.json (adds nimbus_context schema)
└── README.md
```

**Key Commands:**

**`/mc-dashboard`** - Launch Mission Control dashboard
```markdown
# Mission Control Dashboard

1. Query active Claude instances from orchestrator
2. Query session data from claude_family.sessions
3. Query project status
4. Display comprehensive dashboard:
   - Active Claudes (identity, project, task, duration)
   - Recent sessions (last 10)
   - Open feedback items
   - System health
```

**`/mc-spawn-worker`** - Spawn specialized agent for task
```markdown
# Spawn Worker Agent

1. Prompt: "Task type? (coder/reviewer/tester/analyst)"
2. Prompt: "Task description:"
3. Prompt: "Workspace directory:"
4. Spawn agent:
```
mcp__orchestrator__spawn_agent(
  agent_type='<type>',
  task='<description>',
  workspace_dir='<dir>'
)
```
5. Monitor agent progress
6. Report results
7. Log to session context
```

**`/mc-sync-instances`** - Sync configuration across all Claudes
```markdown
# Sync Claude Instances

1. Query all active Claude instances
2. Check plugin versions on each
3. Identify outdated instances
4. Send update messages via orchestrator
5. Generate sync report
```

### 3.2: ato-tax-tools

```
ato-tax-tools/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── ato-validate.md
│   ├── ato-test-scenarios.md
│   ├── ato-export-data.md
│   └── ato-compliance-check.md
├── .mcp.json (adds ato schema if needed)
└── README.md
```

### 3.3: nimbus-loader-tools

```
nimbus-loader-tools/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── nimbus-sync.md
│   ├── nimbus-validate-users.md
│   ├── nimbus-export-config.md
│   └── nimbus-test-connection.md
├── .mcp.json (adds nimbus_context schema)
└── README.md
```

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/PLUGIN_ARCH_Layers.md
