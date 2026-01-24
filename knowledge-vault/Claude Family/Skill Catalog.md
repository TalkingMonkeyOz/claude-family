---
projects:
  - claude-family
tags:
  - skills
  - reference
synced: false
---

# Skill Catalog

Complete catalog of available skills for Claude Code. Use Skill tool to load.

---

## Core Skills (Built-in)

| Skill | Description | Agent |
|-------|-------------|-------|
| `session-management` | Session start/end/resume | - |
| `database` | PostgreSQL patterns, Data Gateway | haiku |
| `feature-workflow` | Feature lifecycle tracking | - |
| `work-item-routing` | Feedback, features, tasks | - |
| `agentic-orchestration` | Agent spawning, parallel work | - |
| `messaging` | Inter-Claude communication | - |
| `project-ops` | Project init, retrofit | - |
| `testing` | Testing patterns | - |
| `code-review` | Pre-commit review | sonnet |
| `doc-keeper` | Documentation maintenance | - |

---

## Domain Skills (Transformed)

| Skill | Description | Source |
|-------|-------------|--------|
| `architect` | System design, NFR, diagrams | awesome-copilot |
| `planner` | Implementation planning | awesome-copilot |
| `debug` | Systematic debugging | awesome-copilot |
| `react-expert` | React 19.2, hooks, RSC | awesome-copilot |
| `sql-optimization` | Query tuning, indexing | awesome-copilot |

---

## Technology Skills

| Skill | Description | Source |
|-------|-------------|--------|
| `winforms` | WinForms patterns | built-in |
| `wpf-ui` | WPF UI library | built-in |

---

## Related Documents

- [[Dynamic Skill System - BPMN Diagram]] - How skills are suggested
- [[Dynamic Skill System - Transformation Guide]] - Converting to Claude Code
- [[RAG Usage Guide]] - Semantic search over skills

---

## MCP Integration

Skills integrate with project-tools MCP:

| Tool | Purpose |
|------|---------|
| `find_skill` | Search skills by task description |
| `create_feature` | Track implementation work |
| `add_build_task` | Break down into tasks |
| `store_knowledge` | Capture learnings |

---

## Skill File Structure

```
.claude/skills/
├── architect.md           # Flat file (simple)
├── debug.md
├── code-review.md
├── planner/               # Folder (with hooks)
│   └── skill.md
├── react-expert/
│   └── skill.md
└── sql-optimization/
    └── skill.md
```

---

**Version**: 1.0
**Created**: 2026-01-24
**Updated**: 2026-01-24
**Location**: knowledge-vault/Claude Family/Skill Catalog.md
