---
projects:
- claude-family
tags:
- identity
- sessions
- architecture
synced: false
---

# Identity Per Project

Each project now has its own dedicated Claude identity, enabling project-specific expertise and role-based session tracking.

---

## Overview

Previously, all sessions used the shared `claude-code-unified` identity. Now each project can have its own identity with specialized knowledge and capabilities.

**Benefits:**
- Project-specific expertise in identity descriptions
- Better session analytics per project
- Clear identity separation for different domains
- Fallback to shared identity for unknown projects

---

## How It Works

### Identity Resolution (Session Startup)

When a new session starts:

1. **Project Lookup**: Query `claude.projects.default_identity_id` for current project
2. **Use Project Identity**: If found and not NULL, use that identity
3. **Fallback Chain**:
   - Environment variable `CLAUDE_IDENTITY_ID`
   - Hardcoded `claude-code-unified` (ff32276f-9d05-4a18-b092-31b54c82fff9)

---

## Current Project Identities

| Project | Identity Name | Expertise |
|---------|---------------|-----------|
| claude-family | `claude-claude-family` | Infrastructure, PostgreSQL, MCP servers, hooks |
| ATO-Tax-Agent | `claude-ato-tax-agent` | Australian tax law, compliance, tax agent app |
| Claude Family Manager v2 | `claude-manager-v2` | WPF/MVVM, Blazor, .NET, UI/UX |
| nimbus-import | `claude-nimbus-import` | Data integration, API, batch processing |
| nimbus-user-loader | `claude-nimbus-user-loader` | User data, sync patterns, validation |

**Fallback Identity:**
- `claude-code-unified` - Used for projects without explicit identity
- `claude-desktop` - Used by Desktop app (not project-specific)

---

## Adding a New Project Identity

### 1. Create Identity Record

```sql
INSERT INTO claude.identities
(identity_id, identity_name, platform, role_description, status, created_at)
VALUES
(
    gen_random_uuid(),
    'claude-myproject',
    'claude-code-console',
    'Dedicated to myproject. Expertise in [domain], [tech stack], [specialty].',
    'active',
    NOW()
)
RETURNING identity_id;
```

### 2. Link to Project

```sql
UPDATE claude.projects
SET default_identity_id = '[identity_id from above]'
WHERE project_name = 'myproject';
```

### 3. Verify

Start a new session in that project:
```bash
cd C:\Projects\myproject
claude-code
```

Check the session record:
```sql
SELECT s.session_id, s.project_name, i.identity_name
FROM claude.sessions s
JOIN claude.identities i ON s.identity_id = i.identity_id
WHERE s.project_name = 'myproject'
ORDER BY s.session_start DESC
LIMIT 1;
```

---

## Naming Convention

**Pattern:** `claude-{project-slug}`

| Project Name | Identity Slug | Notes |
|--------------|---------------|-------|
| claude-family | claude-claude-family | Redundant but consistent |
| ATO-Tax-Agent | claude-ato-tax-agent | Lowercase, kebab-case |
| Claude Family Manager v2 | claude-manager-v2 | Abbreviated for brevity |
| nimbus-import | claude-nimbus-import | Direct mapping |

---

## Migration Notes

**Before (2025-12-26):**
- All sessions used `claude-code-unified`
- 39 sessions had NULL identity (backfilled)
- No project-specific expertise

**After (2025-12-26):**
- 5 active projects have dedicated identities
- New sessions auto-resolve to project identity
- Foreign key constraint enforces valid identities
- Old sessions preserved with `claude-code-unified`

---

## Related Documents

- [[Identity System - Overview]] - Full identity system documentation
- [[Session Lifecycle Guide]] - How sessions are created and tracked
- [[Database Schema - Core Tables]] - Projects and identities schema

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/Claude Family/Identity Per Project.md
