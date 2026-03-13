---
projects:
- claude-family
- Project-Metis
tags:
- audit
- skills
- config
- logging
- vault
synced: false
---

# Audit: Operations (Skills, Config, Logging, Vault)

**Parent**: [[claude-family-systems-audit]]
**Raw data**: `docs/audit/skills_config_audit.md` (19K), `docs/audit/logging_audit.md` (17K)

---

## 1. Skills System (16 skills)

Markdown files in `.claude/skills/` providing domain instructions when invoked via the Skill tool.

| Skill | Status | Key Issue |
|-------|--------|-----------|
| agentic-orchestration | Healthy | Correctly documents native Task tool |
| bpmn-modeling | Healthy | Minor: calls `store_knowledge` (legacy) |
| code-review | Healthy | None |
| database | Healthy | Placeholder hook in frontmatter (no-op) |
| planner | Healthy | None |
| project-ops | Healthy | None |
| react-expert | Healthy | None |
| sql-optimization | Healthy | Verify MCP tools exist |
| wpf-ui | Healthy | Very large (52KB) |
| messaging | Healthy | One stale orchestrator example |
| **doc-keeper** | **Stale** | References orchestrator + filesystem MCP (both retired) |
| **feature-workflow** | **Stale** | `status='pending'` (should be `todo`); raw SQL bypasses WorkflowEngine |
| **session-management** | **Stale** | Frontmatter lists `mcp__orchestrator__check_inbox` |
| **testing** | **Stale** | Uses `mcp__orchestrator__spawn_agent` throughout |
| **winforms** | **Stale** | Ends with orchestrator spawn call |
| **work-item-routing** | **Stale** | Invalid status values; raw SQL bypasses WorkflowEngine |

**7 skills registered in settings.local.json**; 9 are on disk only (invoked ad hoc).

---

## 2. Slash Commands (24 commands)

### Severely Broken (6) — Use retired schemas/MCPs

| Command | Issue |
|---------|-------|
| `session-start.md` | Queries `claude_family.*`, `mcp__memory__*` tools — all retired |
| `session-end.md` | Same: `claude_family.*`, `nimbus_context.*`, `mcp__memory__*` |
| `feedback-check.md` | All SQL against `claude_pm.*` — retired |
| `feedback-create.md` | All SQL against `claude_pm.*` — retired |
| `feedback-list.md` | All SQL against `claude_pm.*` — retired |
| `knowledge-capture.md` | Pre-F130; doesn't mention `remember()` |

**Note**: These broken commands are NOT the same as the auto-hooks or Skill-invoked skills. The `/session-start` skill (via Skill tool) works correctly. These `.claude/commands/` files are legacy.

### Healthy (16)

session-resume, session-save, session-commit, session-status, maintenance, crash-recovery, sa-plan, sa-plan-template, todo, feedback, ideate, check-compliance, phase-advance, retrofit-project, self-test, plus several others not fully audited.

---

## 3. Config Management

**Architecture**: DB → `generate_project_settings.py` → `.claude/settings.local.json`

3-layer merge: `config_templates` (hooks-base) + `project_type_configs` (type defaults) + `workspaces.startup_config` (project overrides).

**Self-healing**: Regenerates on every SessionStart. Manual edits overwritten.

**Gaps Found**:
1. 3 plugin scripts in settings.local.json are undocumented in MEMORY.md
2. `ENABLE_TOOL_SEARCH: false` env var undocumented
3. Config Management SOP step 6 describes generating `hooks.json` (removed)
4. Two MCP list fields (`mcp_servers` vs `enabledMcpjsonServers`) not documented

---

## 4. Logging & Monitoring (7 systems)

| System | Storage | Status | Value |
|--------|---------|--------|-------|
| Session logging | `claude.sessions` | Working (52 orphaned) | **High** — core to all features |
| MCP usage | `claude.mcp_usage` | Working | **High** — shows tool adoption |
| Audit log | `claude.audit_log` | Working, limited scope | **Medium** — only WorkflowEngine transitions |
| Failure capture | JSONL + `claude.feedback` | Working | **High** — self-healing loop |
| Subagent logging | `claude.agent_sessions` | **Broken** | **Low** — empty IDs, no data captured |
| Task sync | `claude.todos` | Working | **High** — bridges memory to DB |
| hooks.log | File (~77K lines) | Working, no rotation | **Medium** — debug only |

### Critical Logging Issues

1. **Subagent logging broken** — `subagent_id` comes through empty from Claude Code. 100+ agent spawns in JSONL files but none in DB.
2. **52 session_end fallbacks never replayed** — `replay_fallback()` exists but nothing calls it.
3. **hooks.log no rotation** — 77K+ lines, growing unboundedly.
4. **No cross-project dashboard** — No aggregate health view.
5. **No RAG quality metrics** — Can't measure if injected context helps.
6. **Audit log too narrow** — Misses direct SQL, knowledge ops, config changes.

---

## 5. Vault Documentation Health

~290 files total. **43 contain deprecated references** to: orchestrator MCP, `claude_family.*` schema, retired MCPs (memory, filesystem, vault-rag).

**Most impactful stale docs**:
- `Family Rules.md` — Lists orchestrator as active MCP (Updated 2026-02-10, retired 2026-02-24)
- `Claude Tools Reference.md` — Lists 3 retired MCPs as active
- `Purpose.md` — Only mentions 3 of 37 projects
- `Orchestrator MCP.md` — Full doc for retired system, no retirement note
- `Session Lifecycle - Overview.md` — Says agent logging is "via orchestrator"
- Multiple SOPs reference orchestrator or retired schemas

---

## For Metis

**Skills**: Standardize skill format. Version skills. Auto-validate references on deployment.

**Config**: The self-healing pattern is excellent. Enterprise needs: config change audit trail, environment-specific overrides (dev/staging/prod), encrypted secrets management.

**Logging**: Need structured logging (JSON) to a proper aggregator. Add metrics, alerting, log rotation. The failure-capture-to-feedback loop is innovative — preserve it.

**Vault**: Implement freshness scoring (deprioritize stale docs in RAG). Auto-detect deprecated references. Version control with automated validation.

---

**Version**: 1.0
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Location**: knowledge-vault/10-Projects/Project-Metis/claude-family-audit-operations.md
