---
projects:
  - claude-family
  - claude-manager-mui
tags:
  - sop
  - configuration
  - rollback
  - recovery
synced: false
---

# Config Rollback SOP

**Purpose**: Recovery procedures when configuration changes go wrong.

---

## Quick Reference

| Scenario | Action |
|----------|--------|
| Bad file change | Restore from `.bak` file |
| Bad database change | Revert to previous version |
| Full disaster | Restore from backup folder |

---

## Scenario 1: Restore File from Backup

**When**: CLAUDE.md or settings.local.json was overwritten incorrectly

### Step 1: Find the backup

```bash
# Backup files are created as .bak
ls -la {project_path}/CLAUDE.md.bak
ls -la {project_path}/.claude/settings.local.json.bak

# Or timestamped backups from bulk operations
ls -la {project_path}/CLAUDE.md.backup-*
```

### Step 2: Restore the file

```bash
# Simple restore
cp CLAUDE.md.bak CLAUDE.md

# Or from timestamped backup
cp CLAUDE.md.backup-20260111-143022 CLAUDE.md
```

### Step 3: Verify

```bash
# Check content is correct
head -20 CLAUDE.md
```

---

## Scenario 2: Revert Database Profile Version

**When**: Profile was updated with bad config in the database

### Option A: Via Claude Manager UI

1. Open Claude Manager
2. Go to **Configuration**
3. Select the affected profile
4. Click **Versions** tab
5. Find the previous good version
6. Click **Revert**

### Option B: Via SQL

```sql
-- Find the profile and its versions
SELECT profile_id, name, current_version
FROM claude.profiles
WHERE name = 'project-name';

-- List versions
SELECT version_id, version, created_at, notes
FROM claude.profile_versions
WHERE profile_id = 'your-profile-id'
ORDER BY version DESC;

-- Revert to specific version
SELECT revert_profile_to_version('profile-uuid', 2);
```

### Option C: Via API

```typescript
await api.revertProfile(profileId, targetVersion);
```

---

## Scenario 3: Full Disaster Recovery

**When**: Multiple files and database are corrupted

### Step 1: Stop all Claude sessions

Close any running Claude Code instances.

### Step 2: Restore files from backup folder

Bulk backups are stored in timestamped folders:

```bash
# List backup folders
ls -la C:\Projects\claude-family\backups\

# Restore specific project
cp -r backups/20260111-143022/claude-family/* C:\Projects\claude-family\
```

### Step 3: Reset database profiles

```sql
-- Delete bad profiles (created after migration)
DELETE FROM claude.profile_versions
WHERE created_at > '2026-01-11 14:30:00';

DELETE FROM claude.profiles
WHERE created_at > '2026-01-11 14:30:00';
```

### Step 4: Re-import from restored files

```bash
python scripts/import_profiles_from_projects.py
```

---

## Backup Locations

| Type | Location |
|------|----------|
| Per-file backup | `{project_path}/CLAUDE.md.bak` |
| Timestamped backup | `{project_path}/CLAUDE.md.backup-{timestamp}` |
| Bulk backup folder | `C:\Projects\claude-family\backups\{timestamp}\` |
| Database versions | `claude.profile_versions` table |

---

## Prevention

1. **Always backup before bulk operations**
   ```bash
   python scripts/backup_claude_configs.py
   ```

2. **Review changes before applying**
   - Use "Preview" in Profile Editor
   - Check diff before "Apply to Project"

3. **Use version notes**
   - When saving profiles, add meaningful notes
   - Makes it easier to identify good versions later

---

## Emergency Contacts

If you cannot recover:

1. Check git history for file content
   ```bash
   git log --oneline -- CLAUDE.md
   git show HEAD~1:CLAUDE.md
   ```

2. Check database transaction logs (if available)

3. Manual reconstruction from knowledge vault documentation

---

## Related Documents

- [[Centralized Config SOP]] - Normal operation procedures
- [[Config Management SOP]] - Legacy config details

---

**Version**: 1.0
**Created**: 2026-01-11
**Updated**: 2026-01-11
**Location**: knowledge-vault/40-Procedures/Config Rollback SOP.md
