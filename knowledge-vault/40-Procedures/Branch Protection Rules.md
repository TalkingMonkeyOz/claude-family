---
projects:
- claude-family
tags:
- git
- github
- security
- workflow
synced: false
---

# Branch Protection Rules

GitHub branch protection settings for Claude Family projects.

---

## Recommended Settings (Main Branch)

Apply to `master` or `main`:

| Setting | Value | Purpose |
|---------|-------|---------|
| Require PR before merging | Yes | No direct pushes |
| Required approvals | 0-1 | Solo projects: 0, Team: 1+ |
| Dismiss stale approvals | Yes | Re-review after changes |
| Require status checks | Optional | If CI configured |
| Require branches up to date | Yes | Prevents merge conflicts |
| Include administrators | Yes | Everyone follows rules |

---

## GitHub CLI Setup

```bash
# Enable branch protection via gh cli
gh api repos/{owner}/{repo}/branches/master/protection \
  -X PUT \
  -F required_pull_request_reviews='{"required_approving_review_count":0}' \
  -F enforce_admins=true \
  -F restrictions=null \
  -F required_status_checks=null
```

---

## Manual Setup

1. Go to repo Settings > Branches
2. Add rule for `master` or `main`
3. Check "Require a pull request before merging"
4. Check "Include administrators"
5. Save changes

---

## Project-Specific Rules

| Project Type | Approvals | Status Checks |
|--------------|-----------|---------------|
| infrastructure | 0 | None |
| application | 0-1 | Build, lint |
| web | 0-1 | Build, lint, test |

---

## Related

- [[Git Strategy]] - Overall workflow
- [[Work Tracking Git Integration]] - Commit hooks

---

**Version**: 1.0
**Created**: 2026-01-03
**Updated**: 2026-01-03
**Location**: knowledge-vault/40-Procedures/Branch Protection Rules.md
