---
projects:
- claude-family
tags:
- claude-md
- configuration
- deployment
- token-optimization
synced: false
---

# CLAUDE.md Change Process

How to modify CLAUDE.md files across the Claude Family ecosystem.

## Architecture: Two Layers of CLAUDE.md

| File | Scope | Loaded When |
|------|-------|-------------|
| `~/.claude/CLAUDE.md` (Global) | ALL projects, ALL sessions | Always - first thing loaded |
| `{project}/CLAUDE.md` (Project) | Single project only | When working in that project directory |

**Global** is the constitution - rules that apply everywhere.
**Project** is project-specific context - architecture, tools, phase, structure.

Both are loaded together, so **avoid duplication**. If something is in Global, don't repeat it in Project.

## Token Budget

| Source | Target | Notes |
|--------|--------|-------|
| Global CLAUDE.md | ~2,000 tokens (~200 lines) | Loaded on every session across all projects |
| Project CLAUDE.md | ~2,500-3,000 tokens (~250-300 lines) | Loaded per-project |
| `@` referenced standards | ~1,470 tokens | markdown-documentation.md - only reference ONCE |
| CORE_PROTOCOL (hook) | ~110 tokens | Injected every prompt via rag_query_hook.py |
| Session facts | ~100 tokens | Auto-injected from DB |
| **Total baseline** | **~6,000-7,000 tokens** | Before any RAG or work context |

**Rule**: Global + Project should stay under 5,000 tokens combined (excluding `@` references).

## What Goes Where

| Content Type | Where | Why |
|-------------|-------|-----|
| Schema rules, constraints | `database-rules.md` (rules file) | Enforced via hooks, not suggestions |
| SQL examples | MCP tools / skills | Tools handle this |
| Verification checklist | CORE_PROTOCOL (hook) | Injected every prompt automatically |
| Data Gateway pattern | `database-rules.md` + `database-operations` skill | Already enforced |
| Feedback system usage | `create_feedback` MCP tool | Tool is self-documenting |
| Delegation routing table | Global CLAUDE.md | Quick reference needed |
| Config management | Project CLAUDE.md + [[Config Management SOP]] | Critical context |
| Work tracking routing | Global CLAUDE.md | Universal pattern |

## How to Make Changes

### Global CLAUDE.md (`~/.claude/CLAUDE.md`)

1. Edit the file directly: `~/.claude/CLAUDE.md`
2. Sync to database: `sync_profile(project='claude-family', direction='file_to_db')`
3. Global file applies to all projects automatically (no per-project deployment needed)
4. Changes take effect on next session start

### Project CLAUDE.md (`{project}/CLAUDE.md`)

1. Edit the file directly in the project root
2. Sync to database: `sync_profile(project='{project-name}', direction='file_to_db')`
3. For deploying DB content to file: `sync_profile(project='{project-name}', direction='db_to_file')`
4. For updating specific sections: `update_claude_md(project, section, content)`

### CORE_PROTOCOL (rag_query_hook.py)

1. Edit `scripts/rag_query_hook.py` directly (the `CORE_PROTOCOL` constant)
2. Change takes effect immediately on next user prompt (no restart needed)
3. This is NOT a deployed component - it lives in the claude-family repo only

### Rules Files (`.claude/rules/*.md`)

1. Edit files in `.claude/rules/` directly
2. Can be deployed from DB: `deploy_project(project, components=['rules'])`
3. Rules are auto-loaded by Claude Code based on file patterns

## Injection Timeline (Per Prompt)

```
1. CLAUDE.md (Global)      - Loaded at session start, stays in system prompt
2. CLAUDE.md (Project)     - Loaded at session start, stays in system prompt
3. @ references            - Expanded inline when CLAUDE.md loads
4. .claude/rules/*.md      - Loaded at session start for matching files
5. CORE_PROTOCOL           - Injected every prompt by rag_query_hook.py
6. Session facts           - Injected every prompt by rag_query_hook.py
7. RAG results             - Injected on questions only by rag_query_hook.py
8. Config warning          - Injected when config keywords detected
```

Items 1-4 are **static** (loaded once). Items 5-8 are **dynamic** (per-prompt).

## Verification Checklist

After making changes:

- [ ] `wc -l ~/.claude/CLAUDE.md` - Should be ~200 lines
- [ ] `wc -l {project}/CLAUDE.md` - Should be ~250-300 lines
- [ ] Start new session - hooks still work
- [ ] Try Write without TaskCreate - task_discipline_hook should block
- [ ] Check CORE_PROTOCOL wording shows in hook output (check hooks.log)
- [ ] Verify `@` references load (markdown standard should still apply)

## Common Mistakes

- Adding SQL examples to CLAUDE.md (use MCP tools instead)
- Duplicating `@` reference in both Global and Project CLAUDE.md
- Editing `settings.local.json` instead of using config tools
- Putting enforcement rules in CLAUDE.md (use hooks - they can't be ignored)
- Adding verbose examples (link to vault docs instead)

---

**Version**: 1.0
**Created**: 2026-02-14
**Updated**: 2026-02-14
**Location**: knowledge-vault/40-Procedures/CLAUDE.md Change Process.md
