---
projects:
- claude-family
tags:
- git
- workflow
- branching
- commits
synced: false
---

# Git Strategy

Standard git workflow for all Claude Family projects.

---

## Branch Strategy

**Main branch**: `master` or `main` (protected)

| Branch Type | Pattern | Purpose |
|------------|---------|---------|
| Feature | `feature/F<code>-<desc>` | New features |
| Fix | `fix/FB<code>-<desc>` | Bug fixes |
| Task | `task/BT<code>-<desc>` | Build tasks |
| Hotfix | `hotfix/<desc>` | Urgent production fixes |

**Examples:**
- `feature/F12-dark-mode`
- `fix/FB3-login-timeout`
- `task/BT45-refactor-api`

---

## Commit Messages

Format: `[WORK_ITEM] <type>: <description>`

**Types:** feat, fix, docs, chore, refactor, test, style

**Examples:**
```
[F12] feat: Add dark mode toggle
[FB3] fix: Increase login timeout to 30s
chore: Update dependencies
```

Hooks auto-prepend work item from branch name.

---

## Git Hooks

Located in `.githooks/` (version controlled).

| Hook | Purpose |
|------|---------|
| prepare-commit-msg | Auto-prepend [F1] from branch |
| commit-msg | Warn if no work item (soft) |

**Enable:** `git config core.hooksPath .githooks`

SessionStart hook auto-configures this.

---

## Workflow

1. Create work item in database (get short code F1, FB1, BT1)
2. Create branch: `git checkout -b feature/F1-description`
3. Make commits (hook adds [F1] prefix)
4. Push and create PR
5. Merge to main after review

---

## Best Practices

- **Atomic commits**: One logical change per commit
- **Link work items**: Use branch naming for automatic linking
- **No force push to main**: Protected branch
- **Rebase before merge**: Keep history clean
- **Delete merged branches**: Keep repo tidy

---

## Quick Commands

```bash
# Create feature branch
git checkout -b feature/F1-my-feature

# Check current branch work item
git symbolic-ref --short HEAD | grep -oE '[A-Z]+[0-9]+'

# View commits for work item
git log --oneline --grep='\[F1\]'

# Enable hooks for new clone
git config core.hooksPath .githooks
```

---

## Related

- [[Work Tracking Git Integration]] - Hook details
- [[Work Tracking Schema]] - Database schema

---

**Version**: 1.0
**Created**: 2026-01-03
**Updated**: 2026-01-03
**Location**: knowledge-vault/40-Procedures/Git Strategy.md
