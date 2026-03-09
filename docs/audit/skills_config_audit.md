I now have a comprehensive picture of the entire system. Let me compile the full structured report.

---

# Claude Family System Audit Report

## 1. Skills Inventory

### Summary

16 skills found in `/C:/Projects/claude-family/.claude/skills/`. The `settings.local.json` `skills` array lists 7 of them (database-operations, work-item-routing, session-management, code-review, project-ops, messaging, agentic-orchestration). The remaining 9 (bpmn-modeling, doc-keeper, feature-workflow, planner, react-expert, sql-optimization, testing, winforms, wpf-ui) are present on disk but not registered in the active skills list.

### Skills Table with Health Status

| Skill Directory | Status | Last Updated | Issues |
|---|---|---|---|
| agentic-orchestration | Healthy | 2026-02-28 | None. Correctly documents native Task tool, notes orchestrator retired. |
| bpmn-modeling | Healthy | 2026-02-20 | Calls `store_knowledge` (legacy) in one gotcha note; minor. Missing version footer date. |
| code-review | Healthy | 2026-02-08 | None. Uses native Task agents throughout. |
| database | Healthy | 2026-01-08 | Has a placeholder hook command in frontmatter (`python -c "import sys; print('{}')"`) that does nothing. |
| doc-keeper | Stale | Unknown | References `mcp-servers/orchestrator/agent_specs.json` (orchestrator retired 2026-02-24). References `mcp__filesystem__*` (filesystem MCP removed Jan 2026). No version footer. |
| feature-workflow | Stale | 2026-01-08 | Uses raw SQL `INSERT` with `status='pending'` for build_tasks, but the valid value is `todo` not `pending` (MEMORY.md gotcha). Bypasses WorkflowEngine. References `feedback_type='idea'` but column_registry only allows `bug, design, question, change`. |
| messaging | Healthy | 2026-02-28 | Contains one legacy code block showing `mcp__orchestrator__spawn_agent_async` inside an example comment block (line 283) — it's in an example of async pattern, but the surrounding text does not update it to the native Task tool equivalent, leaving a broken example. |
| planner | Healthy | 2026-01-24 | None. Uses native tools correctly. |
| project-ops | Healthy | 2026-01-08 | None. |
| react-expert | Healthy | 2026-01-24 | None. |
| session-management | Stale | 2025-12-27 | Frontmatter lists `mcp__orchestrator__check_inbox` as allowed tool (orchestrator retired). Updated date (2025-12-27) very old. Describes `update memory graph` at session end — memory MCP was removed Jan 2026. |
| sql-optimization | Healthy | 2026-01-24 | References `mcp__postgres__explain_query` and `mcp__postgres__analyze_query_indexes` in frontmatter — these may not be available tools on the postgres MCP server; verify. |
| testing | Stale | 2026-01-10 | Frontmatter lists `mcp__orchestrator__spawn_agent` as allowed tool. Two `mcp__orchestrator__spawn_agent()` calls in the body with no note that this is retired. Should use native Task tool. |
| winforms | Stale | Unknown | Last line uses `mcp__orchestrator__spawn_agent(...)`. No version footer. |
| work-item-routing | Stale | 2026-01-08 | Uses raw SQL bypassing WorkflowEngine. Lists `feedback_type='idea'` which is not a valid value per column_registry (valid: bug, design, question, change). Same issue as feature-workflow. |
| wpf-ui | Healthy | Unknown | Very large file (52KB+). No version footer visible in preview. |

### Deprecated Tool References in Skills

The following files contain `mcp__orchestrator` references that should be replaced with native `Task` tool calls:

- `/C:/Projects/claude-family/.claude/skills/session-management/skill.md` — frontmatter `allowed-tools` line 8
- `/C:/Projects/claude-family/.claude/skills/testing/skill.md` — frontmatter line 10, body lines 32 and 39
- `/C:/Projects/claude-family/.claude/skills/winforms/skill.md` — body line 113
- `/C:/Projects/claude-family/.claude/skills/messaging/skill.md` — body line 283 (inside async example)

### Skills Not in settings.local.json

These skills exist in `.claude/skills/` but are NOT in the `skills` array in `settings.local.json`: bpmn-modeling, doc-keeper, feature-workflow, planner, react-expert, sql-optimization, testing, winforms, wpf-ui.

This is partially by design (skills are invoked ad hoc) but the CLAUDE.md skill registry table lists `bpmn-modeling` as a core skill while it is absent from the active skills list.

---

## 2. Config Management Assessment

### Architecture

The config system works as described: `generate_project_settings.py` reads from `claude.config_templates` (hooks-base), `claude.project_type_configs` (type defaults), and `claude.workspaces.startup_config` (project overrides), deep-merges in that order, and writes everything into `.claude/settings.local.json`. Permissions from the existing file are preserved.

### Is Self-Healing Working?

The self-healing mechanism is correctly implemented. The `session_startup_hook_enhanced.py` fires on `SessionStart` and calls `generate_project_settings.py`. The current `settings.local.json` is well-formed and contains all hook types (SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PostToolUse, PreCompact, SubagentStart), MCP configs, permissions, and launch preferences.

### Config Flow Gaps Found

**Gap 1 — Plugin scripts referenced in PreToolUse hooks.**
Lines 100-115 of `settings.local.json` reference three scripts in `.claude-plugins/claude-family-core/scripts/`:
- `validate_db_write.py`
- `validate_phase.py`
- `validate_parent_links.py`

These appear to be project-type enforcement hooks. They are not listed in the MEMORY.md hook inventory. Whether this directory and these scripts exist is worth verifying.

**Gap 2 — `ENABLE_TOOL_SEARCH: false` in env.**
The settings file has `"env": {"ENABLE_TOOL_SEARCH": "false"}` but no documentation in CLAUDE.md or the Config Management SOP explains what this flag does or when it was added.

**Gap 3 — Config Management SOP is slightly stale.**
The SOP (version 3.2, updated 2026-02-11) describes generating both `.claude/hooks.json` (hooks only) and `.claude/settings.local.json` in step 6. The actual `generate_project_settings.py` code explicitly states `hooks.json` is NOT used and deletes it if found (line 513-516). This is a minor documentation drift.

**Gap 4 — mcp_servers array vs enabledMcpjsonServers.**
The `settings.local.json` has both `"mcp_servers": ["postgres", "project-tools", "sequential-thinking"]` and `"enabledMcpjsonServers": ["postgres", "project-tools", "sequential-thinking", "mui", "playwright", "bpmn-engine"]`. The Config Management SOP does not document this two-field pattern or the distinction between them.

---

## 3. Vault Documentation Health

### Family Rules (`knowledge-vault/40-Procedures/Family Rules.md`)

**Version**: 1.4, Updated 2026-02-10.

**Stale content:**
- MCP server table still lists `orchestrator` as active (`✅ Code`) but orchestrator was retired 2026-02-24, after this document was last updated.
- The `synced_at` frontmatter shows `2025-12-20` — this document has never been re-synced to the DB embeddings since creation.
- References `Deprecated MCPs (Jan 2026)` — mentions memory and vault-rag but not orchestrator.

### Session Lifecycle - Overview (`knowledge-vault/40-Procedures/Session Lifecycle - Overview.md`)

**Version**: 2.1, Updated 2026-01-08.

**Stale content:**
- Agent Session table says "Automatic via orchestrator" for logging — orchestrator is retired.
- The `synced: false` frontmatter means this document has never been synced.
- The linked detail documents (`Session Lifecycle - Session Start`, `Session Lifecycle - Session End`, `Session Lifecycle - Reference`) are referenced by wiki-link but their existence was not verified in this audit.

### Config Management SOP (`knowledge-vault/40-Procedures/Config Management SOP.md`)

**Version**: 3.2, Updated 2026-02-11. Mostly current.

**Minor stale content:**
- Step 6 of the SessionStart Flow section describes writing `.claude/hooks.json` (hooks only) — the script no longer does this; it was deprecated. This single line contradicts the actual implementation.
- `updated: 2026-01-02` in YAML frontmatter but Version footer says `2026-02-11` — frontmatter and footer are out of sync.

### Structured Autonomy Workflow (`knowledge-vault/30-Patterns/Structured Autonomy Workflow.md`)

**Version**: 1.0, Updated 2026-01-10.

**Stale content:**
- Phase table references `spawn_agent(coder-haiku/sonnet)` without specifying this is now via the native `Task` tool, not the orchestrator MCP.
- "Workflow Commands (Optional)" table mentions `/sa-plan`, `/sa-generate`, `/sa-implement` — `/sa-plan` and `/sa-plan-template` exist as commands; `/sa-generate` and `/sa-implement` were not found in the commands directory (only sa-plan and sa-plan-template are present).
- Related Documents section links `[[Orchestrator MCP]]` — this document refers to a retired system.

### Agent Selection Decision Tree (`knowledge-vault/30-Patterns/Agent Selection Decision Tree.md`)

**Version**: 1.1, Updated 2026-01-10.

**Stale content:**
- Related Documents section links `[[Orchestrator MCP]]` — retired.
- The table mentions `doc-keeper-haiku` as an agent type. The agent file exists at `.claude/agents/doc-keeper-haiku.md`, so this is valid.
- `researcher-opus` agent is referenced — agent file exists at `.claude/agents/researcher-opus.md`. Valid.
- No references to the cognitive memory system (F130, added 2026-02-26) in the decision tree, which may be intentional as it is not an agent selection concern.

---

## 4. Instructions System Assessment

### File Count and Pattern Coverage

9 instruction files at `/C:/Users/johnd/.claude/instructions/`:

| File | `applyTo` Pattern | Assessment |
|---|---|---|
| `csharp.instructions.md` | `**/*.cs` | Current. C# 12+, .NET 8+, modern patterns. |
| `markdown.instructions.md` | `**/*.md` | Current. Reflects documentation standards. |
| `sql-postgres.instructions.md` | `**/*.sql` | Current. Includes Data Gateway pattern and claude.* schema. |
| `winforms.instructions.md` | `**/Forms/**/*.cs`, `**/*.Designer.cs` | Not read in this audit but present. |
| `winforms-dark-theme.instructions.md` | `**/*Form.cs`, `**/*Control.cs` | Not read in this audit but present. |
| `wpf-ui.instructions.md` | `**/*.xaml`, `**/ViewModels/**/*.cs` | Not read in this audit but present. |
| `mvvm.instructions.md` | `**/ViewModels/**/*.cs`, `**/Views/**/*.xaml` | Not read in this audit but present. |
| `a11y.instructions.md` | `**/*.cs`, `**/*.tsx` | Not read in this audit but present. |
| `playwright.instructions.md` | `**/*.spec.ts`, `**/tests/**/*.ts` | Not read in this audit but present. |

**Issue found**: The `markdown.instructions.md` instruction file has `"Keep it short" - Target 250-500 tokens` as its first core principle, but the global CLAUDE.md `standards/core/markdown-documentation.md` (which overrides it via `@` include) now states the first principle is `"Chunk, don't summarize"` with explicit warning against summarizing. These two files are divergent — the global standard was updated to a newer philosophy but the instructions file was not updated to match.

The `settings.local.json` only lists `sql-postgres.instructions.md` in its `instructions` array. This means the project-level settings only auto-inject one instruction file. The others rely on global Claude Code settings matching file patterns.

---

## 5. Slash Commands Inventory

24 command files found. Assessment:

### Severely Stale (legacy schema / retired MCP)

| Command | Problem |
|---|---|
| `session-end.md` | Queries `claude_family.session_history`, `claude_family.universal_knowledge`, `nimbus_context.patterns`. Uses `mcp__memory__*` tools. Completely wrong — all three schemas/tools retired. |
| `session-start.md` | Same issues as session-end: `claude_family.session_history`, `claude_family.universal_knowledge`, `claude_pm.project_feedback`, `mcp__memory__search_nodes`. Also references `C:/claude/shared/scripts/` path that likely does not exist. Completely wrong. |
| `feedback-check.md` | All SQL queries against `claude_pm.project_feedback`, `claude_pm.project_feedback_comments`, `claude_pm.projects`. Schema is retired. Also hardcodes stale project UUIDs. |
| `feedback-create.md` | All SQL against `claude_pm.project_feedback`, `claude_pm.project_feedback_comments`, `claude_pm.projects`. Schema retired. |
| `feedback-list.md` | All SQL against `claude_pm.*`. Schema retired. |
| `knowledge-capture.md` | References `python scripts/sync_obsidian_to_db.py` (script likely exists but pattern superseded by `remember()` cognitive memory tools). Also lists hardcoded project names (nimbus-import, ato-tax-agent, mission-control-web) as domain examples. Version 1.0 from 2026-01-08 — never updated for cognitive memory. |

### Partially Stale

| Command | Problem |
|---|---|
| `project-init.md` | Uses `claude.projects` (correct schema) but calls `scan_documents.py` and references `claude.v_project_governance` — view existence unverified. Also uses `claude.document_projects` table which is not in the known 58-table schema. |
| `review-docs.md` | References `reviewer_doc_staleness.py` and `claude.reviewer_runs` table — not in known schema. May be from pre-cleanup era. |

### Current and Healthy

| Command | Notes |
|---|---|
| `session-resume.md` | Version 6.0, 2026-02-24. Correctly uses `mcp__project-tools__start_session`. Display-only pattern. |
| `session-save.md` | Version 1.0, 2026-02-14. Uses `store_session_notes`, `store_session_fact`, `store_knowledge`. Current. |
| `session-commit.md` | Not read but present. Likely current given proximity to session-save. |
| `session-status.md` | Not read but listed. |
| `maintenance.md` | Version 2.0, 2026-02-28. Calls `mcp__project-tools__system_maintenance`. Current. |
| `crash-recovery.md` | Version 2.0, 2026-02-21. Calls `mcp__project-tools__recover_session`. Current. |
| `sa-plan.md` | Version 2.0, 2026-02-28. Uses native Task tool. Current. |
| `sa-plan-template.md` | Present. Not read but likely supporting sa-plan. |
| `todo.md` | Present. |
| `feedback.md` | Present (separate from feedback-check/create/list). |
| `ideate.md` | Present. |
| `check-compliance.md` | Present. |
| `phase-advance.md` | Present. |
| `retrofit-project.md` | Present. |
| `self-test.md` | Present. |

---

## 6. Gaps and Issues Summary

### Critical Issues (will cause errors if used)

1. **session-start.md and session-end.md are completely broken.** They reference `claude_family.*` schema (dropped Dec 2025), `mcp__memory__*` tools (removed Jan 2026), and `C:/claude/shared/scripts/` paths. Any Claude invoking these commands will fail every SQL statement and every MCP call. These commands are the entry point for every session.

2. **feedback-check.md, feedback-create.md, feedback-list.md use retired schema.** All three query `claude_pm.*` (retired). The feedback workflow these commands implement is fundamentally broken.

3. **testing skill uses `mcp__orchestrator__spawn_agent`.** Any Claude invoking the testing skill and following the primary "Recommended: Spawn Tester Agent" pattern will call a retired MCP and get an error.

4. **feature-workflow skill uses invalid `feedback_type='idea'`.** The column_registry valid values for `feedback.feedback_type` are `bug, design, question, change` — `idea` is not valid. Any Claude using the skill's quick reference table will get a constraint violation.

5. **feature-workflow and work-item-routing skills use `status='pending'` for build_tasks.** The valid status value is `todo` (per MEMORY.md gotcha). These skills instruct raw SQL with invalid values.

### High Priority Issues (outdated information, will mislead)

6. **Family Rules still lists orchestrator as active MCP.** Any Claude reading this document to understand available tools gets wrong information.

7. **session-management skill frontmatter lists `mcp__orchestrator__check_inbox`.** This propagates to agents inheriting from this skill.

8. **winforms skill ends with `mcp__orchestrator__spawn_agent` as the spawn pattern.** No native Task tool alternative is shown.

9. **Agent Selection Decision Tree links `[[Orchestrator MCP]]` as related reading.** Points to a retired system.

10. **Structured Autonomy Workflow references `/sa-generate` and `/sa-implement` commands** that do not exist in the commands directory.

11. **messaging skill async agent example uses `mcp__orchestrator__spawn_agent_async`.** The correct pattern (native Task with `run_in_background=true`) is documented in the agentic-orchestration skill but not here.

12. **doc-keeper skill references `mcp-servers/orchestrator/agent_specs.json` and `mcp__filesystem__*`.** Both retired.

### Medium Priority Issues (minor staleness, documentation drift)

13. **markdown.instructions.md first principle ("Keep it short") diverges from global standard ("Chunk, don't summarize").** The global standard has been updated to a more nuanced philosophy; the instruction file has not followed.

14. **Config Management SOP step 6 still describes generating `hooks.json`** which the actual script explicitly removes.

15. **Session Lifecycle Overview says agent sessions are "Automatic via orchestrator"** — retired.

16. **knowledge-capture.md does not mention `remember()` cognitive memory tools** (introduced 2026-02-26). Still documents the older manual vault + SQL pattern.

17. **bpmn-modeling skill calls `store_knowledge()` (legacy)** in one section — should reference `remember()`.

18. **database skill placeholder hook** in frontmatter is a no-op; either implement it or remove it.

19. **settings.local.json has two MCP lists** (`mcp_servers` and `enabledMcpjsonServers`) with differing contents — not documented in Config Management SOP.

20. **Three `.claude-plugins/claude-family-core/scripts/` hooks** in settings.local.json are undocumented in MEMORY.md hook inventory.

---

## Relevant File Paths

**Skills directory**: `C:/Projects/claude-family/.claude/skills/`

**Critical stale command files**:
- `C:/Projects/claude-family/.claude/commands/session-start.md`
- `C:/Projects/claude-family/.claude/commands/session-end.md`
- `C:/Projects/claude-family/.claude/commands/feedback-check.md`
- `C:/Projects/claude-family/.claude/commands/feedback-create.md`
- `C:/Projects/claude-family/.claude/commands/feedback-list.md`

**Stale skills**:
- `C:/Projects/claude-family/.claude/skills/session-management/skill.md`
- `C:/Projects/claude-family/.claude/skills/testing/skill.md`
- `C:/Projects/claude-family/.claude/skills/winforms/skill.md`
- `C:/Projects/claude-family/.claude/skills/messaging/skill.md`
- `C:/Projects/claude-family/.claude/skills/feature-workflow/skill.md`
- `C:/Projects/claude-family/.claude/skills/work-item-routing/skill.md`
- `C:/Projects/claude-family/.claude/skills/doc-keeper/skill.md`

**Stale vault docs**:
- `C:/Projects/claude-family/knowledge-vault/40-Procedures/Family Rules.md`
- `C:/Projects/claude-family/knowledge-vault/40-Procedures/Session Lifecycle - Overview.md`
- `C:/Projects/claude-family/knowledge-vault/30-Patterns/Structured Autonomy Workflow.md`
- `C:/Projects/claude-family/knowledge-vault/30-Patterns/Agent Selection Decision Tree.md`

**Config files**:
- `C:/Projects/claude-family/.claude/settings.local.json`
- `C:/Projects/claude-family/scripts/generate_project_settings.py`

**Instructions**:
- `C:/Users/johnd/.claude/instructions/markdown.instructions.md`