---
name: sa-plan
description: "Structured Autonomy Phase 1 â€” research codebase and create a structured implementation plan for a feature"
user-invocable: true
disable-model-invocation: true
---

# Structured Autonomy: Create Feature Plan

**Phase**: Planning
**Usage**: `/sa-plan {feature-name}`

Example: `/sa-plan dark-mode-toggle` creates `plans/dark-mode-toggle/plan.md`

---

## Overview

Phase 1 of the **Structured Autonomy Workflow** - research and planning for cost-effective feature development.

**Pattern**: Plan -> Generate -> Implement (73% cheaper than all-premium approach)

See: `knowledge-vault/30-Patterns/workflows/Structured Autonomy Workflow.md`

---

## Step 1: Parse Feature Name

Extract from command argument or prompt user if missing.
**Normalization**: lowercase, spaces to hyphens (e.g., "Dark Mode" -> "dark-mode")

## Step 2: Research Codebase

Spawn analyst-sonnet using the native Task tool to research: existing patterns, key files, dependencies, code examples, tech stack conventions.

Save the output for plan population.

## Step 3: Write Plan File

Use Write tool (NOT bash) with the plan template:

```python
Write(
    file_path=f"C:/Projects/{project_name}/plans/{feature_name}/plan.md",
    content=populated_plan_content
)
```

**Plan sections**:
- Requirements (Functional + Non-Functional)
- Current State Analysis (Patterns, Architecture, Dependencies)
- Implementation Strategy (Approach + numbered Steps)
- Files Affected (table: path, status, notes)
- Risks & Mitigations (table)
- Dependencies & Prerequisites
- Verification Checklist
- Success Criteria + Rollback Plan

## Step 4: Verify Creation

Use Read tool (NOT bash) to verify the file was created.

## Step 5: Display Summary

Show: step count, files affected, key technologies, complexity, and next command (`/sa-generate`).

---

## Plan Template

See the full template structure below for populating plan files:

- Feature Plan header with status, date, project
- Functional and Non-Functional Requirements
- Existing Patterns and Key Architecture Decisions
- High-Level Approach with numbered Implementation Steps
- Files Affected table (path, CREATE/MODIFY, notes)
- Risks & Mitigations table
- Verification Checklist and Success Criteria
- Rollback Plan

## Quality Checklist

- Be specific in agent task (tech stack, similar features)
- Request code examples, not just descriptions
- Steps must be actionable with specific file paths
- Logical order respecting dependencies
- Clear verification for each step

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Missing feature name | Prompt: "What feature would you like to plan?" |
| Plan already exists | Ask: "Overwrite, Skip to /sa-generate, or Cancel?" |
| Research agent fails | Offer: Retry, try coder-haiku, manual research, or cancel |

---

## Related Commands

- `/sa-generate {feature-name}` - Phase 2: Generate implementation specs
- `/sa-implement {feature-name}` - Phase 3: Execute implementation

**Reference**: `knowledge-vault/30-Patterns/workflows/Structured Autonomy Workflow.md`

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/sa-plan/SKILL.md
