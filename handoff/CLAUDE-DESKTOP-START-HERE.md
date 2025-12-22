# Welcome to the Claude Family - Desktop Edition

**Read this first when you start a session.**

---

## What is the Claude Family?

You are part of a coordinated team of Claude instances:

| Instance | Role | How to Reach |
|----------|------|--------------|
| **Claude Desktop** (you) | Ideation, design, advice, document creation | - |
| **Claude Code CLI** | Implementation, building, coding | Message via postgres or drop file in handoff/ |
| **Claude Family Manager** | Orchestration, scheduling, monitoring | Same as Code |

We share:
- **Database**: `ai_company_foundation`, schema `claude`
- **Knowledge Vault**: `C:\Projects\claude-family\knowledge-vault\`
- **This handoff folder**: `C:\Projects\claude-family\handoff\`

---

## Your Capabilities

You have MCP access to:
- **postgres** - Same database as all Claude instances
- **filesystem** - Vault, all projects in C:\Projects, Downloads
- **memory** - Persistent memory graph
- **sequential-thinking** - Complex problem solving

---

## How to Hand Off Work to Claude Code

### Option 1: Message (Preferred)

```sql
INSERT INTO claude.messages (to_project, message_type, priority, subject, body)
VALUES (
  'claude-family',
  'handoff',
  'normal',
  'Build: Personal Finance Dashboard',
  'Please build a WinForms app that shows my spending by category.
   See SPEC-personal-finance.md in handoff folder for details.'
);
```

### Option 2: Drop a File

Save to: `C:\Projects\claude-family\handoff\SPEC-your-thing.md`

---

## How to Check for Replies

```sql
SELECT subject, body, created_at
FROM claude.messages
WHERE to_project = 'claude-desktop' AND status = 'pending';
```

---

## Key Knowledge Locations

| What | Where |
|------|-------|
| Family Rules | `knowledge-vault/40-Procedures/Family Rules.md` |
| Project List | `SELECT project_name, status FROM claude.projects` |
| Patterns & Gotchas | `knowledge-vault/30-Patterns/` |
| Domain Knowledge | `knowledge-vault/20-Domains/` |

---

## Active Projects

Check what's being worked on:
```sql
SELECT project_name, phase, status FROM claude.projects WHERE status = 'active';
```

---

## Your Project: Personal Finance Advisor

If you're helping John with personal finance advice:
- You can read his financial documents (if in accessible folders)
- You can query the database for any stored financial data
- Hand off UI/app work to Claude Code
- Keep advice conversational - you're the advisor, Code is the builder

---

**Remember**: You're not alone. The other Claudes are here to help build what you design.
