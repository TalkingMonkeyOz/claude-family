---
projects:
- claude-family
tags:
- database
- work-tracking
- schema
- fk-constraints
synced: false
---

# Work Tracking Schema

Database schema for work item tracking with FK constraints.

---

## Tables Overview

| Table | Purpose | FK to Projects | FK to Sessions |
|-------|---------|----------------|----------------|
| `features` | Feature tracking | Required | Optional |
| `feedback` | Bugs, ideas | Required | Optional |
| `build_tasks` | Implementation | Via feature | Optional |
| `requirements` | Acceptance criteria | Via feature | Optional |

---

## Migration Script

```sql
-- Phase 1: FK Constraints for Work Tracking
-- Run against claude schema

-- 1. FEATURES
ALTER TABLE claude.features
  ALTER COLUMN project_id SET NOT NULL,
  ADD COLUMN IF NOT EXISTS created_session_id UUID,
  ADD COLUMN IF NOT EXISTS short_code SERIAL;

ALTER TABLE claude.features
  ADD CONSTRAINT fk_features_project
    FOREIGN KEY (project_id)
    REFERENCES claude.projects(project_id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_features_session
    FOREIGN KEY (created_session_id)
    REFERENCES claude.sessions(session_id) ON DELETE SET NULL;

-- 2. FEEDBACK
ALTER TABLE claude.feedback
  ALTER COLUMN project_id SET NOT NULL,
  ADD COLUMN IF NOT EXISTS created_session_id UUID,
  ADD COLUMN IF NOT EXISTS short_code SERIAL;

ALTER TABLE claude.feedback
  ADD CONSTRAINT fk_feedback_project
    FOREIGN KEY (project_id)
    REFERENCES claude.projects(project_id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_feedback_session
    FOREIGN KEY (created_session_id)
    REFERENCES claude.sessions(session_id) ON DELETE SET NULL;

-- 3. BUILD_TASKS
ALTER TABLE claude.build_tasks
  ADD COLUMN IF NOT EXISTS project_id UUID,
  ADD COLUMN IF NOT EXISTS created_session_id UUID,
  ADD COLUMN IF NOT EXISTS short_code SERIAL;

ALTER TABLE claude.build_tasks
  ADD CONSTRAINT fk_build_tasks_feature
    FOREIGN KEY (feature_id)
    REFERENCES claude.features(feature_id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_build_tasks_project
    FOREIGN KEY (project_id)
    REFERENCES claude.projects(project_id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_build_tasks_session
    FOREIGN KEY (created_session_id)
    REFERENCES claude.sessions(session_id) ON DELETE SET NULL;

-- 4. REQUIREMENTS
ALTER TABLE claude.requirements
  ADD COLUMN IF NOT EXISTS project_id UUID,
  ADD COLUMN IF NOT EXISTS created_session_id UUID;

ALTER TABLE claude.requirements
  ADD CONSTRAINT fk_requirements_feature
    FOREIGN KEY (feature_id)
    REFERENCES claude.features(feature_id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_requirements_project
    FOREIGN KEY (project_id)
    REFERENCES claude.projects(project_id) ON DELETE RESTRICT;

-- 5. INDEXES
CREATE INDEX IF NOT EXISTS idx_features_project ON claude.features(project_id);
CREATE INDEX IF NOT EXISTS idx_features_status ON claude.features(status);
CREATE INDEX IF NOT EXISTS idx_feedback_project ON claude.feedback(project_id);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON claude.feedback(status);
CREATE INDEX IF NOT EXISTS idx_build_tasks_feature ON claude.build_tasks(feature_id);
CREATE INDEX IF NOT EXISTS idx_build_tasks_project ON claude.build_tasks(project_id);
```

---

## Short Codes

Human-readable IDs for git branch names:
- Features: F1, F2, F3...
- Feedback: FB1, FB2, FB3...
- Build Tasks: BT1, BT2, BT3...

---

## Column Registry Values

See [[Data Gateway Usage]] for validation. Key statuses:

| Table | Column | Valid Values |
|-------|--------|--------------|
| features | status | draft, planned, in_progress, blocked, completed, cancelled |
| feedback | status | new, triaged, in_progress, resolved, wont_fix, duplicate |
| build_tasks | status | pending, in_progress, blocked, completed, cancelled |

---

## Related

- [[Work Tracking Compliance Plan]] - Overview
- [[Work Tracking Git Integration]] - Branch/commit linking
- [[Data Gateway Usage]] - Validation rules

---

**Version**: 1.0
**Created**: 2026-01-03
**Updated**: 2026-01-03
**Location**: knowledge-vault/20-Domains/Database/Work Tracking Schema.md
