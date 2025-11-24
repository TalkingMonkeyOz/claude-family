# Claude Family - Infrastructure Project

**Type**: Infrastructure
**Purpose**: Shared configuration, scripts, and documentation for Claude Family instances

---

## Project Structure

```
claude-family/
├── docs/                     # Documentation and session notes
├── .claude/                  # Shared slash commands (distributed to instances)
├── shared/
│   ├── commands/            # Slash commands (session-start, session-end)
│   ├── scripts/             # Python utilities
│   └── docs/                # Importable documentation
└── README.md
```

---

## This Repository Contains

**Shared Resources:**
- Slash commands (`/session-start`, `/session-end`)
- Python scripts (workspace sync, context loading)
- Documentation (MCP guides, troubleshooting)
- Session notes archive

**NOT Code Projects:**
- Work projects (nimbus, ATO) are in separate repos
- Personal projects are in separate repos
- This is ONLY infrastructure

---

## Build Commands

```bash
# No build - this is config/docs only

# Test scripts
python shared/scripts/sync_workspaces.py
python shared/scripts/select_project.py

# Commit changes
git add .
git commit -m "Update: description"
git push
```

---

## When Working Here

You're likely:
- Updating shared scripts
- Adding/modifying slash commands
- Updating documentation
- Archiving session notes

**Remember**: Changes here affect ALL Claude instances on next startup.

---

## Documentation Management

**System**: `.docs-manifest.json` + `audit_docs.py` + git pre-commit hook

**Rules:**
- CLAUDE.md must stay ≤250 lines (enforced by pre-commit hook)
- Audit monthly: `python scripts/audit_docs.py`
- Archive candidates: Move to `docs/archive/YYYY-MM/`
- Deprecated docs: Keep 90 days, then archive

**Install hook**: `python scripts/install_git_hooks.py`

---

## Procedures Registry

**Central database of ALL Claude Family procedures** - no more searching!

**Quick Query:**
```sql
-- Find procedures for current project
SELECT procedure_name, short_description, location, mandatory, frequency
FROM claude_family.my_procedures
WHERE 'all' = ANY(applies_to_projects);

-- Find mandatory procedures only
SELECT procedure_name, frequency, location
FROM claude_family.my_procedures
WHERE mandatory = true;
```

**Key Procedures:**
- Session Start/End: `SELECT * FROM claude_family.my_procedures WHERE procedure_type = 'session-workflow'`
- C# Compliance: `SELECT * FROM claude_family.my_procedures WHERE 'claude-pm' = ANY(applies_to_projects)`
- All Mandatory: `SELECT * FROM claude_family.my_procedures WHERE mandatory = true`

**Location:** `claude_family.procedure_registry` table (12 procedures registered)
**View:** `claude_family.my_procedures` (sorted by priority)

---

## Recent Work

```sql
SELECT summary, outcome, files_modified, session_start
FROM claude_family.session_history
WHERE project_name = 'claude-family'
ORDER BY session_start DESC LIMIT 10;
```

---

**Version**: 1.1 (Project-Specific - Infrastructure + Doc Management)
**Created**: 2025-10-21
**Updated**: 2025-10-23
**Location**: C:\Projects\claude-family\CLAUDE.md
