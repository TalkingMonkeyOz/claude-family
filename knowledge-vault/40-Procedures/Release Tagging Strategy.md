---
projects:
- claude-family
tags:
- git
- releases
- versioning
- deployment
synced: false
---

# Release Tagging Strategy

Semantic versioning and release workflow.

---

## Version Format

`vMAJOR.MINOR.PATCH` (e.g., v1.2.3)

| Component | When to Increment |
|-----------|-------------------|
| MAJOR | Breaking changes |
| MINOR | New features (backward compatible) |
| PATCH | Bug fixes, small changes |

---

## Pre-release Tags

For testing before official release:

- `v1.2.3-alpha.1` - Early testing
- `v1.2.3-beta.1` - Feature complete, testing
- `v1.2.3-rc.1` - Release candidate

---

## Creating Releases

```bash
# Tag the release
git tag -a v1.2.0 -m "Release v1.2.0: Dark mode feature"

# Push tag
git push origin v1.2.0

# Create GitHub release (includes notes)
gh release create v1.2.0 --title "v1.2.0" --notes "## Changes
- Added dark mode toggle [F12]
- Fixed login timeout [FB3]"
```

---

## Release Checklist

1. [ ] All tests passing
2. [ ] Version bumped in package.json/csproj
3. [ ] CHANGELOG updated
4. [ ] Create git tag
5. [ ] Push tag
6. [ ] Create GitHub release
7. [ ] Log release in database

---

## Database Logging

```sql
-- Log release
INSERT INTO claude.releases (
    project_id, version, release_date, notes, created_by_session_id
) VALUES (
    'PROJECT_UUID', 'v1.2.0', now(),
    'Dark mode feature, login fix',
    'SESSION_UUID'
);
```

---

## Related

- [[Git Strategy]] - Branch workflow
- [[Work Tracking Schema]] - Linking to work items

---

**Version**: 1.0
**Created**: 2026-01-03
**Updated**: 2026-01-03
**Location**: knowledge-vault/40-Procedures/Release Tagging Strategy.md
