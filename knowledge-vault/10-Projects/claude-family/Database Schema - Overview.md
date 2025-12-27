---
projects:
  - claude-family
tags:
  - database
  - schema
  - reference
  - overview
synced: false
---

# Database Schema - Overview

**Database**: `ai_company_foundation`
**Schema**: `claude` (57 tables total)
**Core Tables**: 7 (session/identity tracking)

This document provides an overview of the Claude Family database architecture and links to detailed documentation for each table grouping.

---

## Introduction

The Claude Family uses PostgreSQL to track sessions, identities, projects, and coordination across multiple Claude instances. This knowledge vault contains comprehensive documentation split into four sections:

1. **[[Database Schema - Overview]]** (this file) - Architecture and relationships
2. **[[Database Schema - Core Tables]]** - Core session tracking (sessions, identities, projects)
3. **[[Database Schema - Workspace and Agents]]** - Workspace and agent execution tracking
4. **[[Database Schema - Supporting Tables]]** - 50+ supporting tables, issues, and recommended fixes

---

## Core Tables

| Table | Purpose | Records | Key Columns |
|-------|---------|---------|-------------|
| **sessions** | Session logging | 395 | session_id, identity_id, project_name |
| **identities** | Claude identity registry | 12 | identity_id, identity_name, platform |
| **projects** | Project registry | 20 | project_id, project_name, phase |
| **workspaces** | Launcher workspaces | 10 | id, project_name, project_path |
| **agent_sessions** | Spawned agent tracking | 144 | session_id, agent_type, success |
| **mcp_usage** | MCP tool call tracking | 13 | usage_id, session_id, tool_name |
| **session_state** | Cross-session state | varies | project_name, todo_list, current_focus |

---

## Table Relationships (Current State)

**Critical Finding**: Only `mcp_usage` has proper foreign key constraints. All other relationships are enforced by application logic only, leading to data integrity issues.

```
┌─────────────┐
│ identities  │
│ (12 rows)   │
└──────┬──────┘
       │
       │ ⚠️  NO FK!
       │
┌──────▼──────┐      ⚠️  NO FK!      ┌──────────────┐
│  sessions   │◄────────────────────│   projects   │
│ (395 rows)  │  project_name only  │  (20 rows)   │
└──────┬──────┘                     └──────────────┘
       │
       │ ✅ HAS FK!
       │
┌──────▼──────┐
│  mcp_usage  │
│  (13 rows)  │
└─────────────┘

┌──────────────┐     ⚠️  NO FK!
│agent_sessions│  (no parent link)
│  (144 rows)  │
└──────────────┘

┌──────────────┐
│session_state │  (singleton per project)
│              │
└──────────────┘

┌──────────────┐     ⚠️  NO FK!
│ workspaces   │  added_by_identity_id
│  (10 rows)   │
└──────────────┘
```

---

## Table Groups

### Core Tracking (3 tables)
Documents fundamental session and identity management:
- **sessions** - Every Claude Code session
- **identities** - Claude instances and platforms
- **projects** - Project registry with lifecycle

See **[[Database Schema - Core Tables]]**

### Workspace & Agents (4 tables)
Tracks workspace configurations and spawned agent executions:
- **workspaces** - Launcher workspace configurations
- **agent_sessions** - Spawned agent tracking
- **mcp_usage** - MCP tool call analytics
- **session_state** - Cross-session persistence

See **[[Database Schema - Workspace and Agents]]**

### Supporting Tables (50+ tables)
Covers work items, workflows, governance, knowledge, orchestration, scheduling, and configuration:
- **Work Items** - 8 tables (feedback, features, tasks)
- **Process Workflow** - 8 tables (process registry, execution)
- **Governance** - 8 tables (column registry, audits, compliance)
- **Knowledge** - 5 tables (synced from Obsidian)
- **MCP Orchestration** - 5 tables (configs, messaging, async tasks)
- **Scheduling** - 3 tables (jobs, reminders)
- **Project Management** - 5 tables (programs, phases, requirements)
- **Configuration** - 3 tables (templates, commands, components)
- **Other** - 5 tables (ADRs, activity, usage)

See **[[Database Schema - Supporting Tables]]**

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

## Navigation

| Document | Focus |
|----------|-------|
| [[Database Schema - Core Tables]] | sessions, identities, projects (250 lines) |
| [[Database Schema - Workspace and Agents]] | workspaces, agent_sessions, mcp_usage, session_state (250 lines) |
| [[Database Schema - Supporting Tables]] | 50+ tables, issues, recommendations (200 lines) |

---

## Related Documents

- [[Database Architecture]] - Overview of all 57 tables
- [[Identity System]] - How identity per project should work
- [[Session Lifecycle]] - Complete session flow
- [[Family Rules]] - Database usage rules
- [[Claude Hooks]] - Enforcement layer

---

**Version**: 2.0 (split from Core Tables)
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Database Schema - Overview.md
