---
projects:
  - claude-family
tags:
  - orchestration
  - workflow
  - agents
  - patterns
synced: false
---

# Structured Autonomy Workflow

**Purpose**: A 3-phase workflow pattern for efficient feature development using agent orchestration.

**Source**: Adapted from [GitHub Copilot's Structured Autonomy](https://github.com/github/awesome-copilot/tree/main/collections/structured-autonomy)

---

## Core Principle

> "Use premium models sparingly for thinking, use cheap models liberally for doing."

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     PLAN        │ ──▶ │    GENERATE     │ ──▶ │   IMPLEMENT     │
│  (1 request)    │     │   (1 request)   │     │  (many agents)  │
│  Premium Model  │     │  Premium Model  │     │   Cheap Models  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## The Workflow

### Phase 1: Plan (Opus/Sonnet - expensive, one-time)

**Who**: Me (Opus) or planner-sonnet
**What**: Research codebase, understand requirements, break into steps
**Output**: `plans/{feature}/plan.md`

```markdown
## Feature: Dark Mode Toggle

### Requirements
- User can toggle between light/dark themes
- Preference persists across sessions

### Implementation Steps
1. Add theme context provider
2. Create toggle component
3. Update styles with CSS variables
4. Persist preference to localStorage

### Files Affected
- src/contexts/ThemeContext.tsx (CREATE)
- src/components/ThemeToggle.tsx (CREATE)
- src/styles/theme.css (MODIFY)
- src/App.tsx (MODIFY)
```

### Phase 2: Generate (Opus/Sonnet - expensive, one-time)

**Who**: Me (Opus) or analyst-sonnet
**What**: Convert plan to detailed implementation specs
**Output**: `plans/{feature}/implementation.md`

```markdown
## Step 1: Create ThemeContext

### File: src/contexts/ThemeContext.tsx
[Full code block with no placeholders]

### Verification
- [ ] File created at correct path
- [ ] Context exports useTheme hook
- [ ] TypeScript compiles without errors

---

## Step 2: Create ThemeToggle Component
...
```

### Phase 3: Implement (Haiku/Sonnet - cheap, many iterations)

**Who**: coder-haiku, mui-coder-sonnet, tester-haiku
**What**: Execute each step, verify, commit
**Pattern**: Spawn agent per step, verify before next

```
For each step in implementation.md:
  1. Spawn appropriate coder agent
  2. Execute step
  3. Run verification checks
  4. If tests pass → commit
  5. If tests fail → fix and retry
```

---

## Claude Family Implementation

### Using Existing Infrastructure

| Phase | Claude Family Equivalent |
|-------|--------------------------|
| Plan | Task(Plan) agent or EnterPlanMode |
| Generate | Me (Opus) with structured output |
| Implement | spawn_agent(coder-haiku/sonnet) per step |
| Review | spawn_agent(reviewer-sonnet) before commit |
| Test | spawn_agent(tester-haiku) per commit |

### Workflow Commands (Optional)

These could be created as slash commands:

| Command | Phase | Action |
|---------|-------|--------|
| `/sa-plan {feature}` | Plan | Research + create plan.md |
| `/sa-generate` | Generate | Create implementation.md from plan |
| `/sa-implement` | Implement | Spawn agents for each step |

---

## Cost Comparison

| Approach | 10-file Feature Cost |
|----------|---------------------|
| All Opus (no delegation) | ~$4.00 |
| Structured Autonomy | ~$1.10 |
| **Savings** | **~73%** |

Breakdown:
- Plan phase (Opus): $0.30
- Generate phase (Opus): $0.30
- Implement (8 × Haiku): $0.28
- Review (Sonnet): $0.15
- Tests (Haiku): $0.10

---

## When to Use This Pattern

**Good for:**
- New features (3+ files)
- Refactoring efforts
- Multi-step implementations
- Tasks with clear commit boundaries

**Not for:**
- Bug fixes (1-2 files)
- Quick changes
- Exploratory work
- Tasks requiring continuous context

---

## Integration with mandatory_workflows

All projects now have `delegation-awareness` in their `mandatory_workflows`. This reminds Claude to consider the Structured Autonomy pattern for significant work.

```sql
-- Check current project workflows
SELECT mandatory_workflows
FROM claude.workspaces
WHERE project_name = 'your-project';
```

---

## Related Documents

- [[Agent Selection Decision Tree]] - When to use which agent
- [[Orchestrator MCP]] - Spawning mechanics
- [[Family Rules]] - Coordination guidelines

---

**Version**: 1.0
**Created**: 2026-01-10
**Updated**: 2026-01-10
**Location**: knowledge-vault/30-Patterns/Structured Autonomy Workflow.md
