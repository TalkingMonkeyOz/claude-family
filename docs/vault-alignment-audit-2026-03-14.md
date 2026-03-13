---
title: Vault Alignment Audit
date: 2026-03-14
auditor: analyst-sonnet
---

# Vault Alignment Audit — 2026-03-14

Verified key claims in the most impactful documentation against actual file system state and CLAUDE.md/MEMORY.md as source of truth.

---

## Summary Table

| Doc Path | Status | Issue |
|----------|--------|-------|
| `ARCHITECTURE.md` | INCORRECT | Table count says 36 (2025-12-04); actual is 63 (2026-03-13). Orchestrator listed as active MCP — retired 2026-02-24. Directory structure lists `.claude/hooks.json` which does not exist; hooks are in `settings.local.json`. `docs/TODO_NEXT_SESSION.md` listed as related doc — likely stale. Version/date footer says 2026-02-10 but content is circa 2025-12-04. |
| `knowledge-vault/Claude Family/mcp-and-tools/MCP Registry.md` | STALE | Lists `orchestrator` as an Active Global MCP. Orchestrator retired 2026-02-24. Updated date 2026-02-20 but not updated for retirement. Also missing: `bpmn-engine` MCP. |
| `knowledge-vault/Claude Family/mcp-and-tools/Orchestrator MCP.md` | CURRENT | Correctly shows RETIRED notice at top with replacement instructions. Preserved as historical reference — acceptable. |
| `knowledge-vault/40-Procedures/New Project SOP.md` | CURRENT | Accurate. Orchestrator note present. Script `generate_project_settings.py` exists. Version footer 2026-03-09. |
| `knowledge-vault/40-Procedures/config-management/Config Management SOP.md` | CURRENT | Accurate for DB-driven config. Last updated 2026-01-02 — may predate v3 tools (`update_claude_md`, `deploy_claude_md`, `regenerate_settings`) but core architecture is correct. |
| `knowledge-vault/40-Procedures/session-lifecycle/Session Lifecycle - Overview.md` | STALE | Content (hook chain, WCC, task_discipline_hook, cognitive memory, workfiles) not reflected. Last updated 2026-01-08. Flow diagram still shows "orchestrator" implied via "Agent spawns tracked". No PreCompact step shown in lifecycle diagram. |
| `knowledge-vault/30-Patterns/auto-apply-instructions.md` | CURRENT | Hook script `scripts/instruction_matcher.py` exists. Pattern is accurate. Footer date 2025-12-26, but this is a stable low-churn pattern — acceptable. Missing `markdown.instructions.md` from the table (present in CLAUDE.md). |
| `knowledge-vault/30-Patterns/post-compaction-claude-md-refresh.md` | STALE | Hook file `.claude/hooks/refresh_claude_md_after_compact.py` exists. But this approach may be superseded: PreCompact hook now injects session state, and CLAUDE.md is re-injected via `SessionStart` with matcher `compact`. The doc describes an older implementation location and may conflict with current hook architecture. Footer: 2025-12-26. |
| `knowledge-vault/30-Patterns/Database-Driven Design System.md` | CURRENT | `scripts/generate_standards.py` exists. References `claude.coding_standards` table — valid per schema. Last updated 2026-01-11. |
| `knowledge-vault/30-Patterns/Interlinked Documentation Pattern.md` | CURRENT | References `features.plan_data` — valid. No external scripts to verify. Last updated 2026-01-17. |
| `knowledge-vault/30-Patterns/Credential Management Pattern.md` | CURRENT | `scripts/config.py` exists. BPMN `credential_loading.bpmn` exists. Last updated 2026-02-26. |
| `knowledge-vault/30-Patterns/comparison-module-pattern.md` | CURRENT | Nimbus-specific TypeScript pattern. No infrastructure claims to verify. Last updated 2026-01-07. |
| `knowledge-vault/Claude Family/sessions-and-config/Session Architecture.md` | STALE | Hook chain table matches current state well (includes WCC in UserPromptSubmit row). However last updated date is unknown and the "Session vs Agent Session" table mentions "Automatic via orchestrator" for agent logging — orchestrator is retired. |
| `knowledge-vault/Claude Family/architecture/System Architecture.md` | STALE | References `session_startup_hook.py` (old name); current script is `session_startup_hook_enhanced.py`. Likely predates 2026 changes. |

---

## Missing SOPs (Referenced but Path Wrong)

CLAUDE.md (project) links to these paths, but they live in subdirectories:

| CLAUDE.md Reference | Actual Path |
|--------------------|-------------|
| `knowledge-vault/40-Procedures/Config Management SOP.md` | `knowledge-vault/40-Procedures/config-management/Config Management SOP.md` |
| `knowledge-vault/40-Procedures/Session Lifecycle - Overview.md` | `knowledge-vault/40-Procedures/session-lifecycle/Session Lifecycle - Overview.md` |
| `knowledge-vault/40-Procedures/New Project SOP.md` | `knowledge-vault/40-Procedures/New Project SOP.md` (correct — at root level) |
| `knowledge-vault/40-Procedures/Add MCP Server SOP.md` | `knowledge-vault/40-Procedures/infrastructure/Add MCP Server SOP.md` |

The CLAUDE.md "Standard Operating Procedures" section links to flat paths that don't match the actual subdirectory structure.

---

## Prioritized Fix List

### P1 — High Impact, Actively Misleading

1. **`ARCHITECTURE.md`** — Almost entirely outdated (Dec 2025 state). States 36 tables (actual: 63), lists orchestrator as active, references non-existent `hooks.json`, describes integration points as "planned" that are now implemented. This is the primary architecture reference and should reflect the current state with 63 tables, ~70 tools, 11 hooks, no orchestrator, bpmn-engine MCP.

2. **`Claude Family/mcp-and-tools/MCP Registry.md`** — Lists orchestrator as an active global MCP with ~9k token cost. Anyone following this will try to configure a retired server. Needs: remove orchestrator from Active, add `bpmn-engine` to Active.

3. **`CLAUDE.md` SOP paths** — The three SOP links in the "Standard Operating Procedures" section point to wrong paths (missing subdirectory). Should be updated to the actual subdirectory paths, or the vault files should be moved.

### P2 — Stale but Low Harm

4. **`Session Lifecycle - Overview.md`** (last updated 2026-01-08) — Missing: WCC (Work Context Container), task_discipline_hook, PreCompact step in lifecycle diagram, cognitive memory tier system, workfiles integration. Session flow diagram is incomplete. The detail docs in the `session-lifecycle/` subfolder may be more current — should be checked separately.

5. **`post-compaction-claude-md-refresh.md`** — Describes a hook mechanism that may now overlap with or be superseded by the PreCompact hook + MEMORY.md-injected context. The script file still exists but the pattern doc should clarify current vs. legacy behavior.

6. **`Claude Family/architecture/System Architecture.md`** — References `session_startup_hook.py` (old filename). Current script is `session_startup_hook_enhanced.py`.

### P3 — Acceptable Staleness (Stable Patterns)

7. **`auto-apply-instructions.md`** (2025-12-26) — Missing `markdown.instructions.md` from the instructions table (9 files in CLAUDE.md vs 8 listed here). Low risk.

8. **`comparison-module-pattern.md`** (2026-01-07) — Nimbus project pattern, not infrastructure. No staleness risk.

---

## What Was Not Checked

- `knowledge-vault/20-Domains/` — domain knowledge docs (APIs, DB) not audited
- `knowledge-vault/10-Projects/` — project-specific docs not audited
- Individual session handoff docs — temporal, expected to be stale
- `Claude Family/` sub-docs beyond the ones read above (27 files total in that folder)
- `knowledge-vault/40-Procedures/session-lifecycle/` detail docs (4 files)

---

**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: docs/vault-alignment-audit-2026-03-14.md
