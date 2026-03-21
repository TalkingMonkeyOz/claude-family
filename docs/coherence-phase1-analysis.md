# Design Coherence Check — Phase 1: Concepts Extracted

**Scope**: Claude Family infrastructure docs (10 files)
**Date**: 2026-03-21
**Part 2 (findings)**: See `coherence-phase1-findings.md`

---

## Concepts Extracted

| concept_name | source | type | description |
|---|---|---|---|
| Database Source of Truth | global CLAUDE.md, project CLAUDE.md | principle | PostgreSQL `ai_company_foundation` schema `claude` is the authoritative source for all configuration. Files are generated from the database and manual edits to generated files are temporary or overwritten. |
| Schema Enforcement | global CLAUDE.md, database-rules.md | constraint | All infrastructure tables must use `claude.*` schema. Legacy schemas `claude_family.*` and `claude_pm.*` are forbidden. Stated in three places with consistent phrasing. |
| Data Gateway Pattern | database-rules.md | principle | Before any INSERT/UPDATE on constrained columns, query `claude.column_registry` for valid values. Prevents bad data from reaching the database and acts as a documentation source for valid enumerations. |
| 3-Tier Memory System | project CLAUDE.md, storage-rules.md | decision | Session facts (SHORT), knowledge table (MID), proven patterns (LONG). `remember()` auto-routes, `recall_memories()` retrieves. `consolidate_memories()` manages lifecycle promotion and decay. |
| Notepad (Session Facts) | storage-rules.md, working-memory-rules.md | decision | `store_session_fact()` for credentials, configs, decisions, and findings within a session. Survives context compaction but is gone after session ends. |
| Filing Cabinet (Workfiles) | storage-rules.md | decision | `stash()` / `unstash()` for component-scoped working notes that bridge sessions. Organized as project (cabinet) → component (drawer) → title (file). |
| Reference Library (Entity Catalog) | storage-rules.md, global CLAUDE.md | decision | `catalog()` / `recall_entities()` for structured data like API endpoints, OData entities, schemas. Uses RRF fusion search. |
| Vault (Knowledge Vault) | storage-rules.md, global CLAUDE.md | decision | Long-form markdown docs in `knowledge-vault/` with YAML frontmatter. Auto-searched via RAG hook. Used for procedures, SOPs, and domain knowledge. |
| 5-System Storage Model | storage-rules.md | principle | Exactly five storage systems: Notepad, Memory, Filing Cabinet, Reference Library, Vault. Each has a distinct purpose and lifecycle. Crossing boundaries (e.g., storing credentials in Memory) is an anti-pattern. |
| MCP-First Principle | global CLAUDE.md, project CLAUDE.md | principle | Check MCP tools before writing code or raw SQL. project-tools has 40+ tools. Status changes go through WorkflowEngine tools, never raw UPDATE statements. |
| WorkflowEngine State Machine | project CLAUDE.md, build-tracking-rules.md | decision | Status changes for feedback/features/build_tasks are enforced via WorkflowEngine. Invalid transitions are rejected. Raw UPDATE statements bypassing the engine are prohibited. |
| BPMN-First Rule | global CLAUDE.md, system-change-process.md | principle | Model workflows in BPMN before writing code. Write tests for the BPMN model. Then implement code. Applies to all projects and especially to system changes. |
| Build Hierarchy (Stream/Feature/Task) | build-tracking-rules.md | decision | Three-level hierarchy: Stream (feature_type='stream') → Feature (parent_feature_id) → Build Task. Only projects with streams use this full hierarchy; others use flat features/tasks. |
| Dependency Enforcement | build-tracking-rules.md | constraint | `start_work()` blocks if predecessor tasks are not completed. Circular dependencies are rejected. Override requires explicit `override_reason` and is logged to audit_log. |
| No Loose Ends | no-loose-ends.md | principle | Every deferred piece of work must become a tracked task before the session ends. "We'll do this later" is not acceptable without a task number. |
| Structured Autonomy | global CLAUDE.md | decision | Features touching 3+ files trigger a 4-phase workflow: PLAN (analyst-sonnet) → GENERATE → IMPLEMENT (coder-sonnet or coder-haiku) → REVIEW (reviewer-sonnet). Skipped for bug fixes and small changes. |
| Delegation Threshold | global CLAUDE.md | constraint | Anything touching 3+ files must spawn an agent via the native Task tool. Agents must write results to session notes/files and return 1-line summaries. |
| Self-Healing Config | project CLAUDE.md, working-memory-rules.md | decision | All project config files regenerate from the database on every launch and SessionStart hook. Manual edits to generated files are temporary. Run `sync_project.py` to force regeneration. |
| Config Flow Chain | project CLAUDE.md | decision | Three-layer merge: `config_templates` → `project_type_configs` → `workspaces.startup_config`. Project-specific overrides go in `workspaces.startup_config` (JSONB). |
| Commit Message Format | commit-rules.md | constraint | Conventional commit format: `<type>: <description>` with co-authorship line. Types: feat, fix, refactor, docs, chore, test. Work item references [F1], [FB1], [BT1] included when applicable. |
| Branch Naming Convention | global CLAUDE.md, commit-rules.md | constraint | Feature branches: `feature/F1-description`. Fix branches: `fix/FB3-description`. Commit-rules adds `task/BT5-description` which global CLAUDE.md does not include. |
| Testing Trigger (3+ files) | testing-rules.md | constraint | Tests required after modifying 3+ code files, before committing feature work, and after bug fixes. Happy path + edge cases for features; regression test for bugs. |
| System Change Process | system-change-process.md | decision | Any change to hook scripts, workflow code, config scripts, BPMN files, or enforcement rules requires: search existing models, update BPMN first, write tests, then implement code. BPMN and code committed together. |
| Process Failure Capture | system-change-process.md | decision | When a hook or state machine fails, file `create_feedback` type='bug', search/update the BPMN model, then fix. Creates a self-improvement loop. |
| Skills-First Architecture | project CLAUDE.md | decision | 32 skills in `.claude/skills/`, all with YAML frontmatter. Skills replaced process_router (ADR-005, 2025-12) and slash commands (2026-03-15). Invoke via `Skill` tool. |
| RAG Hook Injection | global CLAUDE.md, project CLAUDE.md | decision | `rag_query_hook.py` fires on every UserPromptSubmit. Injects knowledge-vault docs and core protocol rules silently. Applies to all Claude instances on all projects. |
| Session Lifecycle | global CLAUDE.md, project CLAUDE.md | decision | SessionStart hook auto-logs session. SessionEnd hook auto-closes. Manual `/session-end` captures detailed summary and learnings. Automatic hooks fire regardless. |
| Feedback Type Enumeration | database-rules.md | constraint | Valid `feedback_type` listed as: bug, design, question, change, idea. Note: `improvement` is also valid per the MCP tool — see findings doc. |
| Priority Scale | database-rules.md | constraint | Priority is 1–5 where 1=critical. The endpoint label (4 vs 5 = "low") is inconsistent across docs — see findings doc. |
| wiki-link Routing Pattern | project CLAUDE.md | decision | CLAUDE.md uses wiki-links `[[Name]]` instead of hardcoded paths. Entity catalog is the indirection layer. Introduced 2026-03-17. |
| Hook Failure Capture | project CLAUDE.md | decision | All hooks have `capture_failure()` in fail-open catch blocks. Failures logged to JSONL and auto-filed as feedback. `rag_query_hook.py` surfaces pending failures on every prompt. |

---

**Version**: 1.0
**Created**: 2026-03-21
**Updated**: 2026-03-21
**Location**: docs/coherence-phase1-analysis.md
