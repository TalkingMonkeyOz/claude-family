# Structured Autonomy: Create Feature Plan

**Phase**: Planning
**Purpose**: Research codebase and create a structured implementation plan for a feature.
**Usage**: `/sa-plan {feature-name}`

Example: `/sa-plan dark-mode-toggle` creates `plans/dark-mode-toggle/plan.md`

---

## Overview

This command initiates Phase 1 of the **Structured Autonomy Workflow** - an efficient pattern for feature development using agent orchestration.

**Pattern**:
1. **Plan** (this command) - Research + understand → `plan.md`
2. **Generate** - Convert plan to specs → `implementation.md`
3. **Implement** - Execute steps with cheap agents → commits

**Cost benefit**: 73% cheaper than all-premium-model approach.

See: `knowledge-vault/30-Patterns/Structured Autonomy Workflow.md`

---

## Step 1: Parse Feature Name

Extract the feature name from the command argument:

```
Command: /sa-plan dark-mode-toggle
Feature name: dark-mode-toggle
Feature directory: plans/dark-mode-toggle/
```

If no argument provided, ask the user: "What feature would you like to plan? (e.g., `dark-mode-toggle`, `user-authentication`)"

---

## Step 2: Research Codebase

Use the **Task tool with Explore agent** OR **orchestrator's analyst-sonnet** to research the codebase:

**Option A - Task Tool (Built-in, no MCP needed):**
```python
Task(
    subagent_type="Explore",
    description="Research codebase for {feature-name}",
    prompt="""Thoroughly research {feature-name} implementation:

1. Find existing patterns (similar features, architecture, testing)
2. Identify key files and structure (entry points, components, state)
3. Document dependencies (UI libs, state management, styling, testing)
4. Find relevant code examples to follow

Thoroughness: "very thorough"
"""
)
```

**Option B - Orchestrator MCP (for DB/vault access):**
```python
mcp__orchestrator__spawn_agent(
    agent_type="analyst-sonnet",
    task="Research codebase patterns for {feature-name}. Find existing patterns, architecture, dependencies, and relevant code examples.",
    workspace_dir="C:/Projects/{project-name}"
)
```

**Save the output** - this becomes research context for the plan.

---

## Step 3: Write Plan Document

Use the **Write tool** to create the plan file (it auto-creates directories):

```python
Write(
    file_path="plans/{feature-name}/plan.md",
    content="<plan content below>"
)
```

---

## Step 4: Plan Template

Generate `plans/{feature-name}/plan.md` with this structure:

```markdown
# Feature Plan: {Feature Name}

**Status**: Draft
**Created**: {Today's date}
**Codebase**: {Brief description of current state}

---

## Requirements

### Functional Requirements
- Requirement 1
- Requirement 2
- Requirement 3

### Non-Functional Requirements
- Performance requirement
- Accessibility requirement
- Browser/platform support

---

## Current State Analysis

### Existing Patterns
- Pattern 1: {Where it's used, example code snippet}
- Pattern 2: {Where it's used, example code snippet}

### Key Architecture Decisions
- Technology choices (framework, libraries)
- State management approach
- Styling strategy
- Testing approach

### Relevant Dependencies
- List of installed packages relevant to this feature
- Version constraints if important

---

## Implementation Strategy

### High-Level Approach
{2-3 sentences describing the strategy}

### Implementation Steps

#### Step 1: {Clear, actionable step title}
- Files affected: `file1.ts`, `file2.tsx` (CREATE/MODIFY)
- Dependencies: Any other steps that must complete first
- Key decisions: Architecture choices specific to this step

#### Step 2: {Next step}
- Files affected: ...
- Dependencies: ...

#### Step 3: {Continue pattern}
...

---

## Files Affected

| File | Status | Notes |
|------|--------|-------|
| `src/path/file1.tsx` | CREATE | New component |
| `src/path/file2.css` | MODIFY | Add theme variables |
| `src/index.tsx` | MODIFY | Wire up provider |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Risk 1 | High/Medium/Low | How to prevent/handle |
| Risk 2 | ... | ... |

---

## Verification Checklist

- [ ] All files in "Files Affected" exist or are created
- [ ] No TypeScript/compilation errors
- [ ] Feature works in development
- [ ] Existing tests still pass
- [ ] Feature is accessible (a11y)
- [ ] Performance is acceptable (if applicable)
- [ ] Browser compatibility verified (if applicable)

---

**Next Phase**: Run `/sa-generate` to create detailed implementation specs from this plan.
```

---

## Step 5: Populate Plan with Research

Use the Explore agent output to populate sections:

1. **Functional Requirements**: Based on feature description and patterns found
2. **Current State Analysis**: From Explore output
3. **Implementation Strategy**: Combine found patterns with new requirements
4. **Files Affected**: List all files the Explore agent discovered + files to create
5. **Risks**: Think through potential complications

---

## Step 6: Verify and Display

After creating the plan:

1. **Verify file exists** using Read tool or Glob:
   ```python
   Read(file_path="plans/{feature-name}/plan.md", limit=10)  # Check first 10 lines
   ```

2. **Display summary to user**:
   ```
   ✅ Feature Plan Created: {feature-name}

   📁 Location: plans/{feature-name}/plan.md

   📋 Summary:
   - {Number} implementation steps
   - {Number} files affected
   - Key technologies: {list}

   🔍 Research used {Agent type} to analyze {N} files and {N} patterns

   ➡️  Next: Run `/sa-generate` to create detailed implementation specs
   ```

---

## Error Handling

**If feature name missing:**
- Prompt user for feature name
- Accept kebab-case or space-separated input
- Convert to kebab-case internally

**If plan directory already exists:**
- Confirm with user: "Plan already exists at `plans/{feature-name}/plan.md`. Overwrite? (yes/no)"
- If yes → overwrite with new research
- If no → show current plan and ask if they want `/sa-generate` instead

**If Explore agent fails:**
- Display: "⚠️ Failed to research codebase: {error}"
- Offer to try again or proceed with manual planning
- Allow user to provide additional context

**If no relevant patterns found:**
- Note in plan: "No existing similar features found. Using standard patterns for this technology stack."
- Continue with standard approach for the tech

---

## Tips for Effective Plans

1. **Be specific about files** - Don't guess; use Explore findings
2. **Link to existing patterns** - Reference what already exists
3. **Identify boundaries** - Each step should be a separate commit
4. **Think about tests** - What tests will verify each step?
5. **Consider rollback** - Can each step be reverted independently?

---

## Related Commands

- `/sa-generate` - Phase 2: Generate implementation specs from plan
- `/sa-implement` - Phase 3: Execute implementation with agents
- `/todo` - Track tasks during implementation

**Reference**: See `knowledge-vault/30-Patterns/Structured Autonomy Workflow.md` for full pattern details.

---

**Version**: 1.0
**Created**: 2026-01-10
**Updated**: 2026-01-10
**Location**: .claude/commands/sa-plan.md
