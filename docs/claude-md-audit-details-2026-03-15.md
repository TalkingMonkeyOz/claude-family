# CLAUDE.md Audit — Section Details — 2026-03-15

Companion to [claude-md-audit-2026-03-15.md](claude-md-audit-2026-03-15.md)

---

## Global `~/.claude/CLAUDE.md` — Section Analysis (281 lines)

### Sections to KEEP

| Section | Lines | Why |
|---------|-------|-----|
| Header + Identity (L1–16) | 16 | Sets scope and persona |
| Environment (L19–29) | 11 | Windows path rules needed everywhere |
| Knowledge Vault overview (L32–48) | 17 | Vault path + key doc pointers |
| Database Connection (L51–54) | 4 | One-line critical rule |
| Work Tracking table (L57–70) | 14 | Hierarchy + git codes — small, high value |
| Session Workflow (L119–127) | 9 | Auto-behavior summary |
| Code Style (L248–254) | 7 | Universal standards |
| SOPs table (L233–244) | 12 | Keep 4-row table; remove "Key Principle" footer |
| Footer (L277–280) | 4 | Required by standards |

### Sections to TRIM

**MCP Tool Index — Storage Tools table (L80–92, 13 lines)**
Fully covered by `.claude/rules/storage-rules.md` which is always loaded. Replace with: "Storage guidance is in `.claude/rules/storage-rules.md` (always loaded)."

**MCP Tool Index — Full Tool Index table (L94–113, 20 lines)**
Trim to 6-7 most universally needed rows: `start_work`, `complete_work`, `remember`, `recall_memories`, `stash`, `catalog`, `check_inbox`. Remove "Legacy tools" footnote — belongs in storage-rules.md.

**Skills section (L130–144, 15 lines)**
Skills are DB-backed (`claude.skills`) and auto-loaded per project scope. Condense to: "Skills are DB-backed (`claude.skills`, scopes: global/project/command/agent). Use the `Skill` tool when a task matches a skill's purpose." Remove the 8-row table.

**Delegation Rules (L147–162, 16 lines)**
The model-name table belongs in the Agent Selection Decision Tree vault doc it already cites. Keep: the principle ("premium models for thinking, cheap models for doing") + pointer. Remove the 7-row table.

**Structured Autonomy (L165–177, 13 lines)**
Condense to 3 lines: trigger condition, 4-step summary on one line, skip conditions, vault pointer.

**BPMN Process Modeling (L180–229, 50 lines)**
Largest offender. The multi-tenancy domain list (L198–207) changes often and belongs in vault. The tool table (L220–228) is discoverable via `list_processes`. Keep: the BPMN-first principle (2 lines) + sync command (1 line) + "search before starting" rule (1 line). Move multi-tenancy table to vault. Remove tool table and hierarchy table.

**Global Instructions table (L257–273, 17 lines)**
Condense to: "9 instruction files in `~/.claude/instructions/` auto-apply by file pattern (csharp, markdown, wpf-ui, mvvm, winforms, a11y, sql-postgres, playwright, winforms-dark-theme). Override in `{project}/.claude/instructions/`."

### Items to UPDATE

| Item | Issue | Fix |
|------|-------|-----|
| Footer `Updated: 2026-02-22` (L279) | Stale by 3 weeks | Update to 2026-03-15 |
| SOPs table — "Update configs" row (L241) | Points to old SOP path; `sync_project.py` is now the mechanism | Update note to mention `sync_project.py` |

---

## Project `claude-family/CLAUDE.md` — Section Analysis (342 lines)

### Sections to KEEP

| Section | Lines | Why |
|---------|-------|-----|
| Header + Problem Statement (L1–18) | 18 | Project identity; links PROBLEM_STATEMENT.md |
| Current Phase (L45–49) | 5 | Orientation for new sessions |
| Architecture Overview (L52–62) | 11 | 5-bullet summary + ARCHITECTURE.md pointer |
| Project Structure tree (L65–92) | 28 | Filesystem map — unique to this file |
| Coding Standards (L95–101) | 7 | Python/SQL/commit rules |
| Work Tracking routing table (L104–114) | 11 | Essential routing + Data Gateway line |
| Workflow Tools table (L120–127) | 8 | 5 core daily-use tools |
| Configuration (DB-Driven) (L199–212) | 14 | Already references `sync_project.py`; accurate |
| SOPs + Key Procedures (L215–229) | 15 | Concise pointers |
| Footer (L338–341) | 4 | Required |

### Sections to TRIM

**Config Management CRITICAL block (L21–42, 22 lines)**
The SQL comment block (L33–37) is misleading — implies manual SQL edits. `sync_project.py` handles all this now. The `generate_project_settings.py` reference (L39) is outdated. Remove SQL block. Update L39 to: "Regenerate manually: `python scripts/sync_project.py <project-name>`". Condense to ~12 lines.

**Config Tools table (L128–135, 8 lines)**
These 4 tools are niche infrastructure tools, not daily work. Condense to 1 line: "Config tools: `update_claude_md`, `deploy_claude_md`, `deploy_project`, `regenerate_settings` — see Config SOP."

**Memory Tools table (L137–148, 12 lines)**
Covered entirely by `storage-rules.md`. Replace with: "Memory tools: `remember(content)` / `recall_memories(query)` — see `storage-rules.md`."

**Knowledge Tools table (L149–160, 12 lines)**
8 infrequently-used tools. Condense to 1 line: "Knowledge/catalog: `catalog`, `recall_entities`, `store_book`, `extract_insights`, `search_conversations` — use ToolSearch for signatures."

**Filing Cabinet Tools table (L162–173, 12 lines)**
Table covered by storage-rules.md. Keep only the key gotcha: "Filing Cabinet: UPSERT on (project, component, title). Use `mode='append'` to concatenate. `is_pinned=True` surfaces at session start."

**WCC section (L175–196, 22 lines)**
WCC is automatic — no manual tool calls needed in normal use. Condense to: "WCC auto-assembles context per activity via RAG hook. Override with `store_session_fact('current_activity', name)` or use `assemble_context()` for debugging." Remove 4-tool table, detection priority list, and state machines table (state machines duplicate the work tracking routing table).

**Knowledge System (L267–312, 46 lines)**
The ASCII pipeline, memory tier descriptions, RAG explanation, and embed commands are all covered in MEMORY.md and RAG Usage Guide. Condense to 4 lines: pipeline one-liner, vault path, "RAG is automatic via rag_query_hook.py", embed command pointer.

**Recent Changes (L315–334, 20 lines)**
14-row changelog back to 2025-12-21. Changes older than ~60 days belong in git log. Keep last 3 entries (2026-03-15, 2026-03-14, 2026-03-13). Add "Full changelog: see git log." Remove 11 old rows.

### Sections to REMOVE

| Section | Lines | Reason |
|---------|-------|--------|
| Skills System (L232–253) | 22 | Duplicate of global CLAUDE.md; skills are DB-backed and auto-loaded |
| Auto-Apply Instructions (L256–263) | 8 | Exact duplicate of global CLAUDE.md |
| WCC tools table (L181–188) | 8 | WCC is automatic; tool details belong in vault |
| WCC state machines (L190–195) | 6 | Duplicates work tracking routing table above |
| Knowledge System memory tier descriptions (L274–280) | 7 | Fully in MEMORY.md |
| Knowledge System RAG explanation (L288–298) | 11 | In RAG Usage Guide vault doc |
| Knowledge System embed commands (L301–311) | 11 | In Vault Embeddings Management SOP |
| Changelog rows before 2026-03-13 (L325–333) | 9 | Historical; git log is authoritative |

### Items to UPDATE

| Item | Issue | Fix |
|------|-------|-----|
| `generate_project_settings.py` (L39) | Replaced by `sync_project.py` | Update reference |
| SQL comment block (L33–37) | Implies manual SQL; `sync_project.py` handles this | Remove block; replace with sync_project.py command |
| Table count "58 tables" (L55) | May be stale | Query `SELECT count(*) FROM information_schema.tables WHERE table_schema='claude'` to verify |
| `regenerate_settings` in Config Tools (L135) | `sync_project.py` is now preferred full sync | Add parenthetical: "(subset — prefer `sync_project.py`)" |

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: C:\Projects\claude-family\docs\claude-md-audit-details-2026-03-15.md
