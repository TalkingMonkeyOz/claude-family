---
projects:
- claude-family
tags:
- git
- work-tracking
- hooks
- commits
synced: false
---

# Work Tracking Git Integration

Link git commits to work items via branch naming and hooks.

---

## Branch Naming Convention

```
feature/F<code>-<description>
fix/FB<code>-<description>
task/BT<code>-<description>
```

**Examples:**
- `feature/F1-dark-mode`
- `fix/FB3-login-timeout`
- `task/BT5-implement-api`

---

## Git Hooks

Store in `.githooks/` directory (version controlled).

### prepare-commit-msg

Auto-prepend work item reference from branch name:

```bash
#!/bin/bash
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
if [[ $BRANCH =~ ^(feature|fix|task)/([A-Z]+[0-9]+) ]]; then
    WORK_ITEM="${BASH_REMATCH[2]}"
    if ! grep -q "^\[$WORK_ITEM\]" "$1"; then
        sed -i.bak "1s/^/[$WORK_ITEM] /" "$1"
    fi
fi
```

### commit-msg

Validate work item exists (warning only, not blocking):

```bash
#!/bin/bash
MSG=$(cat "$1")
if ! echo "$MSG" | grep -qE '\[(F|FB|BT)[0-9]+\]'; then
    echo "Note: No work item reference found."
    echo "Consider using feature/F1-* branch naming."
fi
# Always exit 0 (soft enforcement)
```

---

## Deployment

SessionStart hook sets hooks path:

```python
subprocess.run(['git', 'config', 'core.hooksPath', '.githooks'], check=False)
```

Or manually: `git config core.hooksPath .githooks`

---

## Commit Format

```
[F1] Add theme toggle component

Implements dark mode toggle in settings panel.
Closes #123.
```

---

## Related

- [[Work Tracking Schema]] - Database schema
- [[Work Tracking Compliance Plan]] - Overview

---

**Version**: 1.0
**Created**: 2026-01-03
**Updated**: 2026-01-03
**Location**: knowledge-vault/20-Domains/Database/Work Tracking Git Integration.md
