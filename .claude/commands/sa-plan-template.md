# Feature Plan Template

Full plan template for `/sa-plan`. Copy and populate with research findings.

**Usage**: Referenced by `/sa-plan` — do not invoke directly.

---

## Plan File Structure

```markdown
# Feature Plan: {Feature Name}

**Status**: Draft
**Created**: {Today's date}
**Feature**: {feature-name}
**Project**: {project-name}
**Codebase**: {Brief description of current state}

---

## Requirements

### Functional Requirements
- Requirement 1
- Requirement 2

### Non-Functional Requirements
- Performance requirement
- Accessibility requirement
- Browser/platform support

---

## Current State Analysis

### Existing Patterns
- Pattern 1: {Where it's used, example snippet}
- Pattern 2: {Where it's used, example snippet}

### Key Architecture Decisions
- Technology choices (framework, libraries)
- State management approach
- Styling strategy
- Testing approach

### Relevant Dependencies
- Package name: purpose (version constraint if needed)

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

---

## Files Affected

| File | Status | Notes |
|------|--------|-------|
| `src/path/file1.tsx` | CREATE | New component |
| `src/path/file2.css` | MODIFY | Add theme variables |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Risk 1 | High/Medium/Low | How to prevent/handle |

---

## Dependencies & Prerequisites

- Prerequisite 1 (must be done before starting)
- Prerequisite 2

---

## Verification Checklist

- [ ] All files in "Files Affected" exist or are created
- [ ] No TypeScript/compilation errors
- [ ] Feature works in development
- [ ] Existing tests still pass
- [ ] Feature is accessible (a11y)
- [ ] Performance is acceptable

---

## Success Criteria

**Definition of Done**: {specific measurable criteria}

**Acceptance Test**: {how to verify it works end-to-end}

---

## Rollback Plan

{How to undo this feature if needed — e.g., revert commits, DB migrations to reverse}

---

**Next Phase**: Run `/sa-generate {feature-name}` to create detailed implementation specs.

---

**Version**: 1.0
**Created**: {date}
**Updated**: {date}
**Location**: plans/{feature-name}/plan.md
```

---

## Quality Checklist for Plans

**Effective Research**:
- Be specific in agent task (tech stack, similar features)
- Request code examples, not just descriptions
- Ask for conventions and patterns

**Quality Steps**:
- Actionable (clear enough to hand off to another agent)
- Specific files (exact paths, not "update components")
- Logical order (respects dependencies)
- Independent where possible (can be rolled back per step)
- Clear verification (how to know each step worked)

**Cost Optimization**:
- One comprehensive research pass with analyst-sonnet
- Reuse research output for `/sa-generate`

---

**Version**: 1.0
**Created**: 2026-02-28
**Updated**: 2026-02-28
**Location**: .claude/commands/sa-plan-template.md
