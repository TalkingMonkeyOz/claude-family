# Component Breadcrumb Audit — Vague vs Specific Knowledge References

**Date**: 2026-04-11
**Scope**: Rules (8), Skills (15 sampled of 24), Hooks (26), Core Protocol (8 rules)

---

## Rules

Only files with issues listed. Files not listed are clean.

| File | Vague | Specific | Vague Examples |
|------|-------|----------|----------------|
| `database-rules.md` | 2 | 5 | "Check `claude.column_registry` before writing" — no example query shown. "Check registry (varies by table)" for status fields — no actual valid values listed. |
| `build-tracking-rules.md` | 0 | 6 | Clean — names specific tools, tables, and override syntax. |
| `commit-rules.md` | 0 | 4 | Clean. |
| `no-loose-ends.md` | 1 | 2 | "Create a task (TaskCreate)" — does not mention `create_feedback()` or `create_linked_task()` as alternatives, only references generic "TaskCreate". |
| `storage-rules.md` | 0 | 12 | Clean — exemplary specificity with tool names, parameters, anti-patterns. |
| `system-change-process.md` | 1 | 4 | "Use `search_processes` or `list_processes`" — good. But "Check if modeled" is vague — no guidance on what to do when no BPMN model exists for the system. |
| `testing-rules.md` | 2 | 3 | "After modifying 3+ code files" — no tool to count files. "Ensure existing tests still pass" — no command given for claude-family project specifically (only generic `pytest`, `npm test`). |
| `working-memory-rules.md` | 1 | 2 | "See `storage-rules.md`" — fine as a cross-ref but the file adds almost no unique value beyond the pointer. Effectively a redirect. |

**Rules Summary**: 7 vague references across 5 of 8 files. `database-rules.md` and `testing-rules.md` are the worst offenders. `storage-rules.md` is the gold standard.

---

## Skills

Only skills with issues listed.

| File | Vague | Specific | Vague Examples |
|------|-------|----------|----------------|
| `database/SKILL.md` | 1 | 10 | `feedback.feedback_type` lists "bug, design, question, change" — **missing** `idea` and `improvement` which are valid values. Stale data acting as a broken breadcrumb. |
| `knowledge-capture/SKILL.md` | 0 | 6 | Clean. Good specific examples of `remember()` calls with parameters. |
| `sa-plan/SKILL.md` | 2 | 5 | "See: `knowledge-vault/30-Patterns/workflows/Structured Autonomy Workflow.md`" — hardcoded vault path, may not exist. Repeated at bottom. Should use `recall_memories("structured autonomy")` instead. |
| `check-compliance/SKILL.md` | 2 | 3 | "Missing hooks: Check `.claude/hooks.json` config" — `.claude/hooks.json` does not exist; hooks are in `settings.local.json`. "Stale docs: Update or archive old documents" — no specific tool or query provided. |
| `doc-keeper/SKILL.md` | 2 | 6 | "Check `knowledge-vault/Claude Family/mcp-and-tools/MCP Registry.md`" — hardcoded vault path that may be stale. Also references "per-project mcpServers in projects section" of `~/.claude.json` — vague about what "projects section" means. |
| `feedback/SKILL.md` | 0 | 8 | Clean — full SQL with specific column names and valid values. |
| `feature-workflow/SKILL.md` | 0 | 14 | Clean — very thorough with specific status values, MCP tool calls with parameters, SQL examples. |
| `phase-advance/SKILL.md` | 1 | 8 | "**Vault SOP**: [[Project Lifecycle SOP]]" — wiki-link to vault doc that may not exist. Should use `recall_memories("project lifecycle")` or remove. |
| `review-data/SKILL.md` | 1 | 3 | References `scripts/reviewer_data_quality.py` with `--table work_tasks` — but the table is `claude.build_tasks`, not `work_tasks`. Potentially broken example. |
| `winforms/SKILL.md` | 1 | 6 | "Related Knowledge" section lists 4 hardcoded vault paths (`knowledge-vault/20-Domains/WinForms/...`) — these may not exist and should use `recall_memories()` or `recall_entities()` instead. |
| `testing/SKILL.md` | 0 | 8 | Clean. |
| `todo/SKILL.md` | 0 | 7 | Clean — full SQL for every operation. |
| `ideate/SKILL.md` | 0 | 6 | Clean. |
| `session-save/SKILL.md` | 0 | 5 | Clean. |
| `maintenance/SKILL.md` | 0 | 7 | Clean — specific SQL, specific tool calls, specific thresholds. |

**Skills Summary**: 10 vague references across 7 of 15 sampled skills. Main patterns: (1) hardcoded vault paths instead of `recall_memories()`, (2) stale/incomplete valid values, (3) references to files that may not exist.

---

## Hooks

Only hooks with issues listed. Hooks not listed are clean.

| File | Issue |
|------|-------|
| `rag_query_hook.py` | **STALE HARDCODED PROTOCOL**: `DEFAULT_CORE_PROTOCOL` (line 31-47) says "5 systems" and lists Vault as "long-form docs, SOPs, research. Auto-searched via RAG" — live `core_protocol.txt` says "6 systems" and includes Credential Vault. Fallback protocol is out of date. Also says "CHECK TOOLS" (rule 7) instead of live version's "RECALL FIRST" + "CORRECT" (rules 7-8). |
| `rag_query_hook.py` | **DEAD CODE**: This hook appears to be superseded by `protocol_inject_hook.py` which loads `core_protocol.txt`. Both exist and both inject core protocol — potential double-injection or the RAG hook may be disabled but still present in codebase. |
| `pattern_suggest_hook.py` | **HARDCODED DB_CONNSTR**: Uses `"dbname=ai_company_foundation host=localhost"` instead of shared `config.py` module. No error handling pointer — fails silently on DB connection error. |
| `pattern_violation_hook.py` | **HARDCODED DB_CONNSTR**: Same issue — uses `"dbname=ai_company_foundation host=localhost"` instead of `config.py`. References `hal.patterns` and `hal.pattern_instances` tables without documenting whether these exist. |
| `context_injector_hook.py` | References `context_rules` table and mentions "inject_vault_query (optional RAG, ~500ms) - TODO" — unclear if this TODO was ever completed or if the vault query path is dead. |
| `session_startup_hook_enhanced.py` | `IDENTITY_MAP` hardcodes 2 identity UUIDs. If identities are added/changed in DB, this map goes stale. Should query `claude.identities` instead. |
| `check-compliance/SKILL.md ref` | `check_compliance` skill references `.claude/hooks.json` — but hooks are configured in `.claude/settings.local.json`, not a separate `hooks.json`. Broken breadcrumb in the remediation guidance. |

**Hooks Summary**: 7 issues across 5 of 26 hooks. The `rag_query_hook.py` stale fallback protocol is the most critical — if `core_protocol.txt` is ever missing, Claude gets an outdated 5-system protocol instead of the current 6-system version.

---

## Core Protocol

Source: `scripts/core_protocol.txt` (8 rules)

| Rule | Issue |
|------|-------|
| Rule 3 (STORAGE) | "See `storage-rules.md` (auto-loaded)" — good cross-ref. But then says "`/skill-load-memory-storage` for detailed guide" — this is a skill name that requires the reader to know to invoke it via Skill tool. No mention that it is a skill. Minor. |
| Rule 4 (DELEGATE) | "3+ files = spawn agent" — does not name the tool (`Task` tool). Says "save_checkpoint() after each task" — good specific call. |
| Rule 7 (RECALL FIRST) | "call recall_memories() + recall_entities()" — good specific tool calls. "project-tools has 60+ tools" — this count may go stale. |
| Rule 8 (CORRECT) | "call remember() with the correction" — good. "Tag it with the domain_concept name if one exists" — vague. Should say "include the domain_concept display_name in the content" or "use `recall_entities('topic')` to find the domain_concept first". |

**Core Protocol Summary**: 3 minor issues. Overall very specific. The stale fallback copy in `rag_query_hook.py` is a bigger concern than the live file.

---

## Cross-Cutting Issues

### 1. Hardcoded Vault Paths (HIGH)
**Files affected**: `sa-plan/SKILL.md`, `doc-keeper/SKILL.md`, `winforms/SKILL.md`, `phase-advance/SKILL.md`
**Pattern**: Skills reference `knowledge-vault/...` paths directly instead of using `recall_memories()` or `recall_entities()`.
**Risk**: Vault files get moved, renamed, or deleted. The skill then points to nothing.
**Fix**: Replace with `recall_memories("topic")` calls or wiki-links `[[Document Name]]`.

### 2. Stale Valid Values (MEDIUM)
**Files affected**: `database/SKILL.md`, `rag_query_hook.py`
**Pattern**: Inline lists of valid values that fall behind `claude.column_registry`.
**Risk**: Claude uses invalid values and gets constraint violations.
**Fix**: Always say "check `column_registry`" AND show the current values with a "verify with:" query.

### 3. Hardcoded Connection Strings (MEDIUM)
**Files affected**: `pattern_suggest_hook.py`, `pattern_violation_hook.py`
**Pattern**: `DB_CONNSTR = "dbname=ai_company_foundation host=localhost"` instead of `from config import get_db_connection`.
**Fix**: Use the shared `config.py` module like all other hooks do.

### 4. Stale Fallback Protocol (HIGH)
**Files affected**: `rag_query_hook.py`
**Pattern**: Hardcoded `DEFAULT_CORE_PROTOCOL` is 2 versions behind the live `core_protocol.txt`.
**Fix**: Either update the fallback to match, or remove it and fail gracefully when the file is missing.

---

**Version**: 1.0
**Created**: 2026-04-11
**Updated**: 2026-04-11
**Location**: docs/component-breadcrumb-audit.md
