---
name: git-workflow
description: "Git ops following Claude Family conventions: commits, branches, PRs, pre-commit checks"
scope: global
user-invocable: true
---

# Git Workflow Skill (Draft)

Enforces Claude Family git conventions. Bakes in `commit-rules.md` as domain knowledge.

**Use for:** Commits, branches, PRs, pre-commit checks.
**Don't use for:** Session-end commits (`/session-commit`), code review (`/code-review`).

## Quick Reference

```
COMMIT:   <type>: <description> [ITEM]
BRANCH:   feature/F1-desc | fix/FB1-desc | task/BT1-desc
TYPES:    feat | fix | refactor | docs | chore | test
```

## Commit Format

```
<type>: <short description> [ITEM_CODE]
[optional body]
Co-Authored-By: Claude <model> <noreply@anthropic.com>
```

Use HEREDOC for multi-line: `git commit -m "$(cat <<'EOF' ... EOF)"`

**Choosing type:** "If I revert, what is lost?" Capability=`feat`, broken fix=`fix`, invisible=`refactor`/`chore`/`docs`/`test`.

## Branch Naming

| Work Item | Pattern | Example |
|-----------|---------|---------|
| Feature | `feature/F{n}-kebab` | `feature/F12-dark-mode` |
| Bug | `fix/FB{n}-kebab` | `fix/FB45-login-redirect` |
| Task | `task/BT{n}-kebab` | `task/BT23-auth-middleware` |

Always branch from `master`. One branch per work item.

## PR Creation

```bash
gh pr create --title "<type>: <desc> [ITEM]" --body "$(cat <<'EOF'
## Summary
<1-3 bullets>
## Work Items
<F/FB/BT codes>
## Test plan
<checklist>
EOF
)"
```

## Pre-Commit Checks

1. Tests pass (if 3+ files changed)
2. Work item code in commit message
3. No secrets staged (`.env`, `.key`, `.pem`)
4. No debug artifacts (`console.log`, `debugger`)
5. Stage specific files, not `git add .`

## Safety (Non-Negotiable)

- Never force push to main/master
- Never skip hooks without explicit request
- Never commit secrets or credentials

## Anti-Patterns

| Don't | Do |
|-------|-----|
| `"fix stuff"` | `"fix: Null ref in auth [FB12]"` |
| `git add .` blindly | `git add src/auth.py` |
| Branch `john-branch` | `feature/F12-dark-mode` |
| Mix features per commit | One logical change per commit |
| `--no-verify` | Fix the hook, then commit |
| Amend to fix mistakes | New commit (preserves history) |

---

**Version**: 1.0
**Created**: 2026-03-18
**Updated**: 2026-03-18
**Location**: docs/git-workflow-skill-draft.md
