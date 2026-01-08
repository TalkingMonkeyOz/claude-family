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
**Last Updated**: 2026-01-08

---

## Overview

This skill provides guidance for project lifecycle operations: initialization, retrofitting, phase advancement, and compliance checking.

---

## When to Use

Invoke this skill when:
- Initializing a new project
- Adding Claude Family infrastructure to existing project
- Advancing project through development phases
- Checking project compliance
- Managing project configuration

---

## Quick Reference

### Project Lifecycle Commands

| Command | Purpose | When |
|---------|---------|------|
| `/project-init` | Initialize new project | Starting new project |
| `/retrofit-project` | Add Claude Family to existing project | Existing codebase |
| `/phase-advance` | Move to next phase | Completing phase |
| `/check-compliance` | Verify project standards | Regular audits |

---

## Project Initialization

### Creating a New Project

```bash
/project-init
```

**What it creates**:
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

**Database record**:
```sql
INSERT INTO claude.projects (
    project_id,
    project_name,
    project_path,
    project_type,
    phase,
    default_identity_id
) VALUES (
    gen_random_uuid(),
    'my-project',
    'C:/Projects/my-project',
    'web-application',
    'planning',
    'identity-uuid'::uuid
);
```

---

## Project Phases

### Phase Progression

```
planning → design → implementation → testing → production
```

### Phase Characteristics

| Phase | Focus | Deliverables |
|-------|-------|--------------|
| **Planning** | Requirements, feasibility | PROBLEM_STATEMENT.md, rough estimates |
| **Design** | Architecture, API design | ARCHITECTURE.md, ADRs, wireframes |
| **Implementation** | Code, tests | Working features, test coverage |
| **Testing** | QA, performance | Test reports, bug fixes |
| **Production** | Deploy, monitor | Live system, monitoring |

### Advancing Phases

```bash
/phase-advance to=implementation
```

**What it does**:
1. Validates current phase requirements met
2. Updates `claude.projects` phase column
3. Creates phase transition ADR
4. Updates TODO_NEXT_SESSION.md

---

## Retrofitting Existing Projects

### Adding Claude Family Infrastructure

```bash
/retrofit-project
```

**What it does**:
1. Analyzes existing project structure
2. Creates missing core docs (CLAUDE.md, etc.)
3. Adds `.claude/` directory structure
4. Creates database project record
5. Sets up default identity

**Preserves**:
- Existing code and structure
- Current git history
- Existing documentation (merges, doesn't replace)

---

## Project Configuration (CLAUDE.md)

### Essential Sections

```markdown
# Project Name

**Type**: web-application | cli-tool | library | desktop-app
**Status**: planning | design | implementation | testing | production
**Project ID**: uuid-from-database
**Identity**: identity-name (uuid-from-database)

## Problem Statement
[Link to PROBLEM_STATEMENT.md]

## Architecture
[Link to ARCHITECTURE.md]

## Tech Stack
[Table of technologies]

## MCP Servers Available
[Which MCP servers this project can use]

## Coding Standards
[Project-specific conventions]

## Work Tracking
[How to use feedback, features, build_tasks]
```

---

## Compliance Checking

### What Gets Checked

```bash
/check-compliance
```

**Verifies**:
- [ ] Core docs exist (CLAUDE.md, PROBLEM_STATEMENT.md, ARCHITECTURE.md, README.md)
- [ ] CLAUDE.md has required sections
- [ ] Project registered in database
- [ ] Default identity configured
- [ ] TODO_NEXT_SESSION.md exists and recent
- [ ] Git repository initialized
- [ ] `.gitignore` includes sensitive files

**Output**: Compliance report with action items

---

## Project Types

### Supported Project Types

| Type | Description | Example Tech Stack |
|------|-------------|-------------------|
| `web-application` | Full-stack web apps | React + Node.js + PostgreSQL |
| `api-service` | REST/GraphQL APIs | FastAPI + PostgreSQL |
| `cli-tool` | Command-line tools | Python + Click |
| `desktop-app` | Native desktop apps | WPF + .NET, Electron |
| `library` | Reusable packages | NPM package, PyPI library |
| `infrastructure` | DevOps/tooling | Terraform, Docker configs |
| `data-pipeline` | ETL/analytics | Airflow + Spark |

---

## Identity Per Project

Each project has a dedicated Claude identity:

```sql
-- Get project's default identity
SELECT
    p.project_name,
    i.identity_name,
    i.role_description
FROM claude.projects p
JOIN claude.identities i ON p.default_identity_id = i.identity_id
WHERE p.project_name = 'my-project';
```

**Why**: Different projects need different expertise (tax law vs UI/UX vs infrastructure)

---

## Common Queries

```sql
-- List all projects
SELECT
    project_name,
    project_type,
    phase,
    is_active,
    created_at
FROM claude.projects
WHERE is_archived = false
ORDER BY created_at DESC;

-- Projects by phase
SELECT
    phase,
    COUNT(*) as project_count
FROM claude.projects
WHERE is_archived = false
GROUP BY phase
ORDER BY
    CASE phase
        WHEN 'planning' THEN 1
        WHEN 'design' THEN 2
        WHEN 'implementation' THEN 3
        WHEN 'testing' THEN 4
        WHEN 'production' THEN 5
    END;

-- Project activity (recent sessions)
SELECT
    p.project_name,
    COUNT(s.session_id) as session_count,
    MAX(s.session_start) as last_session
FROM claude.projects p
LEFT JOIN claude.sessions s ON p.project_name = s.project_name
WHERE p.is_archived = false
GROUP BY p.project_name
ORDER BY last_session DESC NULLS LAST;
```

---

## Project Templates

Templates available in `C:\Projects\claude-family\templates\`:

```
templates/
├── CLAUDE.md.template.md
├── PROBLEM_STATEMENT.template.md
├── ARCHITECTURE.template.md
├── README.template.md
└── llms.txt.template.md
```

**Usage**: `/project-init` automatically uses these templates

---

## Related Skills

- `session-management` - Project-scoped sessions
- `work-item-routing` - Project work items
- `database-operations` - Project database access

---

## Key Gotchas

### 1. Skipping Core Docs

**Problem**: Starting to code without PROBLEM_STATEMENT.md or ARCHITECTURE.md

**Solution**: Use `/project-init` to ensure docs are created

### 2. Wrong Project Type

**Problem**: Choosing wrong type affects MCP availability and patterns

**Solution**: Match project type to actual architecture

### 3. Not Setting Default Identity

**Problem**: Sessions use wrong identity for the project

**Solution**: Always set `default_identity_id` during project init

### 4. Phase Skipping

**Problem**: Jumping from planning → implementation without design

**Solution**: Follow phase progression, validate requirements

---

**Version**: 1.0
**Created**: 2025-12-26
**Location**: .claude/skills/project-ops/skill.md
