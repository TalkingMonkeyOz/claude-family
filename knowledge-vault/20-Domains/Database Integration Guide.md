---
synced: true
synced_at: '2025-12-20T23:29:45.916709'
tags:
- database
- domain-knowledge
projects: []
---

# Database Integration Guide

**Category**: database
**Tags**: #database #integration #claude-family-manager #postgresql

---

## Overview

The Claude Family uses PostgreSQL database `ai_company_foundation` with a consolidated `claude` schema. This guide explains how to integrate database access into tools like claude-family-manager (Mission Control).

---

## Connection Details

```
Host: localhost
Port: 5432
Database: ai_company_foundation
Schema: claude
```

**Connection String Pattern:**
```
postgresql://postgres:{PASSWORD}@localhost:5432/ai_company_foundation
```

---

## Schema Categories (51 Tables)

### Session & Identity (4 tables)
| Table | Purpose |
|-------|---------|
| `sessions` | Session logs (who worked when) |
| `session_state` | Persisted todo/focus between sessions |
| `identities` | Claude identity registry |
| `messages` | Inter-Claude messaging |

### Project Management (9 tables)
| Table | Purpose |
|-------|---------|
| `projects` | Project registry (28 columns) |
| `programs` | Program groupings |
| `features` | Feature tracking |
| `components` | Component tracking |
| `requirements` | Requirements tracking |
| `build_tasks` | Development tasks |
| `pm_tasks` | Project management tasks |
| `work_tasks` | Generic work items |
| `phases` | Project phases |

### Feedback & Ideas (4 tables)
| Table | Purpose |
|-------|---------|
| `feedback` | Bug reports, questions, changes |
| `feedback_comments` | Comments on feedback |
| `feedback_screenshots` | Attached screenshots |
| `ideas` | Idea capture |

### Knowledge & Docs (7 tables)
| Table | Purpose |
|-------|---------|
| `knowledge` | Synced from Obsidian vault |
| `knowledge_retrieval_log` | What knowledge was queried |
| `procedures` | SOPs and procedures |
| `documents` | Document registry |
| `document_projects` | Document-project links |
| `project_docs` | Project-specific docs |
| `doc_templates` | Document templates |

### Process & Workflow (7 tables) ⚠️ DEPRECATED
| Table | Purpose |
|-------|---------|
| `process_registry` | ~~Workflow definitions~~ (replaced by skills) |
| `process_steps` | ~~Steps for each process~~ |
| `process_triggers` | ~~Keywords that trigger processes~~ |
| `process_runs` | ~~Execution history~~ |
| `process_dependencies` | ~~Workflow interconnections~~ |
| `process_classification_log` | ~~Classification history~~ |
| `workflow_state` | ~~Active workflow state~~ |

**Note**: Process workflow system replaced by skills (`skill_content`) and RAG. Tables archived.

### MCP & Agents (5 tables)
| Table | Purpose |
|-------|---------|
| `mcp_usage` | MCP tool call logging |
| `mcp_usage_stats` | Aggregated stats |
| `mcp_configs` | MCP server configurations |
| `agent_sessions` | Spawned agent sessions |
| `async_tasks` | Async agent tracking |

### Quality & Compliance (6 tables)
| Table | Purpose |
|-------|---------|
| `compliance_audits` | Audit results |
| `audit_schedule` | Audit scheduling |
| `audits_due` | Due audit view |
| `reviewer_runs` | Auto-reviewer executions |
| `reviewer_specs` | Reviewer specifications |
| `test_runs` | Test execution history |

### System & Config (7 tables)
| Table | Purpose |
|-------|---------|
| `column_registry` | Valid values for constrained columns |
| `schema_registry` | Schema documentation |
| `enforcement_log` | Reminder/enforcement logging |
| `actions` | Shared actions (MCW + CLI) |
| `reminders` | Reminder system |
| `scheduled_jobs` | Job scheduling |
| `job_run_history` | Job execution history |

---

## Data Gateway Pattern

**MANDATORY**: Before writing to constrained columns, check `column_registry`:

```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'TABLE' AND column_name = 'COLUMN';
```

### Common Constraints

| Table.Column | Valid Values |
|--------------|--------------|
| `projects.status` | active, paused, archived, completed |
| `projects.phase` | idea, research, planning, implementation, maintenance, archived |
| `projects.priority` | 1, 2, 3, 4, 5 |
| `feedback.feedback_type` | bug, design, question, change |
| `feedback.status` | new, in_progress, resolved, wont_fix, duplicate |
| `features.status` | not_started, planned, in_progress, blocked, completed, cancelled |
| `build_tasks.status` | todo, in_progress, completed, blocked, cancelled |
| `messages.message_type` | task_request, status_update, question, notification, handoff, broadcast |
| `sessions.status` | active, ended, abandoned |

---

## Key Queries for Mission Control

### Dashboard Overview
```sql
-- Active sessions
SELECT * FROM claude.sessions
WHERE status = 'active'
ORDER BY session_start DESC;

-- Open feedback by project
SELECT project_id, COUNT(*) as open_count
FROM claude.feedback
WHERE status IN ('new', 'in_progress')
GROUP BY project_id;

-- Recent activity
SELECT * FROM claude.activity_feed
ORDER BY occurred_at DESC LIMIT 20;
```

### Project View
```sql
-- Project with counts
SELECT
    p.*,
    (SELECT COUNT(*) FROM claude.features f WHERE f.project_id = p.project_id) as feature_count,
    (SELECT COUNT(*) FROM claude.feedback fb WHERE fb.project_id = p.project_id AND fb.status IN ('new', 'in_progress')) as open_feedback
FROM claude.projects p
WHERE p.is_archived = false;
```

### Build Tracker
```sql
-- Features with components and tasks
SELECT
    f.feature_id, f.feature_name, f.status as feature_status,
    c.component_id, c.component_name, c.status as component_status,
    t.task_id, t.task_name, t.status as task_status
FROM claude.features f
LEFT JOIN claude.components c ON c.feature_id = f.feature_id
LEFT JOIN claude.build_tasks t ON t.component_id = c.component_id
WHERE f.project_id = '{PROJECT_UUID}'
ORDER BY f.priority, c.sort_order, t.priority;
```

---

## Dynamic Configuration

Mission Control uses **dynamic configuration** - database drives the UI:

1. **Actions table** (`claude.actions`) - Defines available actions for each context
2. **Column registry** (`claude.column_registry`) - Provides valid values for dropdowns
3. **Skill content** (`claude.skill_content`) - Domain skills for guidance

### Adding New Actions
```sql
INSERT INTO claude.actions (action_name, action_type, description, context, is_active)
VALUES ('archive_project', 'project', 'Archive a project', 'project_detail', true);
```

### Getting Actions for Context
```sql
SELECT action_name, description, icon, hotkey
FROM claude.actions
WHERE context = 'project_list' AND is_active = true
ORDER BY sort_order;
```

---

## Migration from Deprecated Schemas

**Deprecated** (remove by Dec 8, 2025):
- `claude_family.*` - Use `claude.*` instead
- `claude_pm.*` - Use `claude.*` instead

**Migration Mapping:**
| Old | New |
|-----|-----|
| `claude_family.session_history` | `claude.sessions` |
| `claude_family.instance_messages` | `claude.messages` |
| `claude_family.identities` | `claude.identities` |
| `claude_pm.projects` | `claude.projects` |
| `claude_pm.features` | `claude.features` |
| `claude_pm.tasks` | `claude.build_tasks` |

---

## Finding This Information

### In Vault
- `knowledge-vault/20-Domains/Database Integration Guide.md` (this file)
- `knowledge-vault/40-Procedures/Family Rules.md` - Database rules

### In Database
```sql
-- List all tables
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'claude' ORDER BY table_name;

-- Get column info
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'claude' AND table_name = 'TABLE_NAME';

-- Check valid values
SELECT * FROM claude.column_registry
WHERE table_name = 'TABLE_NAME';
```

### In Code
- `CLAUDE.md` (project root) - Quick reference
- `~/.claude/CLAUDE.md` - Global rules

---

## Referential Integrity

The `claude` schema uses FK constraints to maintain data integrity. Key relationships:

| Child Table | Column | References | On Delete |
|-------------|--------|------------|-----------|
| `feedback_comments` | `feedback_id` | `feedback` | CASCADE |
| `feedback_screenshots` | `feedback_id` | `feedback` | CASCADE |
| `build_tasks` | `feature_id` | `features` | RESTRICT |
| `build_tasks` | `project_id` | `projects` | RESTRICT |
| `sessions` | `identity_id` | `identities` | RESTRICT |
| `todos` | `project_id` | `projects` | NO ACTION |
| `enforcement_log` | `session_id` | `sessions` | SET NULL |
| `knowledge_retrieval_log` | `session_id` | `sessions` | SET NULL |

**Full FK list**: 71 constraints in `claude` schema (as of Jan 2026).

### Important Indexes

| Table | Column | Purpose |
|-------|--------|---------|
| `sessions` | `project_name` | Fast project session lookup |
| `messages` | `to_project` | Message routing queries |
| `knowledge` | `knowledge_category` | Category filtering |

---

## nimbus_context Schema

The `nimbus_context` schema stores Nimbus-specific knowledge:

| Table | Purpose |
|-------|---------|
| `api_entities` | OData entity metadata |
| `api_properties` | Entity property details |
| `code_patterns` | Reusable code patterns |
| `project_learnings` | Lessons learned |
| `project_facts` | Known facts |
| `api_field_mappings` | **OData↔REST field name mappings** |

### API Field Mappings

Maps OData field names (PascalCase) to REST API field names (camelCase):

```sql
SELECT odata_field, rest_field, data_type
FROM nimbus_context.api_field_mappings
WHERE entity_name = 'User';
-- LocationID -> locationId
-- UserName -> userName
```

Entities covered: User, Location, Department, Schedule, Shift (54 mappings).

---

## Related Documents

- [[Family Rules]] - Coordination rules
- [[Observability]] - Logging and monitoring
- [[MCP configuration]] - MCP server setup

---

**Version**: 1.2 (Added FK constraints, indexes, nimbus_context schema)
**Created**: 2025-12-20
**Updated**: 2026-01-26
**Location**: knowledge-vault/20-Domains/Database Integration Guide.md