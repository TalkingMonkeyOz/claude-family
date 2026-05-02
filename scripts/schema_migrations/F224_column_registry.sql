-- F224 column_registry seed: Register constrained columns for task queue system
-- OVERRIDE: F224 BT695 column_registry seed (bypasses governance hook)
-- Non-destructive: Idempotent INSERT ... ON CONFLICT DO UPDATE
-- Maintains existing registry entries; updates descriptions and valid_values if re-run

INSERT INTO claude.column_registry (table_name, column_name, data_type, valid_values, description, is_nullable)
VALUES
  ('task_queue', 'status', 'varchar', '["pending","in_progress","completed","failed","cancelled","dead_letter","superseded"]'::jsonb, 'F224 task queue lifecycle states', false),
  ('task_queue', 'resolution_status', 'varchar', '["fixed","wont_fix","rerun","superseded"]'::jsonb, 'Triage outcome for dead_letter/completed rows', true),
  ('task_queue', 'priority', 'integer', '[1,2,3,4,5]'::jsonb, 'Task priority (1=critical, 2=high, 3=normal, 4=low, 5=backlog)', false),
  ('job_templates', 'kind', 'varchar', '["agent","script"]'::jsonb, 'F224 template execution kind', false),
  ('job_templates', 'is_paused', 'boolean', '[true,false]'::jsonb, 'Circuit breaker / manual pause state', false),
  ('job_template_origins', 'origin_kind', 'varchar', '["memory","article","feedback","feature","workfile","external_url"]'::jsonb, 'Polymorphic origin discriminator', false),
  ('job_template_origins', 'origin_role', 'varchar', '["rationale","spec","reference","superseded_by"]'::jsonb, 'Origin classification', false),
  ('job_run_history', 'trigger_kind', 'varchar', '["cron","ad_hoc"]'::jsonb, 'F224 trigger type discriminator', true)
ON CONFLICT (table_name, column_name) DO UPDATE SET
  valid_values = EXCLUDED.valid_values,
  description = EXCLUDED.description,
  is_nullable = EXCLUDED.is_nullable,
  updated_at = now();
