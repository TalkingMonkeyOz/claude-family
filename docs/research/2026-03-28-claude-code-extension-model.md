# Claude Code Extension Model — Summary (2026-03-28)

Research from official Anthropic docs (code.claude.com) and anthropics/claude-code GitHub.

## The 7 Layers (simplest to most complex)

| Layer | Location | Purpose | Loads |
|-------|----------|---------|-------|
| **CLAUDE.md** | `./CLAUDE.md`, `~/.claude/CLAUDE.md` | Project/user instructions | Every session |
| **Rules** | `.claude/rules/*.md` | Path-scoped instructions | Conditionally (glob match) |
| **Skills** | `.claude/skills/<name>/SKILL.md` | Reusable workflows, slash commands | On demand or auto |
| **Subagents** | `.claude/agents/<name>.md` | Isolated AI with custom tools/model | When delegated |
| **Hooks** | `settings.json` hooks object | Deterministic shell/HTTP/prompt | On lifecycle events |
| **Plugins** | Dir with `.claude-plugin/plugin.json` | Distributable bundle of all above | When installed |
| **MCP** | `.mcp.json` | External tool servers | Session start |

## Key Findings

**Commands merged into Skills.** Both `.claude/commands/` and `.claude/skills/` create `/name`. Skills recommended (more features). Existing commands still work.

**`.claude/instructions/` is NOT official.** The official mechanism for file-pattern-scoped instructions is `.claude/rules/` with `paths` frontmatter. Our custom instructions directory is non-standard.

**Plugins are for distribution, not customization.** Start with standalone `.claude/` config. Convert to plugin only when sharing with teams/community. Plugin skills are namespaced (`/plugin:skill`).

**No `.claude-plugins/` directory in docs.** Plugins live in their own directories with `.claude-plugin/plugin.json` manifests. Installed via `/plugin install`.

**Auto memory (v2.1.59+) overlaps with our `remember()`.** Built-in at `~/.claude/projects/<project>/memory/MEMORY.md`. Claude writes notes automatically. Needs investigation re: interaction with our system.

**Subagent persistent memory is official.** `memory: user|project|local` in agent frontmatter. Could complement our workfile system for agent-specific context.

## Implications for Claude Family

| What we do | Status | Action needed |
|-----------|--------|---------------|
| Skills in `.claude/skills/` | Correct | None |
| Hooks in settings.json | Correct | None |
| Rules in `.claude/rules/` | Correct | None |
| CLAUDE.md for instructions | Correct | None |
| `.claude/instructions/` | Non-standard | Migrate to `.claude/rules/` with `paths` frontmatter |
| `.claude/collections/` | Non-standard | Not in official docs; evaluate |
| No plugins created | Gap | Could package skills for cross-project distribution |
| Custom `remember()` system | Overlap | Investigate interaction with auto-memory (#405) |

## Full Reference

Detailed breakdown of all 7 mechanisms stashed in workfile: `claude-code-extensions / extension-model-reference`

## Sources

- [Overview](https://code.claude.com/docs/en/overview) | [Plugins](https://code.claude.com/docs/en/plugins) | [Skills](https://code.claude.com/docs/en/skills)
- [Subagents](https://code.claude.com/docs/en/sub-agents) | [Memory](https://code.claude.com/docs/en/memory) | [Hooks](https://code.claude.com/docs/en/hooks)
- [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md) | [Official Plugins](https://github.com/anthropics/claude-plugins-official)

---
**Version**: 1.0
**Created**: 2026-03-28
**Updated**: 2026-03-28
**Location**: docs/research/2026-03-28-claude-code-extension-model.md
