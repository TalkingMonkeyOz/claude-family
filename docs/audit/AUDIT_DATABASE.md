# Audit: Database Schema

**Part of**: [Infrastructure Audit Report](../INFRASTRUCTURE_AUDIT_REPORT.md)

---

## Schema Overview

| Schema | Tables | Status |
|--------|--------|--------|
| claude | 65 | ✅ Primary (ACTIVE) |
| claude_family | 3 | ⚠️ Legacy |
| claude_pm | 1 | ⚠️ Legacy |

---

## Key Tables

| Table | Records | Purpose |
|-------|---------|---------|
| sessions | 409+ | Session tracking |
| todos | ~50 | Persistent todos |
| feedback | ~100 | Bug/feature tracking |
| projects | 31 | Project registry |
| workspaces | 16 | Active workspace configs |
| vault_embeddings | 1,149 | RAG chunks |
| messages | ~20 | Inter-Claude messaging |

---

## Foreign Key Relationships (30)

Key relationships:
- sessions → projects, identities
- todos → sessions, projects
- feedback → projects
- features → projects
- build_tasks → features
- messages → sessions

---

## Issues Found

### 1. Duplicate FK Constraint
```sql
-- mcp_usage.session_id has duplicate FK
ALTER TABLE claude.mcp_usage DROP CONSTRAINT mcp_usage_session_id_fkey1;
```

### 2. Missing Indexes (10)

| Table | Column | Fix |
|-------|--------|-----|
| todos | session_id | `CREATE INDEX idx_todos_session_id ON claude.todos(session_id);` |
| feedback | project_id | `CREATE INDEX idx_feedback_project_id ON claude.feedback(project_id);` |
| build_tasks | feature_id | `CREATE INDEX idx_build_tasks_feature_id ON claude.build_tasks(feature_id);` |
| messages | session_id | `CREATE INDEX idx_messages_session_id ON claude.messages(session_id);` |

---

## Deprecated Tables (DO NOT USE)

These tables are referenced in old docs but **don't exist**:
- `claude_family.session_history`
- `claude_family.universal_knowledge`
- `claude_pm.project_feedback`

**Correct tables**:
- `claude.sessions`
- `claude.knowledge`
- `claude.feedback`

---

**Version**: 1.0
**Created**: 2026-01-03
**Location**: docs/audit/AUDIT_DATABASE.md
