---
name: coding-intelligence
description: "Coding Intelligence — Research / Plan / Implement using CKG, workfiles, and standards injection"
user-invocable: true
---

# Coding Intelligence — Research / Plan / Implement

**Status**: Active | **Feature**: F156

## Overview

Routes coding tasks through the appropriate workflow intensity based on file count and complexity. Auto-populates a workfile from CKG, memory, and coding standards before implementation begins.

## When to Use

- Before starting any coding task involving 2+ files
- When you want context about existing patterns before writing code
- User says: "prep for", "research first", "what exists for", "coding prep"

**Skip for**: Single-line fixes, typos, config changes, documentation-only changes.

## Three Workflow Intensities

### Small (1 file)
1. Run `find_symbol(query)` and `check_collision(name)` for the main function/class
2. Call `populate_dossier(component, files=[file])` to gather context
3. Review workfile — check for similar implementations, apply standards
4. Implement

### Medium (2-3 files)
1. **Research**: `get_dependency_graph(symbol_id)`, `recall_memories(query)`, `find_similar(symbol_id)`
2. **Plan**: Write 5-10 point plan: what changes in each file, where state lives, edge cases
3. **Workfile**: `populate_dossier(component, files=[...], query=task_description)`
4. **Implement**: Follow plan, reference workfile for patterns/standards
5. **Review**: Check against workfile — did we follow existing patterns?

### Large (3+ files or high complexity)
1. Spawn analyst-sonnet to research codebase patterns
2. Analyst produces implementation specs per file
3. Spawn coder-sonnet (complex) or coder-haiku (simple) per step
4. Spawn reviewer-sonnet before commit
5. Each agent receives populated workfile as context

## Workfile Auto-Population

```python
from scripts.dossier_auto_populate import populate_dossier
result = populate_dossier(component="auth-flow", project_name="claude-family",
                          files=["src/auth.py", "src/middleware.py"],
                          query="authentication middleware")
```

Populates: Module Structure, Related Symbols, Similar Implementations, Relevant Decisions, Relevant Patterns, Applicable Standards.

Read with: `unstash(component)`

## Quick Reference

| Step | Tool | Purpose |
|------|------|---------|
| Find symbols | `find_symbol(query)` | Name-based + semantic search |
| Check naming | `check_collision(name)` | Avoid duplicate names |
| File structure | `get_module_map(file_path)` | All symbols in a file |
| Similar code | `find_similar(symbol_id)` | Find duplicate patterns |
| Dependencies | `get_dependency_graph(symbol_id)` | What calls what |
| Populate workfile | `populate_dossier(component, files)` | Auto-gather all context |
| Read workfile | `unstash(component)` | Load assembled context |

## BPMN Process

Modeled in: `coding-intelligence-workflow.bpmn`