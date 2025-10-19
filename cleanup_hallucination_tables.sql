-- HALLUCINATION TABLE CLEANUP
-- Created: 2025-10-19
-- Purpose: Drop 45 empty tables that were hallucinated and never used
-- Backup: Git tag 'pre-cleanup' created before execution

-- PUBLIC SCHEMA CLEANUP (45 tables)

-- AI Company Infrastructure (never implemented)
DROP TABLE IF EXISTS public.departments CASCADE;
DROP TABLE IF EXISTS public.ai_agents CASCADE;
DROP TABLE IF EXISTS public.ai_personas CASCADE;
DROP TABLE IF EXISTS public.agent_performance_log CASCADE;
DROP TABLE IF EXISTS public.agent_messages CASCADE;
DROP TABLE IF EXISTS public.cursor_agent_tracking CASCADE;

-- Batch Processing (never used)
DROP TABLE IF EXISTS public.batch_jobs CASCADE;
DROP TABLE IF EXISTS public.batch_results CASCADE;
DROP TABLE IF EXISTS public.batch_requests CASCADE;

-- Elaborate Tracking (hallucinated features)
DROP TABLE IF EXISTS public.enforcement_log CASCADE;
DROP TABLE IF EXISTS public.diana_accountability_log CASCADE;
DROP TABLE IF EXISTS public.learning_insights CASCADE;
DROP TABLE IF EXISTS public.capability_registry CASCADE;

-- Complex Workflow Systems (over-engineered)
DROP TABLE IF EXISTS public.workflow_states CASCADE;
DROP TABLE IF EXISTS public.schedule_instances CASCADE;
DROP TABLE IF EXISTS public.recurring_tasks CASCADE;

-- Unused Communication Features
DROP TABLE IF EXISTS public.conversations CASCADE;
DROP TABLE IF EXISTS public.messages CASCADE;
DROP TABLE IF EXISTS public.reminders CASCADE;
DROP TABLE IF EXISTS public.reminder_log CASCADE;

-- Unused Project Management Extensions
DROP TABLE IF EXISTS public.deferred_tasks CASCADE;
DROP TABLE IF EXISTS public.tasks CASCADE;
DROP TABLE IF EXISTS public.sub_tasks CASCADE;
DROP TABLE IF EXISTS public.task_history CASCADE;
DROP TABLE IF EXISTS public.ideas_backlog CASCADE;
DROP TABLE IF EXISTS public.project_timeline_events CASCADE;
DROP TABLE IF EXISTS public.project_milestones CASCADE;
DROP TABLE IF EXISTS public.project_health_checks CASCADE;
DROP TABLE IF EXISTS public.project_risks CASCADE;
DROP TABLE IF EXISTS public.project_audits CASCADE;

-- Unused SOP Extensions
DROP TABLE IF EXISTS public.sop_steps CASCADE;
DROP TABLE IF EXISTS public.sop_executions CASCADE;

-- Unused Knowledge Systems
DROP TABLE IF EXISTS public.knowledge_base CASCADE;
DROP TABLE IF EXISTS public.solution_patterns CASCADE;
DROP TABLE IF EXISTS public.anti_patterns CASCADE;
DROP TABLE IF EXISTS public.decisions_log CASCADE;

-- Unused Session/Cost Tracking
DROP TABLE IF EXISTS public.subscription_costs CASCADE;
DROP TABLE IF EXISTS public.ai_sessions CASCADE;
DROP TABLE IF EXISTS public.ai_attempts CASCADE;
DROP TABLE IF EXISTS public.ai_requests_universal CASCADE;
DROP TABLE IF EXISTS public.session_context CASCADE;

-- Unused System Management
DROP TABLE IF EXISTS public.system_config CASCADE;
DROP TABLE IF EXISTS public.system_health CASCADE;
DROP TABLE IF EXISTS public.process_registry CASCADE;
DROP TABLE IF EXISTS public.audit_triggers CASCADE;

-- TABLES TO KEEP (8 total)
-- ✅ work_packages (8 rows) - active project tracking
-- ✅ projects (3 rows) - project metadata
-- ✅ api_cost_tracking (2 rows) - cost monitoring
-- ✅ diana_inbox (1 row) - reminder system
-- ✅ sops (1 row) - SOP registry
-- ✅ claude_family.session_history (14 rows) - who did what
-- ✅ claude_family.shared_knowledge (4 rows) - learned patterns
-- ✅ claude_family.identities (1 row) - Claude instances

-- VERIFICATION QUERY (run after cleanup)
SELECT
    schemaname,
    COUNT(*) as total_tables,
    SUM(CASE WHEN n_live_tup > 0 THEN 1 ELSE 0 END) as tables_with_data,
    SUM(CASE WHEN n_live_tup = 0 THEN 1 ELSE 0 END) as empty_tables
FROM pg_stat_user_tables
WHERE schemaname IN ('claude_family', 'public')
GROUP BY schemaname;

-- Expected result after cleanup:
-- claude_family: 5 tables, 3 with data, 2 empty
-- public: 5 tables, 5 with data, 0 empty ✅
