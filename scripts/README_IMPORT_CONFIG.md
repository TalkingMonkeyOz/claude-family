# Config Import Script

This script imports configuration files from the file system into the Claude database.

## Overview

The `import_config_to_database.py` script populates three tables in the `claude` schema:

1. **claude.skills** - Configuration skill definitions
   - Imported from `~/.claude/skills/` (global) and `.claude/skills/` (project)
   - Each skill folder contains markdown files that are concatenated as content

2. **claude.instructions** - Auto-apply coding standards
   - Imported from `~/.claude/instructions/*.instructions.md` (global only)
   - Parses YAML frontmatter to extract `applyTo` glob pattern
   - Uses `applyTo` from frontmatter, or generates fallback pattern from filename

3. **claude.rules** - Project-specific rules
   - Imported from `.claude/rules/*.md` (project)
   - Extracts rule type from filename (e.g., `commit-rules.md` → `commit`)

## Requirements

- Python 3.8+
- psycopg2: `pip install psycopg2-binary`
- PyYAML: `pip install pyyaml`
- PostgreSQL database with `claude` schema

## Usage

### Basic Usage

```bash
python scripts/import_config_to_database.py
```

### Environment Variables

The script uses the following environment variable to connect to the database:

```bash
DATABASE_URL=postgresql://user:password@localhost/ai_company_foundation
```

If not set, defaults to: `postgresql://localhost/ai_company_foundation`

### Example with Custom Connection

```bash
export DATABASE_URL="postgresql://admin:secret@db.example.com/ai_company_foundation"
python scripts/import_config_to_database.py
```

## Output

The script prints a summary of imported items:

```
Claude Config Import Tool
--------------------------------------------------

✓ Connected to database

--- Importing Skills ---
✓ Imported skill: agentic-orchestration (global)
✓ Imported skill: code-review (global)
✓ Imported skill: agentic-orchestration (project)
...

--- Importing Instructions ---
✓ Imported instruction: a11y (applies_to: **/*.cs,**/*.tsx,**/*.ts,**/*.css)
✓ Imported instruction: csharp (applies_to: **/*.cs)
...

--- Importing Rules ---
✓ Imported rule: commit-rules (type: commit)
✓ Imported rule: database-rules (type: database)
...

==================================================
IMPORT SUMMARY
==================================================
Skills imported:        20
Instructions imported:  9
Rules imported:         3
Total:                  32
==================================================

✓ Import complete!
```

## Idempotency

The script uses `ON CONFLICT DO UPDATE` to allow re-running the import multiple times:

- If a skill/instruction/rule with the same name and scope already exists, it will be updated
- Timestamps (`updated_at`) will be refreshed
- Content will be replaced with the latest from files

## File Paths

The script imports from the following hardcoded paths:

| Item | Path |
|------|------|
| Global Skills | `C:/Users/johnd/.claude/skills/` |
| Project Skills | `C:/Projects/claude-family/.claude/skills/` |
| Global Instructions | `C:/Users/johnd/.claude/instructions/` |
| Project Rules | `C:/Projects/claude-family/.claude/rules/` |

To change these paths, edit the script constants or the directory checks in the import methods.

## Database Schema

### claude.skills

```sql
CREATE TABLE claude.skills (
    skill_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    scope VARCHAR NOT NULL CHECK (scope IN ('global', 'project')),
    scope_ref UUID,
    content TEXT NOT NULL,
    description TEXT,
    file_pattern VARCHAR,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(name, scope, scope_ref)
);
```

### claude.instructions

```sql
CREATE TABLE claude.instructions (
    instruction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    scope VARCHAR NOT NULL CHECK (scope IN ('global', 'project')),
    scope_ref UUID,
    applies_to TEXT NOT NULL,
    content TEXT NOT NULL,
    priority INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(name, scope, scope_ref)
);
```

### claude.rules

```sql
CREATE TABLE claude.rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    scope VARCHAR NOT NULL CHECK (scope IN ('global', 'project')),
    scope_ref UUID,
    content TEXT NOT NULL,
    rule_type VARCHAR,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(name, scope, scope_ref)
);
```

## Troubleshooting

### Connection Error

```
✗ Database connection failed: connection refused
```

Make sure PostgreSQL is running and the connection string is correct:

```bash
psql postgresql://localhost/ai_company_foundation -c "SELECT 1"
```

### Missing psycopg2

```
Error: psycopg2 not installed. Run: pip install psycopg2-binary
```

Install the required package:

```bash
pip install psycopg2-binary pyyaml
```

### File Not Found

The script gracefully handles missing directories:

- If a directory doesn't exist, it skips that import step
- Missing files within directories are also skipped
- Encoding errors are handled with UTF-8 fallback (`errors='replace'`)

## Notes

- Skill folders must contain at least one `.md` file to be imported
- Instruction files must be named `*.instructions.md`
- Rule files must be named `*.md` in the rules directory
- The project ID for claude-family is hardcoded: `20b5627c-e72c-4501-8537-95b559731b59`

---

**Version**: 1.0
**Created**: 2025-01-10
**Updated**: 2025-01-10
