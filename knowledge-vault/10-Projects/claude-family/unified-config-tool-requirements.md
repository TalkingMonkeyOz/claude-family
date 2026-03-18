---
projects:
- claude-family
tags:
- config
- requirements
- deployment
---

# Unified Config Management Tool — Requirements

## The Scenario

Project Metis wants to add a new skill. Currently, Metis can't — skills are in the central DB (`claude.skills` table), and there's no MCP tool to update them. The file protection hook blocks direct edits to `.claude/skills/*/SKILL.md`. The only way is raw SQL or messaging claude-family to do it. Neither works well.

Meanwhile, `update_claude_md()` works perfectly — it validates, versions, deploys, and audits. We need the same pattern for everything else.

## What Exists Today

### Working (CLAUDE.md only)
- `update_claude_md(project, section, content, mode)` — parses by section, updates DB, creates `profile_versions` snapshot, deploys to file, logs to `audit_log`
- `deploy_claude_md(project)` — one-way DB → file sync
- File protection hook blocks direct CLAUDE.md edits with redirect message

### Infrastructure Ready But Unused
- `claude.skills_versions` table — **exists, 0 rows**, no code writes to it
- `claude.rules_versions` table — **exists, 0 rows**, no code writes to it
- `claude.instructions_versions` table — **exists, 0 rows**, no code writes to it
- File protection hook already blocks skills/rules/agents/commands with "deployed from database" message

### Broken / Inconsistent
- **Two skills tables**: `claude.skills` (used by sync_project.py, has scope column) vs `claude.skill_content` (used by server_v2.py deploy_project, legacy) — need consolidation
- **No update tools**: No `update_skill()`, `update_rule()`, `update_instruction()` MCP tools
- Projects can't self-serve config changes — must message claude-family or use raw SQL

## What I Want

A single MCP tool that handles all deployable config, following the `update_claude_md()` pattern:

```
update_config(
    component_type: "skill" | "rule" | "instruction" | "claude_md",
    project: "project-name",
    component_name: "session-management",     # for skill/rule/instruction
    section: "Recent Changes",                # for claude_md only
    content: "new content...",
    change_reason: "Added task description requirement",
    mode: "replace" | "append"                # default: replace
)
```

### Behavior per component_type

| Type | Validates | Versions to | Deploys to | Audits |
|------|-----------|-------------|------------|--------|
| `skill` | name exists in `claude.skills` | `claude.skills_versions` | `.claude/skills/{name}/SKILL.md` | `audit_log` |
| `rule` | name exists in `claude.rules` | `claude.rules_versions` | `.claude/rules/{name}.md` | `audit_log` |
| `instruction` | name exists in `claude.instructions` | `claude.instructions_versions` | `.claude/instructions/{name}.instructions.md` | `audit_log` |
| `claude_md` | project exists | `claude.profile_versions` | `CLAUDE.md` | `audit_log` |

### Key design decisions

1. **Single tool, not four** — reduces MCP surface, consistent interface
2. **component_name identifies what to update** — scoped by project
3. **Versioning is mandatory** — every change creates a snapshot
4. **Deploy is automatic** — after DB update, file is regenerated
5. **Scope-aware** — respects global vs project_type vs project scoping
6. **Works cross-project** — Metis can update its own skills without messaging

### What about agents and commands?

Agents and commands are stored in `claude.skills` with `scope='agent'` and `scope='command'`. They deploy to `.claude/agents/` and `.claude/commands/` respectively. The tool handles them as skill variants:

- `update_config("skill", project, "coder-sonnet", content, reason)` — if scope='agent', deploys to agents dir
- `update_config("skill", project, "session-end", content, reason)` — if scope='command', deploys to commands dir

### Table consolidation needed

Before building: consolidate `claude.skill_content` (legacy, 26 rows) into `claude.skills` (current, 20 rows). The `skills` table is the source of truth per ADR-005. `skill_content` should be deprecated.

## Solution Architecture

```
update_config(component_type, project, name, content, reason)
    │
    ├── Validate: component exists in DB for this project/scope
    │   └── Not found → error with available components list
    │
    ├── Version: INSERT into {type}_versions table
    │   └── Increment version_number, store full content snapshot
    │
    ├── Update: UPDATE main table with new content
    │   └── Set updated_at = NOW()
    │
    ├── Deploy: Write file to correct location
    │   └── skill → .claude/skills/{name}/SKILL.md
    │   └── rule → .claude/rules/{name}.md
    │   └── instruction → .claude/instructions/{name}.instructions.md
    │   └── claude_md → delegate to existing update_claude_md()
    │
    └── Audit: INSERT into claude.audit_log
        └── entity_type, entity_id, change_source='update_config', from→to
```

## Status: IMPLEMENTED (2026-03-16)

1. ~~Write requirements doc~~ (this document)
2. ~~Consolidate skill_content → skills table~~ — skill_content view dropped, deploy_project fixed to use claude.skills
3. BPMN model the update_config lifecycle — TODO
4. ~~Implement the tool in server_v2.py~~ — Done, with UPSERT support (create + update)
5. ~~Test: update a skill from another project~~ — METIS skill created via tool
6. ~~Update file protection hook messages to reference update_config()~~ — Already done

### UPSERT Enhancement (2026-03-16)

Original design only supported UPDATE. Enhanced to UPSERT:
- If component exists → version snapshot + update (original behavior)
- If component doesn't exist → INSERT with scope/description + deploy
- New params: `scope` (global/project_type/project/command/agent), `description`
- For project-scoped skills, auto-resolves project UUID from project name
- Filed as FB187, resolved same session

### deploy_project Fix (2026-03-16)

Fixed FB188: deploy_project's skills component referenced dropped `skill_content` view.
Now queries `claude.skills` directly with proper scope filtering (mirrors sync_project.py).

---

**Version**: 1.1
**Created**: 2026-03-15
**Updated**: 2026-03-16
**Location**: knowledge-vault/10-Projects/claude-family/unified-config-tool-requirements.md
