---
projects:
  - claude-family
tags:
  - database
  - schema
  - reference
  - supporting
synced: false
---

# Database Schema - Supporting Tables

**Part of**: [[Database Schema - Overview]]

**Database**: `ai_company_foundation`
**Schema**: `claude`
**Focus**: 50+ supporting tables, critical issues, and recommended fixes

This document provides an overview of supporting tables, identifies critical issues, and recommends schema improvements.

---

## Supporting Tables (Summary)

These 50+ tables support the core functionality. Grouped by domain:

### Work Items (8 tables)
| Table | Purpose |
|-------|---------|
| build_tasks | Development tasks |
| work_tasks | General work items |
| pm_tasks | Project management tasks |
| features | Feature registry |
| feedback | Issue/feedback tracking |
| feedback_comments | Comments on feedback |
| feedback_screenshots | Screenshot attachments |
| ideas | Idea capture |

### Process Workflow (8 tables)
| Table | Purpose |
|-------|---------|
| process_registry | Workflow definitions |
| process_steps | Steps within processes |
| process_triggers | Keyword triggers |
| process_runs | Execution history |
| process_dependencies | Process interconnections |
| process_classification_log | Router decisions |
| workflow_state | Active workflow state |
| procedures | Legacy procedures |

### Governance (8 tables)
| Table | Purpose |
|-------|---------|
| column_registry | Valid values for columns |
| schema_registry | Schema documentation |
| enforcement_log | Reminder/enforcement tracking |
| compliance_audits | Audit results |
| audit_schedule | Audit scheduling |
| reviewer_runs | Auto-reviewer executions |
| reviewer_specs | Reviewer configurations |
| test_runs | Test execution results |

### Knowledge (5 tables)
| Table | Purpose |
|-------|---------|
| knowledge | Synced from Obsidian vault |
| knowledge_retrieval_log | Query tracking |
| documents | Document registry |
| doc_templates | Document templates |
| document_projects | Doc-project links |

### MCP Orchestration (5 tables)
| Table | Purpose |
|-------|---------|
| mcp_configs | MCP server configurations |
| messages | Inter-Claude messaging |
| async_tasks | Async agent tracking |
| actions | Shared actions for MCW |
| config_deployment_log | Config deployment history |

### Scheduling (3 tables)
| Table | Purpose |
|-------|---------|
| scheduled_jobs | Cron-like job definitions |
| job_run_history | Job execution history |
| reminders | Session reminders |

### Project Management (5 tables)
| Table | Purpose |
|-------|---------|
| programs | Program groupings |
| phases | Project phases |
| requirements | Project requirements |
| project_docs | Document metadata |
| project_command_assignments | Command assignments |
| project_config_assignments | Config assignments |

### Configuration (3 tables)
| Table | Purpose |
|-------|---------|
| config_templates | Config template definitions |
| shared_commands | Shared slash commands |
| components | UI/system components |

### Other (5 tables)
| Table | Purpose |
|-------|---------|
| architecture_decisions | ADR tracking |
| activity_feed | Activity stream |
| capability_usage | Feature usage tracking |
| feature_usage | Feature toggle tracking |

---

## Critical Issues Summary

### Missing Foreign Keys ⚠️

| Table | Column | Should Reference | Impact |
|-------|--------|------------------|--------|
| sessions | identity_id | identities.identity_id | 10% NULL values, no referential integrity |
| sessions | project_name | projects.project_id | String matching, name variants, no cascade |
| workspaces | added_by_identity_id | identities.identity_id | Can't track who added workspace |
| agent_sessions | metadata | Should have parent_session_id | All 144 agent sessions orphaned |

### Missing Indexes ⚠️

| Table | Column | Usage | Impact |
|-------|--------|-------|--------|
| sessions | identity_id | Frequent joins | Slow queries |
| sessions | project_name | Frequent filters | Table scans |
| sessions | session_start | Ordering | Slow sorts |
| identities | identity_name | Lookups | No benefit from index |
| projects | project_name | Frequent lookups | Table scans |

### Data Quality Issues ⚠️

- **39 sessions** (10%) have NULL identity_id
- **164 sessions** (41.5%) missing session_summary
- **2 sessions** still marked active from Dec 21 (stale)
- **144 agent sessions** have no parent link
- **Project names** have variants: "ATO-Tax-Agent" vs "ato-tax-agent"

---

## Recommended Schema Fixes

**Note**: These are documented for future implementation, not implemented yet.

### Priority 1: Add Foreign Keys

```sql
-- Sessions to identities
ALTER TABLE claude.sessions
ADD CONSTRAINT sessions_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude.identities(identity_id);

-- Workspaces to identities
ALTER TABLE claude.workspaces
ADD CONSTRAINT workspaces_identity_fkey
FOREIGN KEY (added_by_identity_id) REFERENCES claude.identities(identity_id);
```

### Priority 2: Add Missing Indexes

```sql
CREATE INDEX idx_sessions_identity ON claude.sessions(identity_id);
CREATE INDEX idx_sessions_project ON claude.sessions(project_name);
CREATE INDEX idx_sessions_start ON claude.sessions(session_start DESC);
CREATE INDEX idx_identities_name ON claude.identities(identity_name);
CREATE INDEX idx_projects_name ON claude.projects(project_name);
```

### Priority 3: Add parent_session_id to agent_sessions

```sql
ALTER TABLE claude.agent_sessions
ADD COLUMN parent_session_id uuid;

ALTER TABLE claude.agent_sessions
ADD CONSTRAINT agent_sessions_parent_fkey
FOREIGN KEY (parent_session_id) REFERENCES claude.sessions(session_id);

CREATE INDEX idx_agent_sessions_parent ON claude.agent_sessions(parent_session_id);
```

---

## Table Organization Strategy

The 57 tables are organized into 10 domains:

1. **Core Tracking** (7 tables) - Sessions, identities, projects, workspaces, agents, MCP usage, state
2. **Work Items** (8 tables) - Feedback, features, tasks, ideas
3. **Process Workflow** (8 tables) - Process registry, execution, triggers
4. **Governance** (8 tables) - Compliance, audits, validation, testing
5. **Knowledge** (5 tables) - Document registry, templates, retrieval
6. **MCP Orchestration** (5 tables) - Configs, messaging, async tasks
7. **Scheduling** (3 tables) - Jobs, reminders, history
8. **Project Management** (6 tables) - Programs, phases, requirements, assignments
9. **Configuration** (3 tables) - Templates, commands, components
10. **Activity & Usage** (5 tables) - ADRs, activity stream, usage tracking

---

## Migration Path

When implementing the recommended fixes:

1. **Phase 1** (Immediate): Add foreign keys to prevent data corruption
2. **Phase 2** (Week 1): Add missing indexes for query performance
3. **Phase 3** (Week 2): Backfill parent_session_id for agent_sessions
4. **Phase 4** (Ongoing): Clean up data quality issues

---

## Related Documents

See **[[Database Schema - Overview]]** for full navigation.

- [[Database Schema - Core Tables]] - Core session/identity tracking
- [[Database Schema - Workspace and Agents]] - Workspace/agent execution
- [[Database Architecture]] - Overview of all 57 tables
- [[Identity System]] - How identity per project should work
- [[Session Lifecycle]] - Complete session flow

---

**Version**: 2.0 (split from Database Schema - Core Tables)
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Database Schema - Supporting Tables.md
