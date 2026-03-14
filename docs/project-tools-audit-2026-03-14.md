# Project-Tools MCP Server Audit

**File**: `mcp-servers/project-tools/server_v2.py`
**Date**: 2026-03-14
**Auditor**: reviewer-sonnet
**Total lines**: 6,437
**Total tools registered**: 70 (66 active after deprecation removal)

## Quick Stats

| Metric | Count |
|--------|-------|
| Total `@mcp.tool()` registrations | 70 → 66 (4 deprecated removed) |
| Active tools | 66 |
| Critical bugs | 0 (recall_entities verified working) |
| Medium issues | 3 |
| Low issues | 4 |

## Categories (66 active tools)

| Category | Count | Tools |
|----------|-------|-------|
| Session | 5 | get_schema, start_session, end_session, save_checkpoint, recover_session |
| Workflow | 11 | advance_status, start_work, complete_work, get_work_context, create_linked_task, create_feature, create_feedback, add_build_task, get_incomplete_todos, get_ready_tasks, promote_feedback, resolve_feedback |
| Knowledge | 6 | remember, recall_memories, consolidate_memories, decay_knowledge, link_knowledge, get_related_knowledge, mark_knowledge_applied |
| Session Facts | 6 | store_session_fact, recall_session_fact, list_session_facts, recall_previous_session_facts, store_session_notes, get_session_notes |
| Config | 4 | update_claude_md, deploy_claude_md, deploy_project, regenerate_settings |
| Conversations | 3 | extract_conversation, extract_insights, search_conversations |
| Books | 3 | store_book, store_book_reference, recall_book_reference |
| BPMN | 2 | sync_bpmn_processes, search_bpmn_processes |
| Protocol | 3 | update_protocol, get_protocol_history, get_active_protocol |
| Messaging | 9 | check_inbox, send_message, broadcast, acknowledge, reply_to, bulk_acknowledge, list_recipients, get_active_sessions, get_unactioned_messages, get_message_history |
| Workfiles | 4 | stash, unstash, list_workfiles, search_workfiles |
| WCC/Activities | 4 | create_activity, list_activities, update_activity, assemble_context |
| Entities | 2 | catalog, recall_entities |
| Maintenance | 1 | system_maintenance |

## Removed (deprecated tools — decorator removed, functions kept for internal use)

| Tool | Replacement | Reason |
|------|------------|--------|
| update_work_status | advance_status | Wrapper, adds confusion |
| store_knowledge | remember | Legacy, replaced by 3-tier memory |
| recall_knowledge | recall_memories | Legacy, replaced by budget-capped recall |
| graph_search | recall_memories | Legacy, graph walk now built into recall |

## Open Issues

| Priority | Issue | Fix |
|----------|-------|-----|
| Medium | recover_session hard-codes C--Projects- slug | Derive from workspaces.project_path |
| Medium | _run_async creates ThreadPoolExecutor per call | Use singleton executor |
| Medium | extract_insights shallow string matching | Add 150-char minimum, dedup guard |
| Low | deploy_project references non-existent tables | Remove rules/instructions from valid_components |
| Low | start_session swallows exceptions silently | Surface as warnings |
| Low | system_maintenance missing "Use when:" | Add to docstring |
| Backlog | 6,437 line monolith | Split into category modules |

---
**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: docs/project-tools-audit-2026-03-14.md
