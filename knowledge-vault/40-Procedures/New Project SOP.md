---
title: New Project SOP
category: procedure
status: active
created: 2025-12-27
updated: 2025-12-27
tags:
- sop
- project-setup
- onboarding
projects: []
---

# New Project SOP

**Purpose**: Standard operating procedure for creating new Claude Family projects

**Quick Start**: Run `/project-init {name}` (uses Skill tool with project-ops)

---

## Prerequisites

Before creating a new project, gather:

- [ ] **Project name** - lowercase with hyphens (e.g., `personal-finance-system`)
- [ ] **Project type** - one of:
  - `infrastructure` - Infrastructure/tooling projects
  - `csharp-desktop` - C# .NET desktop (WPF, Console)
  - `csharp-winforms` - C# WinForms applications
  - `web-app` - Web applications (Next.js, React)
  - `tauri-react` - Tauri desktop with React
- [ ] **Location** - `C:\Projects\{name}` (standard location)
- [ ] **Purpose** - What problem does this solve? (1-2 sentences)

---

## Automated Method (Recommended)

Use the `/project-init` command which handles everything automatically:

```bash
# In any Claude Code session:
/project-init project-name
```

This will:
1. ✓ Create directory structure
2. ✓ Generate governance docs (CLAUDE.md, PROBLEM_STATEMENT.md, ARCHITECTURE.md)
3. ✓ Register in database (`projects`, `workspaces` tables)
4. ✓ Create identity record
5. ✓ Generate `.claude/settings.local.json` from project type defaults
6. ✓ Run compliance check

**Verify**: Run `/check-compliance` to ensure 100% governance

---

## Manual Method (If Skill Not Available)

### 1. Create Project Directory

```bash
mkdir C:\Projects\{project-name}
cd C:\Projects\{project-name}
```

### 2. Register in Database

```sql
-- Insert into projects table
INSERT INTO claude.projects (
    project_id,
    project_name,
    description,
    status,
    created_at
) VALUES (
    gen_random_uuid(),
    'project-name',
    'Project description',
    'active',
    NOW()
) RETURNING project_id;

-- Note the returned project_id for next step

-- Insert into workspaces table
INSERT INTO claude.workspaces (
    project_name,
    project_path,
    project_type,
    is_active,
    added_at
) VALUES (
    'project-name',
    'C:\Projects\project-name',
    'csharp-desktop',  -- or appropriate type
    true,
    NOW()
);

-- Create identity for project
INSERT INTO claude.identities (
    identity_id,
    identity_name,
    identity_type,
    description,
    created_at
) VALUES (
    gen_random_uuid(),
    'claude-project-name',
    'claude_instance',
    'Claude instance for project-name project',
    NOW()
) RETURNING identity_id;

-- Update project with default identity
UPDATE claude.projects
SET default_identity_id = '{identity_id from above}'
WHERE project_name = 'project-name';
```

### 3. Generate Configuration

```bash
# Generate settings.local.json from project type defaults
cd C:\Projects\project-name
python C:\Projects\claude-family\scripts\generate_project_settings.py project-name
```

This creates `.claude/settings.local.json` with:
- Hooks (from project type defaults)
- MCP servers (from project type defaults)
- Skills (from project type defaults)
- Instructions (from project type defaults)

### 4. Create Governance Documents

Create three files in project root:

**CLAUDE.md**:
```markdown
# {Project Name}

**Type**: {project-type}
**Status**: Planning
**Project ID**: {uuid}

## Problem Statement
See PROBLEM_STATEMENT.md

## Architecture Overview
See ARCHITECTURE.md

## Quick Queries
[SQL queries for project status]
```

**PROBLEM_STATEMENT.md**:
```markdown
# Problem Statement - {Project Name}

## The Problem
[1-2 paragraph description]

## Current State
[What exists today]

## Desired State
[What should exist]

## Success Criteria
1. ...
2. ...
```

**ARCHITECTURE.md**:
```markdown
# Architecture - {Project Name}

## System Overview
[High-level architecture]

## Components
[Key components and their responsibilities]

## Data Flow
[How data moves through the system]

## Technology Stack
[Technologies used]
```

### 5. Verify Compliance

```sql
SELECT * FROM claude.v_project_governance
WHERE project_name = 'project-name';
```

Should show:
- `has_claude_md = true`
- `has_problem_statement = true`
- `has_architecture = true`
- `compliance_pct = 100`

---

## Project Type Defaults

What you get automatically based on project type:

### infrastructure
- **MCP Servers**: postgres, memory, orchestrator
- **Skills**: database-operations, work-item-routing, session-management, code-review, project-ops, messaging, agentic-orchestration
- **Instructions**: sql-postgres.instructions.md

### csharp-desktop
- **MCP Servers**: postgres, memory
- **Skills**: code-review, testing-patterns
- **Instructions**: csharp.instructions.md, a11y.instructions.md

### csharp-winforms
- **MCP Servers**: postgres, memory
- **Skills**: code-review, testing-patterns
- **Instructions**: csharp.instructions.md, winforms.instructions.md, winforms-dark-theme.instructions.md, a11y.instructions.md

### web-app
- **MCP Servers**: postgres, memory
- **Skills**: code-review, testing-patterns
- **Instructions**: playwright.instructions.md, a11y.instructions.md

### tauri-react
- **MCP Servers**: postgres, memory
- **Skills**: code-review, testing-patterns
- **Instructions**: playwright.instructions.md, a11y.instructions.md

---

## Customizing Project Configuration

To override defaults for a specific project:

```sql
-- Add project-specific config overrides
UPDATE claude.workspaces
SET startup_config = '{
  "enabledMcpjsonServers": ["postgres", "memory", "custom-mcp"],
  "hooks": {
    "PostToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "python custom-hook.py",
        "timeout": 5
      }]
    }]
  }
}'::jsonb
WHERE project_name = 'project-name';
```

Next session will regenerate settings with these overrides applied.

---

## Troubleshooting

**Problem**: `/project-init` command not found

**Solution**: Use Skill tool directly:
```
Use the Skill tool with skill="project-ops" and args="init project-name"
```

**Problem**: Settings not generated

**Solution**:
1. Check project exists in `claude.workspaces`
2. Check project type is valid (run `SELECT * FROM claude.project_type_configs`)
3. Run generator manually: `python scripts/generate_project_settings.py project-name`

**Problem**: Compliance check fails

**Solution**: Check which documents are missing:
```sql
SELECT has_claude_md, has_problem_statement, has_architecture
FROM claude.v_project_governance
WHERE project_name = 'project-name';
```

Create missing documents using templates above.

---

**Version**: 1.0
**Created**: 2025-12-27
**Updated**: 2025-12-27
**Location**: 40-Procedures/New Project SOP.md
