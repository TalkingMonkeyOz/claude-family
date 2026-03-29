# Project Operations Skill — Detailed Reference

## Project Initialization — Database Record

```sql
INSERT INTO claude.projects (
    project_id, project_name, project_path,
    project_type, phase, default_identity_id
) VALUES (
    gen_random_uuid(), 'my-project', 'C:/Projects/my-project',
    'web-application', 'planning', 'identity-uuid'::uuid
);
```

---

## Project Configuration (CLAUDE.md) — Full Template

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

## Identity Per Project

Each project has a dedicated Claude identity:

```sql
SELECT p.project_name, i.identity_name, i.role_description
FROM claude.projects p
JOIN claude.identities i ON p.default_identity_id = i.identity_id
WHERE p.project_name = 'my-project';
```

**Why**: Different projects need different expertise (tax law vs UI/UX vs infrastructure)

---

## Common Queries

```sql
-- List all projects
SELECT project_name, project_type, phase, is_active, created_at
FROM claude.projects
WHERE is_archived = false
ORDER BY created_at DESC;

-- Projects by phase
SELECT phase, COUNT(*) as project_count
FROM claude.projects
WHERE is_archived = false
GROUP BY phase
ORDER BY CASE phase
    WHEN 'idea' THEN 1 WHEN 'planning' THEN 2
    WHEN 'design' THEN 3 WHEN 'implementation' THEN 4
    WHEN 'testing' THEN 5 WHEN 'production' THEN 6
    WHEN 'archived' THEN 7 END;

-- Project activity (recent sessions)
SELECT p.project_name, COUNT(s.session_id) as session_count,
    MAX(s.session_start) as last_session
FROM claude.projects p
LEFT JOIN claude.sessions s ON p.project_name = s.project_name
WHERE p.is_archived = false
GROUP BY p.project_name
ORDER BY last_session DESC NULLS LAST;
```

---

## Project Templates

Templates in `C:\Projects\claude-family\templates\`:

```
templates/
├── CLAUDE.md.template.md
├── PROBLEM_STATEMENT.template.md
├── ARCHITECTURE.template.md
└── README.template.md
```

**Usage**: `/project-init` automatically uses these templates

---

## Compliance Checking — What Gets Verified

- [ ] Core docs exist (CLAUDE.md, PROBLEM_STATEMENT.md, ARCHITECTURE.md, README.md)
- [ ] CLAUDE.md has required sections
- [ ] Project registered in database
- [ ] Default identity configured
- [ ] TODO_NEXT_SESSION.md exists and recent
- [ ] Git repository initialized
- [ ] `.gitignore` includes sensitive files

**Output**: Compliance report with action items
