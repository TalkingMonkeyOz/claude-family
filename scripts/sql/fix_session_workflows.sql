-- Fix SESSION Workflow Issues
-- Date: 2025-12-08
-- Purpose: Fix critical issues found in SESSION_WORKFLOWS_TEST_REPORT_2025-12-08.md

-- ============================================================================
-- ISSUE #3: PROC-SESSION-004 missing command_ref
-- ============================================================================

UPDATE claude.process_registry
SET command_ref = '/session-resume'
WHERE process_id = 'PROC-SESSION-004';

-- ============================================================================
-- ISSUE #2: PROC-SESSION-004 has no process steps
-- ============================================================================

INSERT INTO claude.process_steps
(process_id, step_number, step_name, step_description, is_blocking, is_user_approval, timeout_seconds)
VALUES
('PROC-SESSION-004', 1, 'Read TODO File', 'Check for docs/TODO_NEXT_SESSION.md in project directory', true, false, 60),
('PROC-SESSION-004', 2, 'Parse TODO Content', 'Extract last session summary and next steps from TODO file', true, false, 60),
('PROC-SESSION-004', 3, 'Check Git Status', 'Run git status to count uncommitted files', false, false, 60),
('PROC-SESSION-004', 4, 'Check Inbox', 'Query MCP orchestrator for pending messages', false, false, 60),
('PROC-SESSION-004', 5, 'Display Resume Card', 'Format and present session resume information to user', false, false, 30);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify command_ref updated
SELECT process_id, process_name, command_ref
FROM claude.process_registry
WHERE process_id = 'PROC-SESSION-004';

-- Verify steps created
SELECT process_id, step_number, step_name, is_blocking
FROM claude.process_steps
WHERE process_id = 'PROC-SESSION-004'
ORDER BY step_number;

-- Verify all SESSION workflows now have steps
SELECT
    pr.process_id,
    pr.process_name,
    pr.command_ref,
    COUNT(ps.step_id) as step_count
FROM claude.process_registry pr
LEFT JOIN claude.process_steps ps ON pr.process_id = ps.process_id
WHERE pr.process_id LIKE 'PROC-SESSION-%'
GROUP BY pr.process_id, pr.process_name, pr.command_ref
ORDER BY pr.process_id;

-- ============================================================================
-- NOTES
-- ============================================================================

-- CRITICAL ISSUES REMAINING (require manual file edits):
--
-- 1. Update .claude/commands/session-start.md:
--    - Replace: claude_family.session_history → claude.sessions
--    - Replace: claude_family.universal_knowledge → claude.knowledge
--    - Replace: claude_pm.project_feedback → claude.feedback
--    - Replace: identity_id = 5 → identity_id = 'ff32276f-9d05-4a18-b092-31b54c82fff9'::uuid
--
-- 2. Update .claude/commands/session-end.md:
--    - Replace: claude_family.session_history → claude.sessions
--    - Replace: claude_family.universal_knowledge → claude.knowledge
--    - Replace: identity_id = 5 → identity_id = '<uuid>'::uuid
--
-- 3. Session-commit.md is mostly correct but verify all references
--
-- 4. Clean up stale process run:
--    UPDATE claude.process_runs
--    SET status = 'abandoned', completed_at = NOW()
--    WHERE run_id = '695078ca-885e-407a-a36b-db42c0771b60';
