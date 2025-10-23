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

## Recent Work

```sql
SELECT summary, outcome, files_modified, session_start
FROM claude_family.session_history
WHERE project_name = 'claude-family'
ORDER BY session_start DESC LIMIT 10;
```

---

**Version**: 1.0 (Project-Specific - Infrastructure)
**Created**: 2025-10-21
**Location**: C:\Projects\claude-family\CLAUDE.md
