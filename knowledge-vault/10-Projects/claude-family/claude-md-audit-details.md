---
projects:
- claude-family
tags:
- audit
- claude-md
- governance
synced: false
---

# CLAUDE.md Audit — Per-Project Details

**Overview**: See [claude-md-audit.md](claude-md-audit.md)
**Audit Date**: 2026-03-13

---

## ATO-Infrastructure — Medium

**File**: `C:\Projects\ATO-Infrastructure\CLAUDE.md`

- No `project-tools` MCP reference. Only lists `azure` and `ms-learn`, omitting all Claude Family standard tools.
- No work tracking section — no guidance on feedback, features, or build_tasks.
- Footer date 2026-01-03 is over two months stale.
- No storage tool guidance (remember(), store_session_fact(), catalog()).
- Very thin file (62 lines) — missing all standard Claude Family sections.

---

## ATO-Tax-Agent — Medium

**File**: `C:\Projects\ATO-Tax-Agent\CLAUDE.md`

- Footer date 2025-12-26 is nearly three months stale.
- No project-tools MCP listed — work tracking section references `claude.*` tables but gives no tool guidance.
- References `python scripts/sync_obsidian_to_db.py` in the Knowledge Vault section — this script no longer exists (vault embedding pipeline replaced it).
- No storage tool guidance.
- Session start/end instructions say to run `/session-start` manually — current system auto-starts via hooks; minor but misleading.
- Database section notes "Use appropriate schema (not `claude` schema)" for app tables — correct, but phrasing could be misread as discouraging `claude.*` for work tracking.

---

## bee-game — Low

**File**: `C:\Projects\bee-game\CLAUDE.md`

- Footer missing the `Updated` field (only `Created: 2026-01-18`).
- No MCP servers section — no reference to project-tools or any Claude Family MCP.
- No storage tool guidance.
- Work tracking table is present but gives no tool guidance on which MCP tools to call.

---

## claude-family-manager-v2 — High

**File**: `C:\Projects\claude-family-manager-v2\CLAUDE.md`

- **Retired MCPs listed as active**: MCP Servers section lists `orchestrator` and `memory`. Both retired (orchestrator 2026-02-24, memory 2026-01).
- Footer missing `Location` field; Updated date 2025-12-27 is stale.
- No storage tool guidance.
- Configuration section instructs "message `claude-family` project via orchestrator" — orchestrator is retired; correct tool is `project-tools.send_message`.

---

## claude-manager-mui — High

**File**: `C:\Projects\claude-manager-mui\CLAUDE.md`

- **Retired MCPs listed as active**: MCP Servers section lists `orchestrator` and `memory`. Both retired.
- Footer date 2025-12-29 is stale; missing `Location` field.
- No storage tool guidance; no explicit project-tools reference.
- Structurally identical to claude-family-manager-v2's MCP section — both generated from the same stale template.

---

## finance-htmx — Low

**File**: `C:\Projects\finance-htmx\CLAUDE.md`

- Footer missing `Updated` field (only `Created: 2025-12-28`).
- No MCP servers section — no reference to project-tools or standard Claude Family tools.
- No storage tool guidance.
- `claude.column_registry` reference in Data Gateway section is correct.

---

## finance-mui — Low

**File**: `C:\Projects\finance-mui\CLAUDE.md`

- Footer missing `Updated` field (only `Created: 2025-12-28`).
- No MCP servers section — no project-tools reference.
- No storage tool guidance.
- `claude.column_registry` reference in Data Gateway section is correct.

---

## monash-nimbus-reports — High

**File**: `C:\Projects\monash-nimbus-reports\CLAUDE.md`

- **Retired MCP listed as active**: MCP Servers table lists `orchestrator`. Retired 2026-02-24.
- Configuration section says "message `claude-family` project via orchestrator" — should use `project-tools.send_message`.
- Footer date 2026-01-26 is over six weeks stale.
- No storage tool guidance.
- `nimbus-knowledge` MCP listed prominently with no deprecation note — MEMORY.md marks it "PENDING SHUTDOWN — 34 rows to migrate via remember(), then retire."

---

## nimbus-import — Low

**File**: `C:\Projects\nimbus-import\CLAUDE.md`

- Footer date 2025-12-27 is over two months stale.
- MCP Servers section only mentions the MUI MCP — no reference to project-tools or standard Claude Family tools.
- No storage tool guidance.
- Schema references (`claude.*`) and work tracking section are correct.

---

## nimbus-mui — High

**File**: `C:\Projects\nimbus-mui\CLAUDE.md`

- **Retired MCP listed as active**: Configuration section (line 121) lists `orchestrator`. Retired 2026-02-24.
- Configuration section says "message `claude-family` project via orchestrator" — should use `project-tools.send_message`.
- `nimbus-knowledge` MCP listed without deprecation note — pending shutdown per MEMORY.md.
- No storage tool guidance.
- Footer 2026-02-22 is the most current of all audited files but still predates the orchestrator retirement.
- `project-tools` is correctly listed in the MCP table; BPMN section is well-formed.

---

## nimbus-odata-configurator — High

**File**: `C:\Projects\nimbus-odata-configurator\CLAUDE.md`

- **Retired MCP listed as active**: MCP Servers table lists `orchestrator`. Retired 2026-02-24.
- Configuration section says "message `claude-family` project via orchestrator" — should use `project-tools.send_message`.
- Footer missing `Updated` field (only `Created: 2026-02-01`) — file has never been updated since creation, which is after orchestrator retirement planning but before the actual retirement.
- No storage tool guidance.
- `project-tools` is correctly listed in MCP table.

---

## nimbus-user-loader — Medium

**File**: `C:\Projects\nimbus-user-loader\CLAUDE.md`

- Footer is malformed: single inline line `Version: 3.0 | Updated: 2025-12-14` — missing `Created` and `Location` fields, non-standard format.
- References `Context7` MCP and `mcp__roslyn__ValidateFile` in the mandatory C# workflow. Neither appears in the global MCP index. If not installed, the mandatory workflow would silently fail with no actionable error.
- No project-tools reference for work tracking despite having the standard tracking table.
- No storage tool guidance.
- `claude.column_registry` reference is correct. Domain-specific content (Nimbus API rules) is valuable.

---

## personal-finance-system — High

**File**: `C:\Projects\personal-finance-system\CLAUDE.md`

- **Retired MCP in config defaults**: Lines 53-56 state that `csharp-desktop` project type defaults include `memory` as an MCP server. The memory MCP was removed 2026-01. The DB record `project_type_configs` for `csharp-desktop` needs to be corrected — the file accurately reflects the stale DB row.
- Footer date 2025-12-27 is nearly three months stale.
- No storage tool guidance; no project-tools MCP reference.
- SOP table uses relative paths (`../claude-family/knowledge-vault/...`) — only reliable from the project working directory.

---

## trading-intelligence — Low

**File**: `C:\Projects\trading-intelligence\CLAUDE.md`

- Footer date 2026-02-08 is over one month stale.
- No storage tool guidance; no MCP servers section.
- Work tracking section correctly names project-tools by tool name (`project-tools.create_feature`, etc.) — strongest tool guidance of any non-infrastructure audited file.
- Uses its own `trading_intelligence` PostgreSQL DB for app data correctly, distinct from `claude.*` for work tracking.

---

## mcp-search-test — Low

**File**: `C:\Projects\mcp-search-test\CLAUDE.md`

- No `Updated`, `Version` footer fields.
- No Claude Family integration sections (expected — ephemeral test project).
- No action required.

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: C:\Projects\claude-family\knowledge-vault\10-Projects\claude-family\claude-md-audit-details.md
