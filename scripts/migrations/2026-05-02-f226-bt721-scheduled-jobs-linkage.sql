-- =====================================================================
-- F226 / BT721 — claude.scheduled_jobs.linked_work_item_id (optional)
-- =====================================================================
-- Purpose:
--   Optional NULLABLE FK from a scheduled_jobs row to a work_items row.
--   Used when a job exists *to drive* a particular work item (e.g. the
--   F226 parity check links itself to F226 / W-coded equivalent).
--
--   Most rows leave it NULL. Provenance in the other direction (job →
--   work_item that the job created) is stamped on the work_items row
--   via attributes.created_by_job_id, not here.
--
-- Idempotency: ADD COLUMN IF NOT EXISTS, additive only.
-- =====================================================================

ALTER TABLE claude.scheduled_jobs
    ADD COLUMN IF NOT EXISTS linked_work_item_id UUID
    REFERENCES claude.work_items(work_item_id);

COMMENT ON COLUMN claude.scheduled_jobs.linked_work_item_id IS
    'F226 BT721: optional pointer to a work_item this job exists to drive (e.g. parity check job linked to its tracking work_item). Most rows are NULL.';

-- Index for the rare reverse lookup ("which job drives W42?")
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_linked_work_item
    ON claude.scheduled_jobs (linked_work_item_id)
    WHERE linked_work_item_id IS NOT NULL;

-- Wire f226-parity-check to its tracking work_item (F226 → W-coded equivalent).
-- Idempotent: only fires when the column is currently NULL.
UPDATE claude.scheduled_jobs sj
   SET linked_work_item_id = wi.work_item_id
  FROM claude.work_item_code_history h
  JOIN claude.work_items wi ON wi.work_item_id = h.work_item_id
 WHERE sj.job_name = 'f226-parity-check'
   AND sj.linked_work_item_id IS NULL
   AND h.short_code = 'F226' AND h.code_kind = 'legacy';
