---
projects:
- claude-family
- Project-Metis
tags:
- audit
- mcp
- tools
synced: false
---

# Audit: MCP Tools & Servers

**Parent**: [[claude-family-systems-audit]]
**Raw data**: `docs/audit/mcp_tools_audit.md` (18K chars)

---

## What It Is

Custom FastMCP servers exposing high-level business operations as tools Claude can call. Replaces raw SQL with encapsulated operations that handle validation, state transitions, and side effects internally.

## Server Inventory

| Server | Tools | Status | Purpose |
|--------|-------|--------|---------|
| `project-tools` | 72 | Active | Core business operations |
| `bpmn-engine` | 10 | Active | BPMN process governance |
| `postgres` | ~8 | Active (external) | Direct SQL access |
| `sequential-thinking` | 1 | Active (external) | Multi-step reasoning |
| `tool-search` | 3 | Deployed, unused | Tool discovery |
| `vault-rag` | 4 | Retired | Replaced by RAG hook |
| `playwright` | ~20 | Active (external) | Browser automation |
| `mui` | 2 | Active (external) | MUI component docs |

## project-tools Tool Categories (72 total)

| Category | Count | Key Tools | Assessment |
|----------|-------|-----------|------------|
| Session | 4 | start_session, end_session, save_checkpoint, recover_session | Core; heavily used |
| Workflow Engine | 5 | advance_status, start_work, complete_work, get_work_context, create_linked_task | Core; enforces state machines |
| Cognitive Memory | 6 | remember, recall_memories, consolidate_memories + 3 | Good design; replaces legacy |
| Session Facts | 6 | store/recall/list session facts, notes | Essential for compaction survival |
| Knowledge (Legacy) | 4 | store_knowledge, recall_knowledge, graph_search, decay_knowledge | Still works; superseded by cognitive memory |
| Work Items | 6 | create_feedback, create_feature, add_build_task + 3 | Core work tracking |
| Messaging | 10 | check_inbox, send_message, broadcast, acknowledge + 6 | Working but low usage (187 messages) |
| Config | 4 | update_claude_md, deploy_claude_md, deploy_project, regenerate_settings | Self-healing config |
| Books/Conversations | 6 | store_book + 5 | Under-utilized (3 books, 12 conversations) |
| Protocol | 3 | update/get_active/get_history protocol | Working (8 versions tracked) |
| BPMN Registry | 2 | sync_bpmn_processes, search_bpmn_processes | sync broken (ImportError) |
| Maintenance | 2 | system_maintenance, get_schema | Working |

## Architecture Issue: server.py vs server_v2.py

The code is split across two files:
- **server.py**: All async implementations (plain `async def tool_*()` functions, NOT decorated)
- **server_v2.py**: Active FastMCP entrypoint. Imports from server.py, wraps with `_run_async()`, plus native sync tools for Phase 2-4.

This creates: dual maintenance burden, confusion about which is authoritative, potential deadlock via `ThreadPoolExecutor` bridge.

**MEMORY.md note "server_v2.py is uncommitted" is outdated** — it contains substantial production code.

## WorkflowEngine

Enforces state transitions via 28 rules in `claude.workflow_transitions`. Conditions (e.g., `all_tasks_done` for feature completion) and side effects (e.g., `check_feature_completion` on task done) are coded in server_v2.py.

All transitions logged to `claude.audit_log`. Invalid transitions return error with list of valid next states.

**Assessment**: Well-designed. Prevents the most common data corruption (invalid status values). The `start_work`/`complete_work` pattern loads context + transitions + suggests next task in one call.

## Issues

1. **72 tools is too many** — Claude must pick from 72+ tools per prompt. Tool discovery is a real problem.
2. **BPMN sync broken** — `sync_bpmn_to_db.py` imports `_discover_process_files` and `_parse_bpmn_file` which don't exist in server.py.
3. **Under-utilized tools** — Books (3 entries), compliance_audits (1 record), conversations (12). Value unclear.
4. **server.py/v2 split** — Should be consolidated into one file.
5. **ThreadPoolExecutor bridge** — Wrapping async with sync via thread pool is a potential deadlock risk.

## For Metis

The encapsulated-call pattern is the correct design for AI agents. Key decisions:
- **Keep**: WorkflowEngine, encapsulated tools, state machine enforcement
- **Change**: Tool namespacing/grouping, dynamic loading based on task, single server codebase
- **Scale**: Consider gRPC or REST alongside MCP for non-Claude clients

---

**Version**: 1.0
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Location**: knowledge-vault/10-Projects/Project-Metis/claude-family-audit-mcp.md
