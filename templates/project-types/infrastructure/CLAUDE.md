# {{PROJECT_NAME}} - Infrastructure Project

**Type**: Infrastructure
**Created**: {{CREATED_DATE}}

---

## Project Overview

Infrastructure project containing shared configuration, scripts, and documentation.

---

## Project Structure

```
{{PROJECT_NAME}}/
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── configs/            # Configuration files
├── .claude/            # Claude slash commands
├── CLAUDE.md           # This file
└── README.md           # Project overview
```

---

## Build Commands

```bash
# No build - config/docs only

# Run scripts
python scripts/<script-name>.py

# Validate configs
# (add validation commands)
```

---

## When Working Here

This is an infrastructure project. Changes may affect multiple systems.
- Test scripts before committing
- Document configuration changes
- Coordinate with dependent projects

---

## Recent Work

```sql
SELECT summary, outcome, session_start
FROM claude.sessions
WHERE project_name = '{{PROJECT_NAME}}'
ORDER BY session_start DESC LIMIT 5;
```

---

**Version**: 1.0
**Location**: {{PROJECT_PATH}}/CLAUDE.md
