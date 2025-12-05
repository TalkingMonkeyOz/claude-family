# SOP-004: Project Initialization and Templates

**Status**: Active
**Created**: 2025-12-06
**Author**: claude-code-unified
**Applies to**: All new projects

---

## Purpose

This SOP defines the standard process for creating new projects with governance-compliant structure.

---

## Quick Start

```bash
# From any Claude session:
/project-init my-new-project

# Answer prompts for:
# - Project type (web, cli, library, infrastructure)
# - Brief problem description
# - Target users
```

---

## Templates Location

All templates are in `C:\Projects\claude-family\templates\`:

| Template | Purpose |
|----------|---------|
| `CLAUDE.template.md` | AI configuration and context |
| `PROBLEM_STATEMENT.template.md` | Problem definition |
| `ARCHITECTURE.template.md` | System design |
| `README.template.md` | User documentation |
| `.docs-manifest.template.json` | Document tracking |

### Type-Specific Templates

Located in `templates/project-types/{type}/`:
- `infrastructure/` - Config/scripts projects
- `web-app/` - Web applications
- `python-tool/` - Python utilities
- `csharp-desktop/` - C# desktop apps

---

## Template Variables

Templates use `{{VARIABLE}}` placeholders:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{PROJECT_NAME}}` | Project name (lowercase, hyphens) | `my-new-app` |
| `{{PROJECT_TYPE}}` | Type of project | `Web App` |
| `{{PROJECT_ID}}` | UUID from database | `abc123...` |
| `{{PROJECT_PHASE}}` | Current phase | `planning` |
| `{{CREATED_DATE}}` | Creation date | `2025-12-06` |
| `{{PROBLEM_SUMMARY}}` | One-line problem description | `Users need...` |
| `{{BUILD_COMMAND}}` | Build command for project type | `npm run build` |
| `{{TEST_COMMAND}}` | Test command | `npm test` |

---

## Project Creation Process

### Step 1: Run Command

```
/project-init {project-name}
```

### Step 2: Answer Prompts

Claude will ask for:
1. **Project type** - web, cli, library, or infrastructure
2. **Problem statement** - What problem does this solve? (1-2 sentences)
3. **Target users** - Who will use this?

### Step 3: Review Created Structure

```
C:\Projects\{project-name}\
├── .claude/
│   └── commands/      # Slash commands (if infrastructure)
├── docs/              # Documentation
├── src/               # Source code (structure varies by type)
├── CLAUDE.md          # AI configuration
├── PROBLEM_STATEMENT.md
├── ARCHITECTURE.md
├── README.md
└── .gitignore
```

### Step 4: Verify Compliance

```sql
SELECT * FROM claude.project_governance
WHERE project_name = '{project-name}';
```

Should show:
- `has_claude_md = true`
- `has_problem_statement = true`
- `has_architecture = true`
- `phase = 'planning'`

---

## Phase Advancement

After requirements/design work, advance to next phase:

```
/phase-advance
```

### Phase Progression

```
idea → research → planning → implementation → maintenance
```

Each transition has requirements - see `/phase-advance` command for details.

---

## Manual Project Creation

If not using `/project-init`:

1. **Create directory**: `C:\Projects\{name}\`

2. **Copy templates**:
   ```bash
   cp templates/CLAUDE.template.md {project}/CLAUDE.md
   cp templates/PROBLEM_STATEMENT.template.md {project}/PROBLEM_STATEMENT.md
   cp templates/ARCHITECTURE.template.md {project}/ARCHITECTURE.md
   ```

3. **Fill in placeholders** - Replace all `{{VARIABLE}}` with actual values

4. **Register in database**:
   ```sql
   INSERT INTO claude.projects (project_name, status, phase)
   VALUES ('{name}', 'active', 'planning');
   ```

5. **Run document scanner**:
   ```bash
   python scripts/scan_documents.py --project {name}
   ```

---

## Creating New Templates

To add a new project type template:

1. Create folder: `templates/project-types/{new-type}/`

2. Add `CLAUDE.md` with type-specific:
   - Build/test commands
   - Directory structure
   - Key constraints
   - Common gotchas

3. Update `scripts/create_project.py`:
   - Add type to `PROJECT_TYPES` list
   - Add directory structure in `create_project_structure()`

4. Test with dry-run:
   ```bash
   python scripts/create_project.py test-project {new-type} --dry-run
   ```

---

## Troubleshooting

### "Project already exists"

Either:
- Use different name
- Delete existing directory first
- Check `claude.projects` for orphaned entries

### "Database registration failed"

Check:
- PostgreSQL is running
- Connection string in script is correct
- `claude.projects` table exists

### "Template not found"

Verify templates exist:
```bash
dir C:\Projects\claude-family\templates\
```

---

## Related

- `/project-init` - Slash command for project creation
- `/phase-advance` - Advance project phase
- `/check-compliance` - Verify governance compliance
- `scripts/create_project.py` - Python scaffolding script

---

**Version**: 1.0
**Location**: C:\Projects\claude-family\docs\sops\SOP-004-PROJECT-INITIALIZATION.md
