# Skills Validation Report

**Date**: 2026-03-29
**Scope**: 9 essential skills validated against current MCP tools (server_v2.py), schema, and deprecated patterns
**Method**: Cross-referenced all tool names in skill files against 76 registered `@mcp.tool()` functions in `server_v2.py`

## Validation Summary

| Skill | SKILL.md | reference.md | Issues Found | Severity |
|-------|----------|-------------|--------------|----------|
| messaging | PASS | PASS | 0 | - |
| session-management | WARN | WARN | 2 | Medium |
| project-ops | WARN | PASS | 1 | Low |
| work-item-routing | FAIL | PASS | 2 | Medium |
| agentic-orchestration | PASS | PASS | 0 | - |
| code-review | PASS | PASS | 0 | - |
| bpmn-modeling | WARN | WARN | 2 | Low |
| coding-intelligence | WARN | N/A | 1 | Low |
| sql-optimization | WARN | N/A | 1 | Low |

**Total issues**: 9
**Fixable via update_config()**: 7 (skill content changes)
**Not fixable** (correct as-is or cosmetic): 2

---

## Detailed Findings by Skill

### 1. messaging

**Files**: SKILL.md, reference.md, reference-sql.md, reference-patterns.md

- **Tool references**: All valid. `check_inbox`, `send_message`, `broadcast`, `reply_to`, `acknowledge`, `list_recipients`, `get_active_sessions` -- all exist in server_v2.py.
- **Schema references**: All SQL uses `claude.messages` -- correct.
- **Deprecated patterns**: None found.
- **Verdict**: PASS. Clean.

### 2. session-management

**Files**: SKILL.md, reference.md

- **Tool references**: SKILL.md does NOT mention the `start_session()` or `end_session()` MCP tools, which are the primary programmatic tools for session lifecycle. It only references slash commands (`/session-start`, `/session-end`). The reference.md mentions `remember()`, `acknowledge()`, `store_session_notes()`, `get_session_notes()` -- all valid.
- **Schema references**: All SQL uses `claude.sessions`, `claude.agent_sessions`, `claude.identities`, `claude.todos` -- all correct.
- **Deprecated patterns**: reference.md line 99 says `"/todo commands for persistent work (survives sessions)"` -- there is no `/todo` slash command. Persistent todos are managed via `claude.todos` table and MCP tools.
- **Issue 1** [MEDIUM]: SKILL.md missing `start_session()` and `end_session()` MCP tool references in the Quick Reference tools section. These are the main MCP tools for programmatic session management.
- **Issue 2** [LOW]: reference.md references `/todo` commands that do not exist.
- **Action**: Update via `update_config('skill', 'claude-family', 'session-management', ...)` to add MCP tools table and fix `/todo` reference.

### 3. project-ops

**Files**: SKILL.md, reference.md

- **Tool references**: SKILL.md references `/project-init`, `/retrofit-project`, `/phase-advance`, `/check-compliance` in a "Commands" table. These are skills, not commands. Commands directory only contains 4 session-related commands. However, skills are invocable via `/skill-name` syntax, so these references are functionally correct.
- **Schema references**: All SQL uses `claude.projects`, `claude.identities` -- correct.
- **Deprecated patterns**: None found.
- **Issue 1** [LOW]: Table header says "Commands" but they are skills. Should say "Skills" for clarity since the `.claude/commands/` directory does not contain these.
- **Action**: Update via `update_config()` to rename "Commands" section to "Skills (Slash Commands)".

### 4. work-item-routing

**Files**: SKILL.md, reference.md

- **Tool references**: `create_feedback`, `create_feature`, `create_linked_task`, `add_build_task`, `advance_status`, `promote_feedback` -- all valid in server_v2.py.
- **Schema references**: All SQL uses `claude.feedback`, `claude.features`, `claude.build_tasks`, `claude.column_registry` -- correct.
- **Deprecated patterns**: None found.
- **Issue 1** [MEDIUM]: SKILL.md feedback status list is `new, in_progress, resolved, wont_fix, duplicate` but is **missing `triaged`**. The `feedback` skill and the actual `WorkflowEngine` both include `triaged` as a valid status. The `promote_feedback()` tool transitions feedback to `triaged`.
- **Issue 2** [LOW]: "Commands" section lists `/feedback-create`, `/feedback-list`, `/feedback-check`. These are skills (invocable via `/feedback`), not standalone commands.
- **Action**: Update via `update_config()` to add `triaged` to status list and rename Commands to Skills.

### 5. agentic-orchestration

**Files**: SKILL.md, reference.md

- **Tool references**: Uses native `Task` tool (correct), `store_session_notes()`, `get_session_notes()`, `save_checkpoint()` -- all valid.
- **Schema references**: `claude.agent_sessions`, `claude.agent_definitions` -- correct.
- **Deprecated patterns**: None. Previously used `mcp__orchestrator__spawn_agent` but this skill has already been updated to use native `Task` tool.
- **Verdict**: PASS. Clean.

### 6. code-review

**Files**: SKILL.md, reference.md

- **Tool references**: Uses native `Task` tool with agent types (`reviewer-sonnet`, `security-sonnet`, `tester-haiku`) -- correct.
- **Schema references**: None (no SQL in this skill).
- **Deprecated patterns**: None found.
- **Verdict**: PASS. Clean.

### 7. bpmn-modeling

**Files**: SKILL.md, reference.md

- **Tool references**: `list_processes`, `get_process`, `get_subprocess`, `validate_process`, `get_current_step`, `get_dependency_tree`, `search_processes`, `check_alignment` -- all valid bpmn-engine MCP tools. Also references `create_feedback()` and `remember()` -- both valid.
- **Schema references**: None (uses BPMN engine, not raw SQL).
- **Deprecated patterns**: None found.
- **Issue 1** [LOW]: SKILL.md has `**Version**: 1.1` but no standard footer format (missing Created/Updated/Location).
- **Issue 2** [LOW]: reference.md has no version footer at all.
- **Action**: Update via `update_config()` to add standard version footers.

### 8. coding-intelligence

**Files**: SKILL.md only (no reference.md)

- **Tool references**: `find_symbol`, `check_collision`, `get_module_map`, `find_similar`, `get_dependency_graph`, `unstash` -- all valid in server_v2.py. Also references `populate_dossier()` which is a Python script (`scripts/dossier_auto_populate.py`), NOT an MCP tool.
- **Schema references**: None.
- **Deprecated patterns**: None.
- **Issue 1** [LOW]: `populate_dossier()` is shown as a direct Python import (`from scripts.dossier_auto_populate import populate_dossier`). This works when called from a script context but is not available as an MCP tool. Claude agents would need to invoke it via Bash. The skill should clarify this is a script call, not an MCP tool.
- **Action**: Update via `update_config()` to clarify `populate_dossier` invocation method.

### 9. sql-optimization

**Files**: SKILL.md only (no reference.md)

- **Tool references**: `mcp__postgres__explain_query`, `mcp__postgres__analyze_query_indexes` -- both valid. However, the example shows `analyze_query_indexes(sql="SELECT ...")` but the actual tool signature takes `queries: list[str]`, not `sql: str`.
- **Schema references**: None (generic SQL patterns, not project-specific).
- **Deprecated patterns**: None.
- **Issue 1** [LOW]: Example shows wrong parameter name. Should be `queries=["SELECT ..."]` not `sql="SELECT ..."`.
- **Action**: Update via `update_config()` to fix parameter name in example.

---

## Global Checks (All 9 Skills)

### Deprecated Pattern Scan

| Pattern | Found In | Status |
|---------|----------|--------|
| `store_knowledge` | None of the 9 skills | CLEAN |
| `recall_knowledge` | None of the 9 skills | CLEAN |
| `get_session_context` | None of the 9 skills | CLEAN |
| `orchestrator` tool | None of the 9 skills | CLEAN (previously fixed in winforms, testing, doc-keeper) |
| `.claude/commands/` | None of the 9 skills | CLEAN |
| `.claude-plugins/` | None of the 9 skills | CLEAN |
| `claude_family.*` schema | None of the 9 skills | CLEAN |
| `claude_pm.*` schema | None of the 9 skills | CLEAN |
| `TodoWrite` as primary | None of the 9 skills | CLEAN (session-management correctly distinguishes TodoWrite as ephemeral) |

### Previously Fixed (Outside Scope but Noted)

These skills outside the 9 essential were already fixed in prior audits:
- `winforms/SKILL.md` -- version note mentions orchestrator fix
- `testing/SKILL.md` -- version note mentions orchestrator fix
- `doc-keeper/SKILL.md` -- notes orchestrator retirement
- `database/SKILL.md` -- mentions `claude_family.*` as legacy warning (correct context)

---

## Recommended Fix Priority

| Priority | Issue | Skill | Fix Method |
|----------|-------|-------|------------|
| 1 | Missing `triaged` status | work-item-routing | `update_config()` |
| 2 | Missing `start_session`/`end_session` tools | session-management | `update_config()` |
| 3 | Wrong param name `sql` -> `queries` | sql-optimization | `update_config()` |
| 4 | Non-existent `/todo` commands | session-management/reference | `update_config()` |
| 5 | "Commands" -> "Skills" header | work-item-routing | `update_config()` |
| 6 | "Commands" -> "Skills" header | project-ops | `update_config()` |
| 7 | `populate_dossier` invocation clarity | coding-intelligence | `update_config()` |
| 8 | Missing version footers | bpmn-modeling | `update_config()` |

**Note**: All fixes require `update_config('skill', 'claude-family', '<skill-name>', '<content>', '<reason>')` because skills are DB-managed and direct file edits are blocked by the `standards_validator.py` hook.

---

**Version**: 1.0
**Created**: 2026-03-29
**Updated**: 2026-03-29
**Location**: docs/skills-validation-report.md
