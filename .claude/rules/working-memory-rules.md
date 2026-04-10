# Working Memory Rules

**Session facts and storage routing**: See `storage-rules.md` (auto-loaded) for the complete guide.

## Config Files are Generated

- `.claude/settings.local.json` regenerates from DB on SessionStart
- NEVER manually edit it - changes will be overwritten
- To change permanently: update DB, run `sync_project.py`