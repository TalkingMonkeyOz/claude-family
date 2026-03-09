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
| project-tools | ~12k | Work tracking, knowledge, messaging, config ops (40+ tools) | Global |
| sequential-thinking | ~2k | Complex reasoning | Global |
| python-repl | ~2k | Python execution | Global |
| bpmn-engine | ~4k | BPMN process navigation, search, validation | Global |
| nimbus-knowledge | ~3k | Nimbus API domain knowledge | Nimbus projects only |
| mui-mcp | ~2k | MUI X docs | nimbus-mui, ATO only |

**Retired MCPs** (no longer available):
- `orchestrator` — **RETIRED 2026-02-24**. Replaced by native `Task` tool (agent spawning) and `project-tools` (messaging)
- `filesystem` — Retired Jan 2026. Replaced by built-in Read/Write/Edit/Glob/Grep tools
- `memory` — Retired Jan 2026. Replaced by `project-tools` cognitive memory (`remember`, `recall_memories`)

---

## Agent Types (via Native Task Tool)

> **Note**: The orchestrator MCP was retired 2026-02-24. Agent spawning now uses the native `Task` tool in Claude Code. See **[[Orchestrator MCP]]** for the historical agent list and capabilities (preserved as reference).

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

| Skill | Purpose |
|-------|---------|
| database-operations | SQL validation, column_registry checks, Data Gateway patterns |
| work-item-routing | Feedback, features, build_tasks routing |
| session-management | Session lifecycle (start/end/resume) |
| code-review | Pre-commit review, testing |
| project-ops | Project init, retrofit, phases |
| messaging | Inter-Claude communication, inbox |
| agentic-orchestration | Agent spawning (native Task tool), parallel work |
| testing-patterns | Test writing and execution |
| bpmn-modeling | BPMN-first process design, query/model/test workflows |

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
- [[Orchestrator MCP]] - RETIRED system (historical reference only)
- [[MCP configuration]] - How MCPs are configured
- [[Setting's File]] - Settings file locations
- [[Claude Hooks]] - Process enforcement

---

**Version**: 2.0 (Updated to current MCP list; marked orchestrator/filesystem/memory retired; updated skills to ADR-005 list)
**Created**: 2025-12-26
**Updated**: 2026-03-09
**Location**: Claude Family/Claude Tools Reference.md