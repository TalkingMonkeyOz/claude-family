-- =====================================================================
-- F226 / BT718 — compat views over claude.work_items
-- =====================================================================
-- Purpose:
--   Read-only views that emit the same row shape as claude.features /
--   build_tasks / feedback / todos, projected from claude.work_items +
--   work_item_code_history. Phase 3 of the migration replaces the
--   physical legacy tables with these views; Phase 1 ships them as
--   parity surfaces for BT719's parity check.
--
--   The views rely on attributes->>'original_legacy_status' (stamped by
--   the backfill so the reverse map is exact) and code_history legacy
--   short_codes for the per-table integer short_code column.
--
-- Idempotency: CREATE OR REPLACE VIEW everywhere.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. v_features_compat
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW claude.v_features_compat AS
SELECT
    wi.work_item_id                                      AS feature_id,
    wi.title                                             AS feature_name,
    COALESCE(wi.attributes->>'feature_type_legacy', wi.kind)::varchar AS feature_type,
    wi.description                                       AS description,
    wi.parent_id                                         AS parent_feature_id,
    NULL::timestamp                                      AS planned_date,
    NULL::uuid                                           AS planned_by_identity_id,
    wi.priority                                          AS priority,
    COALESCE(wi.attributes->>'original_legacy_status',
             CASE wi.stage
                  WHEN 'raw'         THEN 'draft'
                  WHEN 'planned'     THEN 'planned'
                  WHEN 'in_progress' THEN 'in_progress'
                  WHEN 'blocked'     THEN 'blocked'
                  WHEN 'done'        THEN 'completed'
                  WHEN 'dropped'     THEN 'cancelled'
                  WHEN 'parked'      THEN 'planned'
                  WHEN 'triaged'     THEN 'planned'
             END)::varchar                               AS status,
    wi.completion_percentage                             AS completion_percentage,
    wi.started_at::timestamp                             AS started_date,
    wi.completed_at::timestamp                           AS completed_date,
    NULL::uuid                                           AS implemented_by_identity_id,
    wi.attributes->>'design_doc_path'                    AS design_doc_path,
    wi.attributes->>'implementation_notes'               AS implementation_notes,
    wi.created_at::timestamp                             AS created_at,
    wi.updated_at::timestamp                             AS updated_at,
    wi.project_id                                        AS project_id,
    wi.created_session_id                                AS created_session_id,
    (regexp_replace(h.short_code, '^F', ''))::int        AS short_code,
    wi.plan_data                                         AS plan_data
  FROM claude.work_items wi
  JOIN claude.work_item_code_history h
    ON h.work_item_id = wi.work_item_id
   AND h.code_kind = 'legacy'
   AND h.short_code LIKE 'F%'
   AND h.short_code !~ '^F[A-Z]'   -- exclude FB### / TODO-### / FIXTURE
 WHERE wi.attributes->>'legacy_table' = 'features'
   AND wi.is_deleted = false;

COMMENT ON VIEW claude.v_features_compat IS
    'F226 BT718: row-shape compat for claude.features projected from work_items + code_history. Used by BT719 parity job and by Phase 3 swap when features retires.';

-- ---------------------------------------------------------------------
-- 2. v_build_tasks_compat
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW claude.v_build_tasks_compat AS
SELECT
    wi.work_item_id                                      AS task_id,
    NULL::uuid                                           AS component_id,
    wi.parent_id                                         AS feature_id,
    wi.title                                             AS task_name,
    wi.description                                       AS task_description,
    (wi.attributes->>'task_type')::varchar               AS task_type,
    COALESCE(wi.attributes->>'original_legacy_status',
             CASE wi.stage
                  WHEN 'planned'     THEN 'todo'
                  WHEN 'triaged'     THEN 'todo'
                  WHEN 'raw'         THEN 'todo'
                  WHEN 'in_progress' THEN 'in_progress'
                  WHEN 'blocked'     THEN 'blocked'
                  WHEN 'done'        THEN 'completed'
                  WHEN 'dropped'     THEN 'cancelled'
                  WHEN 'parked'      THEN 'todo'
             END)::varchar                               AS status,
    wi.priority                                          AS priority,
    NULL::uuid                                           AS assigned_to_identity_id,
    wi.estimated_hours                                   AS estimated_hours,
    wi.actual_hours                                      AS actual_hours,
    wi.started_at::timestamp                             AS started_at,
    wi.completed_at::timestamp                           AS completed_at,
    wi.attributes->>'blocked_reason'                     AS blocked_reason,
    wi.blocked_by_id                                     AS blocked_by_task_id,
    wi.created_at::timestamp                             AS created_at,
    wi.updated_at::timestamp                             AS updated_at,
    wi.project_id                                        AS project_id,
    wi.created_session_id                                AS created_session_id,
    (regexp_replace(h.short_code, '^BT', ''))::int       AS short_code,
    NULLIF(wi.attributes->>'step_order','')::int         AS step_order,
    wi.files_affected                                    AS files_affected,
    wi.verification                                      AS verification
  FROM claude.work_items wi
  JOIN claude.work_item_code_history h
    ON h.work_item_id = wi.work_item_id
   AND h.code_kind = 'legacy'
   AND h.short_code LIKE 'BT%'
 WHERE wi.attributes->>'legacy_table' = 'build_tasks'
   AND wi.is_deleted = false;

COMMENT ON VIEW claude.v_build_tasks_compat IS
    'F226 BT718: row-shape compat for claude.build_tasks projected from work_items + code_history.';

-- ---------------------------------------------------------------------
-- 3. v_feedback_compat
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW claude.v_feedback_compat AS
SELECT
    wi.work_item_id                                      AS feedback_id,
    wi.project_id                                        AS project_id,
    wi.kind::varchar                                     AS feedback_type,
    wi.description                                       AS description,
    wi.attributes->>'screenshot_path'                    AS screenshot_path,
    COALESCE(wi.attributes->>'original_legacy_status',
             CASE wi.stage
                  WHEN 'raw'         THEN 'new'
                  WHEN 'triaged'     THEN 'triaged'
                  WHEN 'planned'     THEN 'triaged'
                  WHEN 'in_progress' THEN 'in_progress'
                  WHEN 'blocked'     THEN 'in_progress'
                  WHEN 'done'        THEN 'resolved'
                  WHEN 'dropped'     THEN 'wont_fix'
                  WHEN 'parked'      THEN 'triaged'
             END)::varchar                               AS status,
    wi.created_at::timestamp                             AS created_at,
    wi.updated_at::timestamp                             AS updated_at,
    wi.completed_at::timestamp                           AS resolved_at,
    wi.attributes->>'resolution_note'                    AS notes,
    -- Legacy feedback used varchar priority (high/medium/low). Reverse-map from the
    -- preserved string if available, else from int 1-5.
    COALESCE(wi.attributes->>'feedback_priority_legacy',
             CASE wi.priority
                  WHEN 1 THEN 'high'   WHEN 2 THEN 'high'
                  WHEN 3 THEN 'medium'
                  WHEN 4 THEN 'low'    WHEN 5 THEN 'low'
             END)::varchar                               AS priority,
    NULL::uuid                                           AS assigned_to,
    wi.created_session_id                                AS created_session_id,
    (regexp_replace(h.short_code, '^FB', ''))::int       AS short_code,
    wi.title                                             AS title
  FROM claude.work_items wi
  JOIN claude.work_item_code_history h
    ON h.work_item_id = wi.work_item_id
   AND h.code_kind = 'legacy'
   AND h.short_code LIKE 'FB%'
 WHERE wi.attributes->>'legacy_table' = 'feedback'
   AND wi.is_deleted = false;

COMMENT ON VIEW claude.v_feedback_compat IS
    'F226 BT718: row-shape compat for claude.feedback projected from work_items + code_history.';

-- ---------------------------------------------------------------------
-- 4. v_todos_compat
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW claude.v_todos_compat AS
SELECT
    wi.work_item_id                                      AS todo_id,
    wi.project_id                                        AS project_id,
    wi.created_session_id                                AS created_session_id,
    wi.completed_session_id                              AS completed_session_id,
    wi.description                                       AS content,
    wi.attributes->>'active_form'                        AS active_form,
    COALESCE(wi.attributes->>'original_legacy_status',
             CASE wi.stage
                  WHEN 'planned'     THEN 'pending'
                  WHEN 'in_progress' THEN 'in_progress'
                  WHEN 'done'        THEN 'completed'
                  WHEN 'dropped'     THEN
                      CASE wi.attributes->>'dropped_reason'
                           WHEN 'archived' THEN 'archived'
                           ELSE 'cancelled'
                      END
                  ELSE 'pending'
             END)::varchar                               AS status,
    wi.priority                                          AS priority,
    NULL::int                                            AS display_order,
    wi.created_at                                        AS created_at,
    wi.updated_at                                        AS updated_at,
    wi.completed_at                                      AS completed_at,
    wi.is_deleted                                        AS is_deleted,
    wi.deleted_at                                        AS deleted_at,
    NULLIF(wi.attributes->>'source_message_id','')::uuid AS source_message_id,
    NULLIF(wi.attributes->>'restore_count','')::int      AS restore_count,
    wi.task_scope                                        AS task_scope
  FROM claude.work_items wi
 WHERE wi.attributes->>'legacy_table' = 'todos';

COMMENT ON VIEW claude.v_todos_compat IS
    'F226 BT718: row-shape compat for claude.todos projected from work_items.';
