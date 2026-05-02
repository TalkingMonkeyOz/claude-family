-- =============================================================================
-- F224: Local Task Queue + Worker Daemon (PG-backed)
-- BT694: Schema migration — 6 new tables + extensions to scheduled_jobs / job_run_history
-- =============================================================================
-- Author  : Claude (BT694, 2026-05-02)
-- Feature : F224
-- Applies : ai_company_foundation, schema claude.*
-- Safety  : ADDITIVE ONLY. Idempotent (safe to re-run 3x). No DROP, no NOT NULL
--           without default, no RENAME. Per storage-rules.md non-destructive
--           migration section.
-- Requires: PostgreSQL >= 9.6 (num_nonnulls() available; confirmed PG 18.0)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. claude.job_templates  (NEW — reusable template catalog)
-- ---------------------------------------------------------------------------
-- One row per kind-of-work this system knows how to run.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claude.job_templates (
  template_id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name                    varchar     NOT NULL UNIQUE,
  description             text        NOT NULL,
  kind                    varchar     NOT NULL,
  current_version         int         NOT NULL DEFAULT 1,
  owner                   varchar,                                            -- session_id or user
  is_paused               bool        DEFAULT false,
  paused_at               timestamptz,
  paused_reason           text,
  is_idempotent           bool        DEFAULT false,
  max_concurrent_runs     int         NOT NULL DEFAULT 1,
  max_attempts            int         NOT NULL DEFAULT 3,
  retry_backoff_base      int         NOT NULL DEFAULT 30,                    -- seconds
  retry_backoff_max       int         NOT NULL DEFAULT 3600,
  retry_jitter_pct        int         NOT NULL DEFAULT 25,
  lease_duration_secs     int         NOT NULL DEFAULT 300,
  transient_error_classes text[]      DEFAULT ARRAY['ConnectionError','TimeoutError','OSError','psycopg.OperationalError'],
  pause_threshold_fails   int         NOT NULL DEFAULT 5,
  pause_threshold_window_secs int     NOT NULL DEFAULT 600,
  created_at              timestamptz DEFAULT now(),
  updated_at              timestamptz DEFAULT now()
);

-- CHECK: kind must be 'agent' or 'script'
DO $$ BEGIN
  ALTER TABLE claude.job_templates
    ADD CONSTRAINT chk_job_templates_kind
    CHECK (kind IN ('agent', 'script'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ---------------------------------------------------------------------------
-- 2. claude.job_template_versions  (NEW — versioned payload)
-- ---------------------------------------------------------------------------
-- Mirrors claude.profiles versioning pattern.
-- payload shape: { command, args, cwd, env } for script;
--                { model, prompt, mcp_servers, max_tokens, on_finding_route } for agent
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claude.job_template_versions (
  version_id   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id  uuid        NOT NULL REFERENCES claude.job_templates(template_id) ON DELETE CASCADE,
  version      int         NOT NULL,
  payload      jsonb       NOT NULL,
  created_at   timestamptz DEFAULT now(),
  created_by   varchar,
  notes        text,
  UNIQUE (template_id, version)
);

-- ---------------------------------------------------------------------------
-- 3. claude.job_template_origins  (NEW — polymorphic 'why' linkage)
-- ---------------------------------------------------------------------------
-- Real FK enforcement via PG num_nonnulls() CHECK (exclusive arc pattern).
-- Exactly ONE of the origin_* columns must be non-null per row.
-- NOTE: workfile DDL referenced 'claude.articles' — correct table is
--       'claude.knowledge_articles' (verified 2026-05-02).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claude.job_template_origins (
  origin_id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id        uuid        NOT NULL REFERENCES claude.job_templates(template_id) ON DELETE CASCADE,
  origin_kind        varchar     NOT NULL,   -- memory|article|feedback|feature|workfile|external_url
  origin_memory_id   uuid        REFERENCES claude.knowledge(knowledge_id),
  origin_article_id  uuid        REFERENCES claude.knowledge_articles(article_id),
  origin_feedback_id uuid        REFERENCES claude.feedback(feedback_id),
  origin_feature_id  uuid        REFERENCES claude.features(feature_id),
  origin_workfile_id uuid        REFERENCES claude.project_workfiles(workfile_id),
  origin_url         text,
  origin_role        varchar     NOT NULL,
  note               text,
  created_at         timestamptz DEFAULT now()
);

-- CHECK: exclusive arc — exactly one origin column set
DO $$ BEGIN
  ALTER TABLE claude.job_template_origins
    ADD CONSTRAINT exactly_one_origin
    CHECK (
      num_nonnulls(
        origin_memory_id, origin_article_id, origin_feedback_id,
        origin_feature_id, origin_workfile_id, origin_url
      ) = 1
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- CHECK: origin_role valid values
DO $$ BEGIN
  ALTER TABLE claude.job_template_origins
    ADD CONSTRAINT chk_job_template_origins_role
    CHECK (origin_role IN ('rationale', 'spec', 'reference', 'superseded_by'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ---------------------------------------------------------------------------
-- 4. claude.scheduled_jobs  (EXISTING — additive extension)
-- ---------------------------------------------------------------------------
-- Add nullable FK to job_templates; existing rows untouched.
-- ---------------------------------------------------------------------------
ALTER TABLE claude.scheduled_jobs
  ADD COLUMN IF NOT EXISTS template_id      uuid NULL REFERENCES claude.job_templates(template_id),
  ADD COLUMN IF NOT EXISTS template_version int  NULL;   -- NULL = always use latest

-- ---------------------------------------------------------------------------
-- 5. claude.task_queue  (NEW — ad-hoc claim/lease/retry/dead-letter)
-- ---------------------------------------------------------------------------
-- Hot path. Status enum:
--   pending | in_progress | completed | failed | cancelled | dead_letter | superseded
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claude.task_queue (
  task_id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id              uuid        REFERENCES claude.job_templates(template_id),
  template_version         int,
  payload_override         jsonb,                                   -- NULL = use template payload
  status                   varchar     NOT NULL DEFAULT 'pending',
  priority                 int         NOT NULL DEFAULT 3,          -- 1-5, matches column_registry priority
  project_id               uuid,
  parent_session_id        uuid,                                    -- Claude session that enqueued
  idempotency_key          varchar,                                 -- sha256(template_id||version||payload)
  claimed_by               varchar,
  claimed_at               timestamptz,
  claimed_until            timestamptz,                             -- lease expiry
  attempts                 int         NOT NULL DEFAULT 0,
  next_attempt_at          timestamptz,
  last_error               text,
  result                   jsonb,                                   -- { output, findings:[], summary }
  output_text              text,                                    -- raw stdout/transcript
  surfaced_as_feedback_id  uuid        REFERENCES claude.feedback(feedback_id),
  resolution_status        varchar,
  resolved_at              timestamptz,
  resolved_by              varchar,
  resolution_notes         text,
  superseded_by_task_id    uuid        REFERENCES claude.task_queue(task_id),
  enqueued_at              timestamptz DEFAULT now(),
  started_at               timestamptz,
  completed_at             timestamptz
);

-- CHECK: status enum
DO $$ BEGIN
  ALTER TABLE claude.task_queue
    ADD CONSTRAINT chk_task_queue_status
    CHECK (status IN ('pending','in_progress','completed','failed','cancelled','dead_letter','superseded'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- CHECK: resolution_status enum
DO $$ BEGIN
  ALTER TABLE claude.task_queue
    ADD CONSTRAINT chk_task_queue_resolution_status
    CHECK (resolution_status IN ('fixed','wont_fix','rerun','superseded'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Claim path index — FIFO by priority + enqueue time, only pending rows
CREATE INDEX IF NOT EXISTS idx_task_queue_claim
  ON claude.task_queue (priority, enqueued_at)
  WHERE status = 'pending';

-- Per-template running-count index — for max_concurrent_runs subquery
CREATE INDEX IF NOT EXISTS idx_task_queue_running_per_template
  ON claude.task_queue (template_id)
  WHERE status = 'in_progress';

-- Idempotency dedupe — unique over active states only (pending or in_progress)
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_queue_idem_active
  ON claude.task_queue (idempotency_key)
  WHERE idempotency_key IS NOT NULL
    AND status IN ('pending', 'in_progress');

-- ---------------------------------------------------------------------------
-- 6. claude.job_run_history  (EXISTING — additive extension)
-- ---------------------------------------------------------------------------
-- One row per execution attempt regardless of trigger (cron or ad-hoc).
-- All new columns are nullable; existing rows untouched.
-- ---------------------------------------------------------------------------
ALTER TABLE claude.job_run_history
  ADD COLUMN IF NOT EXISTS template_id              uuid        REFERENCES claude.job_templates(template_id),
  ADD COLUMN IF NOT EXISTS template_version_snapshot int,
  ADD COLUMN IF NOT EXISTS payload_snapshot         jsonb,       -- pinned at run time, immutable
  ADD COLUMN IF NOT EXISTS trigger_kind             varchar,
  ADD COLUMN IF NOT EXISTS trigger_id               uuid,        -- scheduled_jobs.job_id or task_queue.task_id
  ADD COLUMN IF NOT EXISTS agent_session_id         uuid        REFERENCES claude.agent_sessions(session_id);

-- CHECK: trigger_kind enum
DO $$ BEGIN
  ALTER TABLE claude.job_run_history
    ADD CONSTRAINT chk_job_run_history_trigger_kind
    CHECK (trigger_kind IN ('cron', 'ad_hoc'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ---------------------------------------------------------------------------
-- 7. claude.task_queue_archive  (NEW — retention / append-only)
-- ---------------------------------------------------------------------------
-- Same shape as task_queue. Nightly archive job moves resolved rows here.
-- Separate table (not partition) to avoid locking the hot path during archival.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claude.task_queue_archive (
  task_id                  uuid        PRIMARY KEY,                -- original task_id preserved
  template_id              uuid,
  template_version         int,
  payload_override         jsonb,
  status                   varchar     NOT NULL,
  priority                 int         NOT NULL DEFAULT 3,
  project_id               uuid,
  parent_session_id        uuid,
  idempotency_key          varchar,
  claimed_by               varchar,
  claimed_at               timestamptz,
  claimed_until            timestamptz,
  attempts                 int         NOT NULL DEFAULT 0,
  next_attempt_at          timestamptz,
  last_error               text,
  result                   jsonb,
  output_text              text,
  surfaced_as_feedback_id  uuid,
  resolution_status        varchar,
  resolved_at              timestamptz,
  resolved_by              varchar,
  resolution_notes         text,
  superseded_by_task_id    uuid,
  enqueued_at              timestamptz,
  started_at               timestamptz,
  completed_at             timestamptz,
  archived_at              timestamptz DEFAULT now()               -- archive timestamp
);

-- ---------------------------------------------------------------------------
-- 8. claude.job_template_stats  (NEW — derived view)
-- ---------------------------------------------------------------------------
-- Rolling 30-day stats per template. Sourced from job_run_history.
-- Uses template_id column added above — safe because this is CREATE OR REPLACE.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW claude.job_template_stats AS
SELECT
  template_id,
  COUNT(*)                                                                          AS runs_total_30d,
  COUNT(*) FILTER (WHERE status = 'completed')                                      AS runs_succeeded_30d,
  COUNT(*) FILTER (WHERE status = 'dead_letter')                                    AS runs_dead_30d,
  AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))                              AS avg_duration_secs,
  PERCENTILE_CONT(0.95) WITHIN GROUP (
    ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at))
  )                                                                                 AS p95_duration_secs,
  MAX(completed_at)                                                                 AS last_run_at
FROM claude.job_run_history
WHERE started_at > now() - INTERVAL '30 days'
GROUP BY template_id;

-- =============================================================================
-- END OF F224_task_queue.sql
-- Applied: NOT YET — requires DBA review and supervised apply.
-- Validated via ROLLBACK transaction on 2026-05-02 (PG 18.0).
-- =============================================================================
