---
name: project-ops
description: Project lifecycle operations (init, retrofit, phase advancement, compliance)
model: haiku
allowed-tools:
  - Read
  - Write
  - Edit
  - mcp__postgres__*
---

# Project Operations Skill

**Status**: Active

---

## Overview

Project lifecycle operations: initialization, retrofitting, phase advancement, and compliance checking.

**Detailed reference**: See [reference.md](./reference.md) for SQL examples, templates, and compliance details.

---

## When to Use

- Initializing a new project
- Adding Claude Family infrastructure to existing project
- Advancing project through development phases
- Checking project compliance
- Managing project configuration

---

## Quick Reference

### Commands

| Command | Purpose | When |
|---------|---------|------|
| `/project-init` | Initialize new project | Starting new project |
| `/retrofit-project` | Add Claude Family to existing project | Existing codebase |
| `/phase-advance` | Move to next phase | Completing phase |
| `/check-compliance` | Verify project standards | Regular audits |

---

## Project Initialization

`/project-init` creates:

```
my-project/
├── CLAUDE.md                    # AI constitution
├── PROBLEM_STATEMENT.md         # What, for whom, why
├── ARCHITECTURE.md              # System design
├── README.md                    # Human overview
├── .claude/
│   ├── instructions/           # Auto-apply coding standards
│   ├── skills/                 # Project-specific skills
│   └── hooks/                  # Enforcement scripts
├── docs/
│   ├── adr/                    # Architecture decisions
│   └── TODO_NEXT_SESSION.md    # Work tracking
└── knowledge-vault/            # Optional: Obsidian vault
```

---

## Project Phases

```
idea -> planning -> design -> implementation -> testing -> production -> archived
```

| Phase | Focus | Deliverables |
|-------|-------|--------------|
| **Idea** | Problem identification | Rough problem statement |
| **Planning** | Requirements, feasibility | PROBLEM_STATEMENT.md, success criteria |
| **Design** | Architecture, API design | ARCHITECTURE.md, ADRs |
| **Implementation** | Code, tests | Working features, test coverage |
| **Testing** | QA, performance | Test reports, bug fixes |
| **Production** | Deploy, monitor | Live system, monitoring |
| **Archived** | Retired | Final docs, archive reason |

---

## Retrofitting Existing Projects

`/retrofit-project` analyzes existing structure, creates missing docs, adds `.claude/` directory, creates DB record. **Preserves** existing code, git history, and documentation.

---

## Project Types

| Type | Description |
|------|-------------|
| `web-application` | Full-stack web apps |
| `api-service` | REST/GraphQL APIs |
| `cli-tool` | Command-line tools |
| `desktop-app` | Native desktop apps |
| `library` | Reusable packages |
| `infrastructure` | DevOps/tooling |
| `data-pipeline` | ETL/analytics |

---

## Related Skills

- `session-management` - Project-scoped sessions
- `work-item-routing` - Project work items
- `database-operations` - Project database access

---

## Key Gotchas

1. **Skipping core docs** — use `/project-init` to ensure docs are created
2. **Wrong project type** — affects MCP availability and patterns
3. **Not setting default identity** — sessions use wrong identity
4. **Phase skipping** — follow progression, validate requirements

---

**Version**: 2.0 (Progressive disclosure: split to SKILL.md overview + reference.md detail)
**Created**: 2025-12-26
**Updated**: 2026-03-29
**Location**: .claude/skills/project-ops/SKILL.md
