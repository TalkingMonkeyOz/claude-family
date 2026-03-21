# Instructions & Memory Coherence Audit — Findings

## Summary
- 11 global instruction files checked (9 original + 2 new: coding-ethos, react-component-architecture)
- 1 project instruction file checked (nimbus-api)
- 3 memory files checked (MEMORY.md, infrastructure_systems.md, feedback_claude_md_routing.md)
- 15 findings total (7 HIGH, 5 MEDIUM, 3 LOW)

---

## HIGH Priority

1. **python-repl listed as active MCP but not configured** — MEMORY.md "Available MCP Servers" table lists `python-repl | execute_python` as an active server. `CLAUDE.md` (claude-family) lists it in the Architecture section: "postgres, project-tools (~60 tools), python-repl, sequential-thinking, bpmn-engine". The actual `.mcp.json` has only: postgres, project-tools, sequential-thinking, mui, playwright, bpmn-engine. `python-repl` is not present. Any Claude told to use `execute_python` will get a tool-not-found error. MEMORY.md also directs "Large data → python-repl" in its MCP-first table.

2. **Core Protocol rule count and content mismatch in MEMORY.md** — MEMORY.md states "Current version: v11 (2026-03-11, 8 rules)" and documents 8 distinct rules (rules 3+4 are separate NOTEPAD and MEMORY rules). The actual `scripts/core_protocol.txt` has 7 rules — rules 3+4 were consolidated into a single "STORAGE: 5 systems" rule, and the DELEGATE/OFFLOAD/BPMN-FIRST rules renumbered. Any Claude relying on MEMORY.md's rule mapping will reference wrong rule numbers and miss the current storage guidance.

3. **server_v2.py "uncommitted — safe to modify" gotcha is false** — MEMORY.md states: "server_v2.py is uncommitted - safe to modify. Located at mcp-servers/project-tools/server_v2.py". Git log shows server_v2.py has 3+ commits (most recent: feat code knowledge graph, 2026-03-18). This is now a committed production file. The "safe to modify without committing" guidance is dangerous.

4. **markdown.instructions.md contains deprecated `synced: false` field** — The YAML frontmatter template in `markdown.instructions.md` (line 53) includes `synced: false  # Set to true after manual sync`. The standards document (`markdown-documentation.md`) explicitly states "Note: synced: false field is deprecated. Embeddings are managed by embed_vault_documents.py." The instruction file directly contradicts the standard it's supposed to enforce. Every new vault doc created using this template will have a stale deprecated field.

5. **sql-postgres.instructions.md lists incomplete feedback_type values** — Line 67 states `feedback.feedback_type: bug, design, question, change`. The actual valid values in `server_v2.py` (line 4064) are `Literal["bug", "design", "idea", "question", "change", "improvement"]`. Both `idea` and `improvement` are missing from the instruction. Claude following this file will incorrectly reject valid types or produce invalid SQL.

6. **MEMORY.md hook table is missing 4 active hooks** — The "Hook Scripts" table lists 11 hooks but 4 active hooks registered in `settings.local.json` are absent: `sql_governance_hook.py`, `code_collision_hook.py`, `postcompact_hook.py`, and `task_completed_hook.py`. Claudes diagnosing hook behavior using this table will have an incomplete picture.

7. **Global CLAUDE.md instruction file count stale (9 → 11)** — Line 181 of `~/.claude/CLAUDE.md` states "9 files: csharp, winforms, winforms-dark-theme, wpf-ui, mvvm, a11y, sql-postgres, playwright, markdown". Two new files have been added: `coding-ethos.instructions.md` and `react-component-architecture.instructions.md`, bringing the total to 11. The listed 9 names omit both new files, so Claudes won't know these auto-apply standards exist.

---

## MEDIUM Priority

8. **MEMORY.md "Available MCP Servers" omits playwright** — The table lists 7 entries (including retired nimbus-knowledge) but does not include `playwright`, which is actively configured in `.mcp.json`. Claudes will not know playwright browser automation tools are available.

9. **CLAUDE.md (claude-family) table count stale (58 vs 63)** — Architecture section says "schema claude (58 tables)". `infrastructure_systems.md` documents the post-entity-catalog count as 63 tables (58 + 5 from entity system: entity_types, entities, entity_relationships + 2 others). Global `CLAUDE.md` says "60+ tables" which is acceptably vague, but the project CLAUDE.md is precisely wrong.

10. **MEMORY.md "Central Deployment" section conflicts with actual startup behavior** — `infrastructure_systems.md` states "settings.local.json regenerates via `regenerate_settings()` (NOT auto on SessionStart)". The actual `session_startup_hook_enhanced.py` (line 503-516) runs `sync_project.py --no-interactive` unconditionally on every session start. Settings do regenerate automatically on SessionStart. The "NOT auto" claim misleads Claudes into thinking manual intervention is needed.

11. **infrastructure_systems.md references `generate_project_settings.py` and `deploy_components.py` as the deployment scripts** — The "Central Deployment" section names these two scripts. While both files still exist in `scripts/`, the canonical deployment script is now `sync_project.py` (which replaced and wraps the other two). MEMORY.md already notes this for the CLAUDE.md doc but `infrastructure_systems.md` still references the old script names.

12. **wpf-ui.instructions.md references skill path as `skill.md` (lowercase)** — Lines 12, 187, 232, 308 reference `.claude/skills/wpf-ui/skill.md`. The actual file is `.claude/skills/wpf-ui/SKILL.md` (uppercase). On case-sensitive filesystems this would fail. On Windows (case-insensitive) it works, but the reference is inconsistent with every other SKILL.md in the project.

---

## LOW Priority

13. **MEMORY.md "8 hooks have capture_failure()" count understates coverage** — The claim says "All 8 hooks have capture_failure() in fail-open catch blocks". `grep` finds 11 hook scripts with `capture_failure` imports. The count was accurate when written but coverage has expanded. Minor accuracy issue, no operational impact.

14. **crash-recovery and reinforce-protocol skill directories are empty** — Two directories exist in `.claude/skills/` (crash-recovery, reinforce-protocol) with no SKILL.md or content. They appear to be placeholder directories that were never populated. No Claude can invoke these skills. They are not listed in CLAUDE.md so there's no immediate confusion, but they're dead weight that could cause confusion if encountered.

15. **markdown.instructions.md "Working" doc type limit differs from standards** — `markdown.instructions.md` table shows Working docs max 100 lines. The `markdown-documentation.md` standard adds a "Reports (docs/)" type at 200 lines (hook-enforced) that doesn't appear in the instruction file's Document Types table. Instruction file is not wrong, just incomplete — Claudes won't know reports have a higher limit than general working docs.

---

**Version**: 1.0
**Created**: 2026-03-21
**Updated**: 2026-03-21
**Location**: docs/coherence-instructions-audit.md
