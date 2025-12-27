---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.757592'
tags:
- quick-reference
- claude-family
---

# Claude Tools Reference

All available tools, MCPs, agents, and skills in one place.

---

## MCP Servers

See **[[MCP Registry]]** for complete documentation.

| Server | Tokens | Purpose | Scope |
|--------|--------|---------|-------|
| postgres | ~6k | Database access | Global |
| orchestrator | ~9k | Agent spawning | Global |
| sequential-thinking | ~2k | Complex reasoning | Global |
| python-repl | ~2k | Python execution | Global |
| filesystem | ~9k | File operations | claude-family only |
| memory | ~6k | Persistent graph | claude-family only |
| mui-mcp | ~2k | MUI X docs | nimbus, ATO only |

---

## Orchestrator Agents

See **[[Orchestrator MCP]]** for full agent documentation and tools.

### Fast (Haiku $0.01-0.08/task)

| Agent | Cost | Use Case |
|-------|------|----------|
| lightweight-haiku | $0.01 | Simple file ops |
| doc-keeper-haiku | $0.03 | Documentation maintenance |
| coder-haiku | $0.035 | Fast code writing |
| python-coder-haiku | $0.045 | Python + REPL + DB |
| web-tester-haiku | $0.05 | Playwright E2E |
| tester-haiku | $0.052 | Unit/integration tests |
| ux-tax-screen-analyzer | $0.08 | ATO UX analysis |

### Balanced (Sonnet $0.10-0.35/task)

| Agent | Cost | Use Case |
|-------|------|----------|
| reviewer-sonnet | $0.105 | Code review, LLM-as-Judge |
| planner-sonnet | $0.21 | Task breakdown |
| security-sonnet | $0.24 | Security audits |
| analyst-sonnet | $0.30 | Research, docs |
| research-coordinator-sonnet | $0.35 | Multi-agent research |

### Premium (Opus $0.70-0.85/task)

| Agent | Cost | Use Case |
|-------|------|----------|
| researcher-opus | $0.725 | Deep analysis |
| architect-opus | $0.825 | System design |

---

## Skills

| Skill | Location | Purpose |
|-------|----------|---------|
| database-operations | `.claude/skills/database/` | Data Gateway patterns |
| testing-patterns | `.claude/skills/testing/` | Test level guidance |
| feature-workflow | `.claude/skills/feature-workflow/` | Feature tracking |
| doc-keeper | `.claude/skills/doc-keeper/` | Documentation maintenance |
| nimbus-api | `.claude/skills/nimbus-api/` | Nimbus API patterns |

---

## Built-in Tools

| Tool | Purpose |
|------|---------|
| Read | Read files |
| Write | Write files |
| Edit | Edit files |
| Glob | Find files by pattern |
| Grep | Search file contents |
| Bash | Run shell commands |
| Task | Spawn subagents |
| WebSearch | Search the web |
| WebFetch | Fetch URL content |
| LSP | Code intelligence |
| TodoWrite | Track tasks |

---

## Config Hierarchy

| Level | Location | Scope |
|-------|----------|-------|
| Global | `~/.claude.json` → `mcpServers` | All projects |
| Project | `.mcp.json` | Git-tracked, shared |
| Local | `~/.claude.json` → `projects[path]` | Per-project |

---

## Related Docs

- [[MCP Registry]] - All MCPs with install guidelines
- [[Orchestrator MCP]] - Agent spawning and messaging
- [[MCP configuration]] - How MCPs are configured
- [[Setting's File]] - Settings file locations
- [[Claude Hooks]] - Process enforcement
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: Claude Family/Claude Tools Reference.md