---
projects:
  - claude-family
tags:
  - identity
  - architecture
  - design
synced: false
---

# Identity System - Overview

**Status**: ✅ IMPLEMENTED (2025-12-26)
**Current**: Identity per project (5 active projects have dedicated identities)
**See Also**: [[Identity System - Implementation]], [[Identity Per Project]]

---

## Concept: Identity Per Project

Each project has its own dedicated Claude identity.

```
Project               Identity
---------             ----------
claude-family    →    claude-family-lead
ATO-tax-agent    →    claude-ato-agent
nimbus-import    →    claude-nimbus
```

**Benefits**:
1. ✅ **Clear attribution**: "Who worked on this?" = check identity
2. ✅ **Better analytics**: Session/cost tracking per project
3. ✅ **Work isolation**: Different projects = different "personas"
4. ✅ **Message routing**: Can target specific project's Claude

---

## Problems Solved

### Before: Single Identity for All Projects

**Problem**: `claude-code-unified` used for ALL CLI sessions
- No way to distinguish Claude working on ATO-tax-agent vs nimbus-import
- Sessions missing identity (10% had NULL identity_id)
- claude-family-manager-v2: 100% sessions had NULL identity
- No foreign key enforcement (orphaned references possible)

### After: Dedicated Project Identities

**Solution**: 5 active projects, 5 dedicated identities
- `claude-claude-family` - Infrastructure lead
- `claude-ato-tax-agent` - Tax agent developer
- `claude-manager-v2` - Family manager developer
- `claude-nimbus-import` - Nimbus integration
- `claude-nimbus-user-loader` - Nimbus user loader

---

## Identity Resolution Flow

When a session starts, identity is determined in this order:

```
1. Check CLAUDE.md frontmatter for identity_id
   ↓
2. Check projects.default_identity_id
   ↓
3. Fall back to claude-code-unified
```

### Step 1: CLAUDE.md Header (Preferred)

```markdown
---
project_id: 20b5627c-e72c-4501-8537-95b559731b59
identity_id: ff32276f-9d05-4a18-b092-31b54c82fff9
---

# Claude Family - Infrastructure Project
```

### Step 2: Database Lookup

```sql
SELECT default_identity_id
FROM claude.projects
WHERE project_name = 'claude-family';
```

### Step 3: Fallback

If neither source provides identity: use `claude-code-unified`

---

## Database Schema

### projects.default_identity_id

```sql
ALTER TABLE claude.projects
ADD COLUMN default_identity_id uuid
REFERENCES claude.identities(identity_id);
```

Links each project to its default Claude identity.

### Foreign Key Enforcement

```sql
-- Sessions must reference valid identity
ALTER TABLE claude.sessions
ADD CONSTRAINT sessions_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude.identities(identity_id);
```

Prevents orphaned identity references.

---

## Benefits in Practice

### 1. Clear Work Attribution

```sql
-- Which identity worked on which projects?
SELECT
    i.identity_name,
    COUNT(DISTINCT s.project_name) as projects,
    COUNT(*) as sessions
FROM claude.sessions s
JOIN claude.identities i ON s.identity_id = i.identity_id
GROUP BY i.identity_name;
```

### 2. Cost Tracking Per Project

```sql
-- Total cost per project (sessions + agents)
SELECT
    s.project_name,
    COUNT(DISTINCT s.session_id) as sessions,
    SUM(a.estimated_cost_usd) as total_cost_usd
FROM claude.sessions s
LEFT JOIN claude.agent_sessions a ON a.created_by = s.identity_id::text
GROUP BY s.project_name;
```

### 3. Message Routing

```sql
-- Send message to specific project's Claude
INSERT INTO claude.messages (to_project, message_type, body)
VALUES ('ato-tax-agent', 'task_request', 'Please run the test suite');
```

---

## Identity Naming Convention

### Format

```
claude-{project-code}
```

### Examples

| Project | Identity Name | Role |
|---------|---------------|------|
| claude-family | claude-claude-family | Infrastructure lead |
| ATO-tax-agent | claude-ato-tax-agent | Tax agent developer |
| nimbus-import | claude-nimbus-import | Nimbus integration |

### Special Identities

| Identity | Purpose |
|----------|---------|
| claude-code-unified | Default fallback for CLI |
| claude-desktop | Desktop app |

---

## Environment Variables

| Variable | Set By | Purpose |
|----------|--------|---------|
| `CLAUDE_IDENTITY_ID` | Session hook | Which Claude instance |
| `CLAUDE_SESSION_ID` | Session hook | Link MCP calls to session |
| `CLAUDE_PROJECT_NAME` | Session hook | Project context |

---

## Related Documents

- [[Identity System - Implementation]] - Migration plan and technical details
- [[Identity Per Project]] - Quick-reference usage guide
- [[Database Schema - Core Tables]] - Sessions and identities tables
- [[Session Lifecycle]] - How identity is determined at session start

---

**Version**: 2.0 (Implemented)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: knowledge-vault/10-Projects/claude-family/Identity System - Overview.md
