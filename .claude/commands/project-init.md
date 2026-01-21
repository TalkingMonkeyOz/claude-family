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
   - Creates entry in `claude.workspaces` with project_type
   - Links documents via `claude.document_projects`
4. **Sets up slash commands**:
   - Copies standard commands from claude-family to project
   - Registers commands in `claude.shared_commands`
5. **Runs document scanner** to index files

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

6. **Set up slash commands**:
   - Create `.claude/commands/` directory in project
   - Copy all standard commands from claude-family:
```bash
python C:\Projects\claude-family\scripts\propagate_commands.py --all
```
   - Register commands in database:
```sql
-- Copy standard commands for the new project
INSERT INTO claude.shared_commands (command_name, filename, description, content, tags, version, scope, scope_ref, is_core, is_active)
SELECT
    command_name, filename, description, content, tags, version,
    'project', '{project_id}', false, true
FROM claude.shared_commands
WHERE scope = 'project'
AND scope_ref = '9b563af2-4762-4878-b5bf-429dac0cc481'  -- Use nimbus-import as template
ON CONFLICT DO NOTHING;
```

7. **Run document scanner**:
```bash
python C:\Projects\claude-family\scripts\scan_documents.py --project {project_name}
```

8. **Verify compliance**:
```sql
SELECT * FROM claude.v_project_governance WHERE project_name = '{project_name}';
```

9. **Report to user**:
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

**Version**: 1.1
**Created**: 2025-12-06
**Updated**: 2026-01-21
**Location**: .claude/commands/project-init.md
