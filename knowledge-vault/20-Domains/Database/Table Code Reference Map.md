---
projects:
- claude-family
tags:
- schema
- cleanup
- reference
synced: false
---

# Table-to-Code Reference Map

Pre-Metis cleanup reference. Maps all `claude.*` tables to code and disposition.

**Generated**: 2026-02-28 (post-ANALYZE) | **Rollback tag**: `pre-metis-cleanup`

## Summary: 101 → 58 tables (43 DROP)

| Category | Count | Action |
|----------|-------|--------|
| Active (data + code) | 32 | KEEP |
| Active infrastructure | 18 | KEEP |
| Versioning system | 8 | KEEP (activate) |
| Superseded systems | 13 | DROP |
| Orchestrator (retired) | 4 | DROP |
| Never-built frameworks | 26 | DROP |

---

## DROP - Superseded (13)

| Table | Rows | Superseded By | Archive |
|-------|------|---------------|---------|
| `process_registry` | 32 | bpmn-engine (ADR-005) | process_router.py |
| `process_runs` | 782 | bpmn-engine | process_router.py |
| `process_steps` | 163 | bpmn-engine | process_router.py |
| `process_triggers` | 67 | bpmn-engine | process_router.py |
| `process_dependencies` | 19 | bpmn-engine | process_router.py |
| `process_classification_log` | 788 | bpmn-engine | process_router.py |
| `mcp_configs` | 26 | .mcp.json files | generate_mcp_config.py |
| `feedback_comments` | 20 | Never used | None |
| `feedback_screenshots` | 14 | Never used | None |
| `git_workflow_deployments` | 24 | Plugin system | deploy_git_workflow.py |
| `global_config` | 1 | config_templates | monitor_anthropic_docs.py |
| `global_config_versions` | 0 | FK to global_config | None |
| `architecture_decisions` | 3 | docs/adr/ files | None |

## DROP - Orchestrator Retired 2026-02-24 (4)

| Table | Rows | Archive |
|-------|------|---------|
| `agent_commands` | 1 | mcp-servers/orchestrator/ |
| `agent_status` | 41 | mcp-servers/orchestrator/ |
| `agent_definitions` | 19 | generate_agent_files.py |
| `async_tasks` | 63 | mcp-servers/orchestrator/ |

## DROP - Never-Built Frameworks (26)

| Table | Rows | Framework |
|-------|------|-----------|
| `config_test_configs` | 11 | Config testing |
| `config_test_runs` | 49 | Config testing |
| `config_test_scores` | 10 | Config testing |
| `config_test_tasks` | 7 | Config testing |
| `phases` | 7 | PM system |
| `pm_tasks` | 11 | PM system |
| `programs` | 4 | PM system |
| `work_tasks` | 5 | PM system |
| `ideas` | 1 | feedback.type='idea' used |
| `components` | 110 | Extended work tracking |
| `requirements` | 109 | Extended work tracking |
| `reminders` | 1 | Notification system |
| `budget_alerts` | 3 | Notification system |
| `models` | 3 | Model registry |
| `doc_templates` | 6 | Doc management |
| `project_docs` | 1 | Doc management |
| `reviewer_specs` | 4 | Auto-reviewer |
| `test_runs` | 2 | Test tracking |
| `procedure_registry` | 18 | SOP registry (vault used) |
| `procedures` | 25 | SOP registry (vault used) |
| `app_logs` | 2 | File logging used |
| `tool_evaluations` | 1 | Tool eval |
| `shared_commands` | 321 | Command sharing |
| `project_command_assignments` | 0 | Command sharing |
| `project_config_assignments` | 8 | Config assignments |
| `actions` | 6 | MCW actions |

Post-ANALYZE: most "empty" tables have historical data. No active code refs (verified via grep).

## FK Drop Order

**Children first**: config_test_scores → config_test_runs → config_test_configs/tasks. project_command_assignments → shared_commands. global_config_versions → global_config. process_deps/runs/steps/triggers → process_registry.

**FK to KEEP tables** (safe): feedback_comments/screenshots → feedback. components/requirements → features. architecture_decisions/ideas/phases/project_docs → projects. agent_commands/status → sessions.

**Standalone**: pm_tasks, programs, work_tasks, reminders, budget_alerts, models, doc_templates, reviewer_specs, procedure_registry, procedures, app_logs, tool_evaluations, mcp_configs, git_workflow_deployments, actions, agent_definitions.

See [[Table Code Reference Map - KEEP]] for the 58 retained tables.

---

**Version**: 1.0
**Created**: 2026-02-28
**Updated**: 2026-02-28
**Location**: knowledge-vault/20-Domains/Table Code Reference Map.md
