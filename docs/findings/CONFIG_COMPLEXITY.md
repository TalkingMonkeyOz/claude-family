# Configuration Complexity Analysis

**Analysis Type**: ULTRATHINK
**Date**: 2026-01-10

---

## The 10 Configuration Mechanisms

| # | Mechanism | Location | Purpose |
|---|-----------|----------|---------|
| 1 | Skills | `.claude/skills/` | Domain workflows (database-ops, testing) |
| 2 | Rules | `.claude/rules/` | Constraints (commit rules, DB rules) |
| 3 | Memory | MCP memory server | Persistent graph knowledge |
| 4 | Hooks | `settings.json` | Event handlers (SessionStart, PreToolUse) |
| 5 | MCPs | `settings.json` | External servers (postgres, orchestrator) |
| 6 | Settings | `settings.json` | Permissions, model config |
| 7 | Instructions | `.claude/instructions/` | File-pattern coding standards |
| 8 | Commands | `.claude/commands/` | Slash command definitions |
| 9 | Agents | `agent_specs.json` | Spawnable specialists |
| 10 | CLAUDE.md | Root | Project constitution |

---

## Overlap Analysis

**Commands vs Skills**: 60% overlap
- `/session-start` duplicates `session-management` skill
- `/feedback-create` duplicates `work-item-routing` skill

**Rules vs CLAUDE.md**: Some duplication
- Database rules in both places

**Instructions vs CLAUDE.md**: Different scope
- Instructions: File-pattern specific
- CLAUDE.md: Project-level guidance

---

## Root Cause

**Not Confusion - Evolution**: The system evolved organically. Each mechanism solved a real problem at the time.

**The Real Issue**: No clear guidance on WHEN to use each mechanism.

---

## Recommendations

### 1. Create Config Placement Guide

```markdown
## When to Use What

| I need to... | Use... |
|-------------|--------|
| Add coding standard for file type | `.claude/instructions/` |
| Create reusable workflow | `.claude/skills/` |
| Enforce a constraint | `.claude/rules/` |
| React to an event | Hooks in settings |
| Add external capability | MCP server |
| Define slash command | `.claude/commands/` |
| Set project context | CLAUDE.md |
```

### 2. Merge Commands into Skills

Phase out 6 commands that duplicate skills:
- `/session-start` → `session-management` skill
- `/session-end` → `session-management` skill
- `/feedback-create` → `work-item-routing` skill
- `/feedback-check` → `work-item-routing` skill
- `/feedback-list` → `work-item-routing` skill
- `/project-init` → `project-ops` skill

### 3. Slim CLAUDE.md

Move reference tables to vault, keep only:
- Project identity
- Current phase
- Key constraints
- Links to detailed docs

---

## Conclusion

The configuration is complex but purposeful. Each layer serves a distinct role. The solution is better documentation, not simplification.

---

**Version**: 1.0
**Created**: 2026-01-10
**Updated**: 2026-01-10
**Location**: docs/findings/CONFIG_COMPLEXITY.md
