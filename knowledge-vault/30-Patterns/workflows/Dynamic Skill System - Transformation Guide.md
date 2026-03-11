---
projects:
  - claude-family
tags:
  - skills
  - awesome-copilot
  - transformation
synced: false
---

# Dynamic Skill System - Transformation Guide

## awesome-copilot → Claude Code

### YAML Frontmatter

**Before** (VS Code Copilot):
```yaml
---
name: "..."
description: "..."
tools: [edit/editFiles, search/usages, ...]
applyTo: "**"
excludeAgent: ["coding-agent"]
---
```

**After** (Claude Code):
```yaml
---
description: "..."
allowed-tools:
  - Read
  - Edit
  - Bash(*)
  - mcp__project-tools__*
context: fork
---
```

### Tool Mapping

| VS Code | Claude Code |
|---------|-------------|
| edit/editFiles | Edit |
| search/codebase | Grep, Glob, Task(Explore) |
| execute/runTerminal | Bash |
| web/fetch | WebFetch |
| read/problems | - (not applicable) |

### Required Additions

1. **MCP Tools**: Reference project-tools, postgres, orchestrator
2. **Vault Paths**: Link to relevant vault docs
3. **Delegation**: Include spawn patterns for implementation
4. **Enforcement**: Reference column_registry, testing requirements

## Category Mapping

| awesome-copilot | Claude Code |
|-----------------|-------------|
| agent | .claude/skills/{name}.md |
| instruction | .claude/instructions/{name}.instructions.md |
| collection | Merge into relevant skills |
| prompt | Evaluate for slash commands |

## Completed Transformations

| Original | Transformed To | Status |
|----------|----------------|--------|
| Senior Cloud Architect | `architect.md` | Done |
| debug | `debug.md` | Done |
| code-review-generic | `code-review.md` | Done |
| Implementation Plan Generation | `planner/skill.md` | Done |
| Expert React Frontend Engineer | `react-expert/skill.md` | Done |
| sql-optimization | `sql-optimization/skill.md` | Done |

---

## Related Documents

- [[Skill Catalog]] - Complete list of skills
- [[Dynamic Skill System - BPMN Diagram]] - How skills are suggested

---

**Version**: 1.1
**Created**: 2026-01-24
**Updated**: 2026-01-24
**Location**: knowledge-vault/30-Patterns/Dynamic Skill System - Transformation Guide.md
