---
projects:
- claude-family
- trading-intelligence
- nimbus-mui
- monash-nimbus-reports
tags:
- coding-intelligence
- workfile
- context-engineering
- workflow
---

# Workfile Usage Guide (Coding Intelligence)

## What Is a Workfile?

A **workfile** is a component-scoped working context that aggregates everything you need before coding:
- **Module structure** — symbols in each file (from CKG)
- **Related code** — similar implementations across the project
- **Decisions** — past choices about this area (from memory)
- **Patterns** — reusable approaches and gotchas
- **Standards** — language-specific coding rules

One `unstash(component)` call loads all of this. No need to invoke 5 separate tools.

## When to Use

| Scenario | Action |
|----------|--------|
| Starting work on 2+ files | `populate_dossier(component, files)` |
| Resuming work on a component | `unstash(component)` |
| Before a medium/large task | Research phase → populate workfile → plan |
| Checking for existing patterns | `search_workfiles(query)` |

**Skip for**: Single-line fixes, typos, documentation-only changes.

## How to Create

### Automatic (Recommended)

```python
from scripts.dossier_auto_populate import populate_dossier

result = populate_dossier(
    component="auth-flow",
    project_name="claude-family",
    files=["src/auth.py", "src/middleware.py"],
    query="authentication middleware"
)
```

### Manual (Quick Notes)

```
stash("auth-flow", "design notes", "JWT tokens stored in httpOnly cookies...")
```

### Via Skill

Load the `/coding-intelligence` skill, which guides you through the workflow.

## Three Worked Examples

### Small Task: Fix a Bug in config.py

```
1. find_symbol("load_config") → found in scripts/config.py:23
2. check_collision("load_all_env_files") → no collision
3. populate_dossier("config-fix", files=["scripts/config.py"])
4. unstash("config-fix") → shows workfile: Python standards, 2 related config functions
5. Fix the bug following existing patterns
```

### Medium Task: Add Caching to API

```
1. Research: get_dependency_graph("api_handler") → 5 callers
2. Research: recall_memories("caching") → found Redis decision from last month
3. Research: find_similar("cache") → 3 existing cache implementations
4. Plan: Write 7 points (cache key strategy, TTL, invalidation, error handling)
5. populate_dossier("api-caching", files=["src/api.py", "src/cache.py", "src/redis.py"])
6. Implement following plan + workfile patterns
7. Review: check workfile — did we match existing cache pattern?
```

### Large Task: Refactor State Management

```
1. Structured Autonomy triggers (3+ files)
2. Analyst agent receives populated workfile as context
3. Analyst produces implementation specs per file
4. Coder agent implements each spec, referencing workfile
5. Reviewer checks against workfile standards
```

## Best Practices

- **Name components descriptively**: `auth-flow` not `fix-123`
- **Include all affected files** in `populate_dossier()` — CKG needs them
- **Add your own notes**: `stash(component, "my-findings", content)` alongside auto-populated workfile
- **Reference in commits**: `feat: [F156] Add caching — see workfile/api-caching`
- **Pin important workfiles**: Set `is_pinned=True` so they appear at session start

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Workfile empty | Files not indexed in CKG — run `index_codebase(project)` |
| No standards shown | File extension not mapped — check `gather_standards_context()` |
| Old data | Re-run `populate_dossier()` — it merges fresh data |
| Notes lost | Use `preserve_notes=True` (default) when re-populating |

---
**Version**: 1.1
**Created**: 2026-03-21
**Updated**: 2026-03-22
**Location**: 40-Procedures/dossier-usage-guide.md
