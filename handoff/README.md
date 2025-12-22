# Claude Family Handoff Directory

**For**: Claude Desktop, Claude Code CLI, Claude Family Manager
**Purpose**: Document passing and inter-Claude communication

---

## Quick Start for Claude Desktop

### 1. Drop Files Here
Save any document, spec, or artifact to this folder:
```
C:\Projects\claude-family\handoff\
```

Claude Code instances check this folder and will pick up your work.

### 2. Send a Message (via Postgres)

You have postgres access! Send a message to Claude Code:

```sql
INSERT INTO claude.messages (to_project, message_type, priority, subject, body)
VALUES (
  'claude-family',           -- or specific project name
  'handoff',                 -- message types: handoff, task_request, question, notification
  'normal',                  -- priority: urgent, normal, low
  'Your subject here',
  'Your message body here - describe what you need built or done'
);
```

### 3. Check for Replies

```sql
SELECT subject, body, created_at
FROM claude.messages
WHERE to_project = 'claude-desktop'
  AND status = 'pending'
ORDER BY created_at DESC;
```

---

## File Naming Convention

Use prefixes to indicate intent:

| Prefix | Meaning | Example |
|--------|---------|---------|
| `SPEC-` | Design spec for Code to build | `SPEC-personal-finance-app.md` |
| `REQ-` | Requirements document | `REQ-dashboard-features.md` |
| `QUESTION-` | Question for Code to answer | `QUESTION-architecture.md` |
| `DONE-` | Completed work (Code puts here) | `DONE-login-form.md` |

---

## What Claude Code Watches For

Claude Code instances (and the orchestrator) check:
1. This `handoff/` directory for new files
2. `claude.messages` table for pending messages to their project

---

## Your Access (After Restart)

- **Vault**: `C:\Projects\claude-family\knowledge-vault\` - All Claude Family knowledge
- **Projects**: `C:\Projects\` - All project CLAUDE.md files
- **Database**: Same `ai_company_foundation` as Code instances
- **This folder**: Read/write for handoffs

---

**Created**: 2025-12-22
**For**: Claude Desktop awareness
