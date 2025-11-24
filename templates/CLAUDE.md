# {PROJECT_NAME}

**Type**: {commercial/internal/infrastructure}
**Purpose**: {One-line description of what this project does}

---

## Build Commands

```bash
# Development
{command to run development server}

# Tests
{command to run tests}

# Build
{command to build for production}

# Deploy (if applicable)
{deployment command}
```

---

## Key Constraints

- {Constraint 1 - e.g., "NEVER modify UserSDK - it's a third-party library"}
- {Constraint 2 - e.g., "All API calls must include auth token"}
- {Constraint 3 - e.g., "Database migrations must be backwards compatible"}

---

## Tech Stack

- **Frontend**: {React/Vue/Angular/N/A}
- **Backend**: {Python/FastAPI, Node/Express, .NET, etc.}
- **Database**: {PostgreSQL, MySQL, MongoDB, etc.}
- **Hosting**: {AWS, Azure, Local, Vercel, etc.}
- **Other**: {Redis, Celery, Docker, etc.}

---

## File Structure

```
{project-name}/
├── src/              # {Description of src}
├── tests/            # {Test files}
├── docs/             # {Business documents - 6 living docs}
│   ├── PROJECT_BRIEF.md
│   ├── BUSINESS_CASE.md
│   ├── ARCHITECTURE.md
│   ├── EXECUTION_PLAN.md
│   ├── COMPLIANCE.md
│   └── RISKS.md
├── data/             # {Data files if applicable}
├── README.md         # {User-facing documentation}
└── CLAUDE.md         # {This file - AI context}
```

---

## Important Gotchas

- {Gotcha 1 - e.g., "API rate limit is 100 req/min"}
- {Gotcha 2 - e.g., "Must run migrations before starting server"}
- {Gotcha 3 - e.g., "Environment variables must be set in .env file"}

---

## Recent Work

Query recent sessions from database:

```sql
SELECT summary, outcome, files_modified, session_start
FROM claude_family.session_history
WHERE project_name = '{project-name}'
ORDER BY session_start DESC LIMIT 10;
```

---

## When Working Here

You're likely:
- {Task 1 - e.g., "Adding new API endpoints"}
- {Task 2 - e.g., "Fixing bugs in frontend"}
- {Task 3 - e.g., "Updating documentation"}

**Remember**: {Important reminder - e.g., "Run tests before committing"}

---

**Version**: 1.0
**Created**: {YYYY-MM-DD}
**Location**: C:\\Projects\\{project-name}\\CLAUDE.md
