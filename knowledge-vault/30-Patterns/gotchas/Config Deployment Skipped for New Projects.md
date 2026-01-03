---
projects:
- claude-family
tags:
- gotcha
- config
- new-project
- workspaces
synced: false
---

# Config Deployment Skipped for New Projects

When launching a new project, you may see `[WARN] Config deployment skipped`.

---

## The Problem

The launcher uses `workspaces.json` to determine which projects get config deployment. If a project is:
1. Added to the database (`claude.workspaces`)
2. But NOT in `workspaces.json`

Then config deployment is skipped and the project gets minimal settings.

---

## Symptoms

- `[WARN] Config deployment skipped` in launcher output
- Minimal `settings.local.json` (no hooks)
- RAG not working (no UserPromptSubmit hook)
- Session not auto-logged (no SessionStart hook)

---

## The Fix (Automatic)

**SessionStart hook now auto-syncs workspaces.json**.

When a session starts, if the current project isn't in `workspaces.json`:
1. The hook queries `claude.workspaces` from the database
2. Regenerates `workspaces.json` with all active projects
3. Logs: `"Regenerated workspaces.json with N projects"`

---

## Manual Fix (If Needed)

```bash
# Regenerate settings for the project
cd /c/Projects/YOUR-PROJECT
python /c/Projects/claude-family/scripts/generate_project_settings.py YOUR-PROJECT
```

Or manually add to `workspaces.json`:
```json
{
  "workspaces": {
    "YOUR-PROJECT": {
      "path": "C:\\Projects\\YOUR-PROJECT",
      "type": "your-project-type",
      "description": "Description"
    }
  }
}
```

---

## Prevention

When creating new projects, always:
1. Add to `claude.projects` table
2. Add to `claude.workspaces` table with correct `project_type`
3. The SessionStart hook will handle the rest

See [[New Project SOP]] for proper workflow.

---

## Related

- [[New Project SOP]] - Creating projects properly
- [[Config Management SOP]] - How config sync works
- [[Windows npx MCP wrapper]] - Another common startup issue

---

**Version**: 1.0
**Created**: 2026-01-03
**Updated**: 2026-01-03
**Location**: knowledge-vault/30-Patterns/gotchas/Config Deployment Skipped for New Projects.md
