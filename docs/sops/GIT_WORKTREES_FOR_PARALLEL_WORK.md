# SOP: Git Worktrees for Parallel Work

**Version**: 1.0
**Created**: 2025-12-06
**Status**: Active

---

## Purpose

Enable multiple Claude instances to work on different features simultaneously in the same repository without conflicts. Git worktrees allow separate working directories that share the same git history.

---

## When to Use

| Scenario | Use Worktrees? |
|----------|----------------|
| Multiple Claude instances need to code on same repo | ✅ Yes |
| One instance writes code, another reviews | ✅ Yes |
| Quick fix needed while feature work in progress | ✅ Yes |
| Simple sequential tasks | ❌ No (overkill) |
| Different repositories | ❌ No (not needed) |

---

## Quick Reference

```bash
# Create worktree for feature branch
git worktree add ../project-feature-a feature-a

# Create worktree from new branch
git worktree add -b feature-b ../project-feature-b main

# List worktrees
git worktree list

# Remove worktree (after merging)
git worktree remove ../project-feature-a
```

---

## Setup Pattern

### 1. Main Repository Structure

```
C:\Projects\
├── myproject/           # Main worktree (main branch)
├── myproject-feature-a/ # Worktree for feature-a
├── myproject-feature-b/ # Worktree for feature-b
└── myproject-hotfix/    # Worktree for urgent fix
```

### 2. Create Worktree for New Feature

```bash
# From main repository
cd C:\Projects\myproject

# Create new branch and worktree
git worktree add -b feature/user-auth ../myproject-user-auth main
```

### 3. Claude Instance Assignment

| Claude Instance | Worktree | Task |
|-----------------|----------|------|
| claude-code-1 | myproject/ | Main development |
| claude-code-2 | myproject-user-auth/ | Implement auth feature |
| claude-code-3 | myproject-hotfix/ | Critical bug fix |

---

## Workflow

### Starting Parallel Work

```bash
# Instance 1: Create worktrees
git worktree add -b feature/api-v2 ../myproject-api-v2 main
git worktree add -b feature/ui-redesign ../myproject-ui-redesign main

# Instance 2: Work in api-v2 worktree
cd ../myproject-api-v2
# ... make changes, commit ...

# Instance 3: Work in ui-redesign worktree
cd ../myproject-ui-redesign
# ... make changes, commit ...
```

### Completing Work

```bash
# From main repo, merge completed feature
cd C:\Projects\myproject
git checkout main
git merge feature/api-v2

# Remove worktree after merge
git worktree remove ../myproject-api-v2

# Prune any stale worktrees
git worktree prune
```

---

## Integration with Orchestrator

When spawning agents for parallel work:

```python
# Coordinator creates worktrees before spawning
worktrees = [
    create_worktree("feature/api", workspace),
    create_worktree("feature/ui", workspace),
]

# Spawn agents to different worktrees
spawn_agent("coder-haiku", "Implement API", worktrees[0])
spawn_agent("coder-haiku", "Implement UI", worktrees[1])
```

---

## Rules

1. **Never work on same branch in multiple worktrees** - Git prevents this
2. **Keep worktrees short-lived** - Create, work, merge, remove
3. **Use descriptive worktree names** - Include feature name
4. **Clean up after merge** - `git worktree remove` and `git worktree prune`
5. **Don't nest worktrees** - Keep them as siblings

---

## Common Issues

### "fatal: 'feature-x' is already checked out"
Another worktree has this branch. List worktrees to find it:
```bash
git worktree list
```

### Orphaned worktree references
```bash
git worktree prune
```

### Worktree directory still exists after remove
Delete manually:
```bash
rm -rf ../myproject-old-feature
git worktree prune
```

---

## Related

- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices) - Multi-Claude workflows section
- `docs/adr/ADR-003-ASYNC-AGENT-WORKFLOW.md` - Async agent coordination

---

**Maintained by**: Claude Family Infrastructure
