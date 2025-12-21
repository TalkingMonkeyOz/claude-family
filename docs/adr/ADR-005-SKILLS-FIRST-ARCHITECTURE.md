# ADR-005: Skills-First Architecture

**Status**: Implemented
**Date**: 2025-12-21
**Context**: Claude Governance System Simplification

---

## Context

The current Claude Family system has accumulated complexity:

- **32 processes** in `process_registry` (now 25 after archiving 7)
- **process_router.py** runs on every `UserPromptSubmit`, doing keyword matching
- **6 skills** defined but underutilized (~20% baseline activation)
- **7 hook types** with **11 scripts** - some overlap

This creates:
1. **Latency**: Every prompt triggers process matching
2. **Confusion**: Overlapping concepts (processes, skills, commands, hooks)
3. **Low ROI**: Complex routing for workflows that rarely trigger

### Usage Data (Dec 8-21, 756 classifications)

| Tier | Trigger Count | Processes |
|------|--------------|-----------|
| High (50+) | 50-155 | 7 processes |
| Medium (20-50) | 20-50 | 8 processes |
| Low (1-20) | 1-20 | 15 processes |
| Never | 0 | 2 processes |

**Finding**: 47% of processes triggered <10 times in 2 weeks.

---

## Decision

Migrate from **Process Router** to **Skills-First** architecture:

### Layer Separation

| Layer | Purpose | Mechanism |
|-------|---------|-----------|
| **Skills** | Domain expertise (HOW) | Model-invoked via Skill tool |
| **Hooks** | Enforcement (MUST/CANNOT) | Pre/Post tool validation |
| **Commands** | User entry points | Slash commands → Skills |

### Deprecate

- `process_router.py` - Remove UserPromptSubmit hook
- `process_registry` table - Archive, don't query
- 32 process workflows - Consolidate into 8-10 skills

### Keep

- PreToolUse hooks (validation)
- SessionStart/End hooks (lifecycle)
- PreCommit hooks (quality gates)

---

## Core Skills (Target: 8-10)

Based on usage data, consolidate into:

| Skill | Replaces Processes | Trigger |
|-------|-------------------|---------|
| **database-operations** | DB Write Validation, Data Quality | SQL writes |
| **session-management** | Session Start/End/Resume/Commit | Session lifecycle |
| **work-routing** | Feedback, Work Item, Feature Impl | Creating work items |
| **code-review** | Code Review, Testing, Pre-Commit | Code changes |
| **doc-keeper** | Doc Creation/Staleness/Update, ADR | Doc operations |
| **agent-orchestration** | Agent Spawn, Parallel Dev | Multi-agent work |
| **project-ops** | Init, Retrofit, Phase, Compliance | Project setup |
| **messaging** | Message Check, Broadcast, Team Status | Inter-Claude comms |

Additional domain skills (project-specific):
- **nimbus-api** - Nimbus REST patterns
- **winforms** - WinForms/C# patterns

---

## Forced Evaluation Hook

To ensure skills are consistently considered, add a lightweight evaluation hook:

```python
# .claude/hooks.json - UserPromptSubmit
{
  "type": "prompt",
  "prompt": "Before responding, evaluate if any of these skills should be activated:\n- database-operations (SQL writes)\n- work-routing (creating feedback/features/tasks)\n- code-review (before commits)\n- session-management (session start/end)\nIf applicable, invoke the Skill tool."
}
```

This achieves ~84% skill activation (vs 20% baseline) based on research.

---

## Migration Plan

### Phase 1: Compact (DONE)
- [x] Archive 7 unused/rarely-used processes
- [x] Clean test data from feedback table
- [x] Document current state

### Phase 2: Skill Definition
- [ ] Define 8 core skills with clear triggers
- [ ] Write skill markdown files
- [ ] Add to .claude/skills/

### Phase 3: Hook Transition
- [ ] Add forced-eval prompt hook
- [ ] Monitor skill activation rates
- [ ] Remove process_router.py from UserPromptSubmit

### Phase 4: Cleanup
- [ ] Archive process_registry table
- [ ] Remove unused hook scripts
- [ ] Update CLAUDE.md documentation

---

## Consequences

### Positive
- Simpler mental model (Skills = domain knowledge)
- Lower latency (no keyword matching on every prompt)
- Better activation (forced eval achieves 84%)
- Easier maintenance (8 skills vs 32 processes)

### Negative
- Migration effort required
- Some edge-case processes may be lost
- Need to monitor activation rates

### Neutral
- Skills still need to be invoked (not automatic)
- Hooks remain for enforcement

---

## Metrics

Track post-migration:
1. **Skill activation rate** - Target: 80%+
2. **False negative rate** - Skills that should fire but don't
3. **Latency improvement** - Measure prompt processing time

---

**Version**: 1.0
**Author**: Claude (claude-family session)
