# Initialize New Project

Create a new project with governance-compliant structure.

## Parameters
- **project_name**: $ARGUMENTS (required - pass as argument)
- **project_type**: Will prompt if not provided (web, cli, library, infrastructure)

## What This Does

1. **Creates directory structure** at `C:\Projects\{project_name}\`
2. **Generates core documents**:
   - `CLAUDE.md` - Claude configuration
   - `PROBLEM_STATEMENT.md` - Problem definition
   - `ARCHITECTURE.md` - System design
   - `README.md` - User documentation
3. **Registers in database**:
   - Creates entry in `claude.projects` with phase='planning'
   - Links documents via `claude.document_projects`
4. **Runs document scanner** to index files

## Instructions

When executing this command:

1. **Validate project name**:
   - Must be lowercase with hyphens (e.g., `my-new-project`)
   - Must not already exist in `C:\Projects\`
   - Must not be reserved (claude-family, shared, etc.)

2. **Ask user for**:
   - Project type: web, cli, library, or infrastructure
   - Brief problem statement (1-2 sentences)
   - Who will use this project

3. **Create directory**: `C:\Projects\{project_name}\`

4. **Generate files** using templates from `C:\Projects\claude-family\templates\`:
   - Copy and fill `CLAUDE.template.md` → `CLAUDE.md`
   - Copy and fill `PROBLEM_STATEMENT.template.md` → `PROBLEM_STATEMENT.md`
   - Copy and fill `ARCHITECTURE.template.md` → `ARCHITECTURE.md`
   - Create basic `README.md`

5. **Register in database**:
```sql
INSERT INTO claude.projects (project_name, description, status, phase)
VALUES ('{project_name}', '{description}', 'active', 'planning')
RETURNING project_id;
```

6. **Run document scanner**:
```bash
python C:\Projects\claude-family\scripts\scan_documents.py --project {project_name}
```

7. **Verify compliance**:
```sql
SELECT * FROM claude.v_project_governance WHERE project_name = '{project_name}';
```

8. **Report to user**:
   - Confirm project created
   - Show compliance status (should be 100%)
   - Provide next steps

## Example Usage

```
/project-init my-new-app
```

Then answer prompts for project type and description.

---

**Action ID**: See `claude.actions` WHERE action_name = 'project-init'

---

**Version**: 1.0
**Created**: 2025-12-06
**Updated**: 2026-01-08
**Location**: .claude/commands/project-init.md
