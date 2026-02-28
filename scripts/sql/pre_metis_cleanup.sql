-- Pre-Metis Cleanup: Drop 43 unused tables from claude schema
-- Generated: 2026-02-28
-- Rollback tag: pre-metis-cleanup
-- Reference: knowledge-vault/20-Domains/Table Code Reference Map.md
--
-- Execute with: psql <connstring> -f scripts/sql/pre_metis_cleanup.sql

BEGIN;

-- ============================================================
-- WAVE 1: Never-built frameworks (26 tables)
-- No active code references. Historical data only.
-- ============================================================

-- Config testing framework (FK chain: scores -> runs -> configs/tasks)
DROP TABLE IF EXISTS claude.config_test_scores CASCADE;
DROP TABLE IF EXISTS claude.config_test_runs CASCADE;
DROP TABLE IF EXISTS claude.config_test_configs CASCADE;
DROP TABLE IF EXISTS claude.config_test_tasks CASCADE;

-- PM system (never activated)
DROP TABLE IF EXISTS claude.phases CASCADE;
DROP TABLE IF EXISTS claude.pm_tasks CASCADE;
DROP TABLE IF EXISTS claude.programs CASCADE;
DROP TABLE IF EXISTS claude.work_tasks CASCADE;

-- Standalone never-built tables
DROP TABLE IF EXISTS claude.ideas CASCADE;
DROP TABLE IF EXISTS claude.components CASCADE;
DROP TABLE IF EXISTS claude.requirements CASCADE;
DROP TABLE IF EXISTS claude.reminders CASCADE;
DROP TABLE IF EXISTS claude.budget_alerts CASCADE;
DROP TABLE IF EXISTS claude.models CASCADE;
DROP TABLE IF EXISTS claude.doc_templates CASCADE;
DROP TABLE IF EXISTS claude.project_docs CASCADE;
DROP TABLE IF EXISTS claude.reviewer_specs CASCADE;
DROP TABLE IF EXISTS claude.test_runs CASCADE;
DROP TABLE IF EXISTS claude.procedure_registry CASCADE;
DROP TABLE IF EXISTS claude.procedures CASCADE;
DROP TABLE IF EXISTS claude.app_logs CASCADE;
DROP TABLE IF EXISTS claude.tool_evaluations CASCADE;

-- Command sharing (FK chain: assignments -> shared_commands)
DROP TABLE IF EXISTS claude.project_command_assignments CASCADE;
DROP TABLE IF EXISTS claude.shared_commands CASCADE;

DROP TABLE IF EXISTS claude.project_config_assignments CASCADE;
DROP TABLE IF EXISTS claude.actions CASCADE;

-- ============================================================
-- WAVE 2: Orchestrator tables (retired 2026-02-24) (4 tables)
-- Code archived to archive/orchestrator-retired-20260224/
-- ============================================================

DROP TABLE IF EXISTS claude.agent_commands CASCADE;
DROP TABLE IF EXISTS claude.agent_status CASCADE;
DROP TABLE IF EXISTS claude.agent_definitions CASCADE;
DROP TABLE IF EXISTS claude.async_tasks CASCADE;

-- ============================================================
-- WAVE 3: Superseded systems (13 tables)
-- Code archived to archive/
-- ============================================================

-- Process router system (FK chain: deps/runs/steps/triggers -> registry)
DROP TABLE IF EXISTS claude.process_classification_log CASCADE;
DROP TABLE IF EXISTS claude.process_dependencies CASCADE;
DROP TABLE IF EXISTS claude.process_runs CASCADE;
DROP TABLE IF EXISTS claude.process_steps CASCADE;
DROP TABLE IF EXISTS claude.process_triggers CASCADE;
DROP TABLE IF EXISTS claude.process_registry CASCADE;

-- Standalone superseded
DROP TABLE IF EXISTS claude.mcp_configs CASCADE;
DROP TABLE IF EXISTS claude.feedback_comments CASCADE;
DROP TABLE IF EXISTS claude.feedback_screenshots CASCADE;
DROP TABLE IF EXISTS claude.git_workflow_deployments CASCADE;
DROP TABLE IF EXISTS claude.architecture_decisions CASCADE;

-- Global config (FK chain: versions -> config)
DROP TABLE IF EXISTS claude.global_config_versions CASCADE;
DROP TABLE IF EXISTS claude.global_config CASCADE;

COMMIT;

-- Post-drop: Run these to update registries:
-- python scripts/schema_docs.py --all
-- python scripts/embed_schema.py
