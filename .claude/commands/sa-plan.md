# Structured Autonomy: Create Feature Plan

**Phase**: Planning
**Purpose**: Research codebase and create a structured implementation plan for a feature.
**Usage**: `/sa-plan {feature-name}`

Example: `/sa-plan dark-mode-toggle` creates `plans/dark-mode-toggle/plan.md`

---

## Overview

Phase 1 of the **Structured Autonomy Workflow** - research and planning for cost-effective feature development.

**Pattern**: Plan → Generate → Implement (73% cheaper than all-premium approach)

**Key practices**:
- Uses analyst-sonnet (better research, DB/vault access)
- Write tool for file creation (not bash mkdir/touch)
- Read tool for verification (not bash test/cat)

See: `knowledge-vault/30-Patterns/Structured Autonomy Workflow.md`

---

## Step 1: Parse Feature Name

Extract from command argument or prompt user if missing.

**Normalization**: lowercase, spaces → hyphens (e.g., "Dark Mode" → "dark-mode")

---

## Step 2: Research Codebase

Spawn analyst-sonnet using the native Task tool:

```python
Task(
    subagent_type="analyst-sonnet",
    description=f"Research codebase for {feature_name}",
    prompt=f"""Research codebase for {feature_name}:
1. Find existing patterns (similar features, architecture, testing)
2. Identify key files and structure (entry points, components, state)
3. Document dependencies (UI libs, state management, styling, testing)
4. Find code examples to follow
5. Identify technology stack and conventions

Provide comprehensive analysis with specific file paths and examples."""
)
```

Save the output — used to populate plan sections.

---

## Step 3: Write Plan File

Use Write tool (NOT bash) with the template from `sa-plan-template.md`:

```python
Write(
    file_path=f"C:/Projects/{project_name}/plans/{feature_name}/plan.md",
    content=populated_plan_content
)
```

**Do NOT use**: `mkdir`, `touch`, `echo >`, `cat <<EOF`

**Plan sections** (see `sa-plan-template.md` for full template):
- Requirements (Functional + Non-Functional)
- Current State Analysis (Patterns, Architecture, Dependencies)
- Implementation Strategy (Approach + numbered Steps)
- Files Affected (table: path, status, notes)
- Risks & Mitigations (table)
- Dependencies & Prerequisites
- Verification Checklist
- Success Criteria + Rollback Plan

---

## Step 4: Verify Creation

Use Read tool (NOT bash test/cat):

```python
Read(file_path=f"C:/Projects/{project_name}/plans/{feature_name}/plan.md", limit=20)
```

---

## Step 5: Display Summary

```
Feature Plan Created: {feature-name}
Location: plans/{feature-name}/plan.md

Plan Summary:
- Implementation steps: {count}
- Files affected: {count} ({new} new, {modified} modified)
- Key technologies: {list}
- Complexity: {Low/Medium/High}

Research: analyst-sonnet, {N} files analyzed, {N} patterns found

Next: Run `/sa-generate {feature-name}` for implementation specs
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Missing feature name | Prompt: "What feature would you like to plan?" |
| Plan already exists | Ask: "Overwrite (1), Skip to /sa-generate (2), or Cancel (3)?" |
| Research agent fails | Offer: Retry, try coder-haiku, manual research, or cancel |
| No patterns found | Note in plan: "No similar features found. Using standard patterns." |
| Write tool fails | Display error: disk space, permissions, special characters |

---

## Implementation Checklist

- [ ] Parse and normalize feature name
- [ ] Handle missing argument + existing plan
- [ ] Spawn analyst-sonnet with detailed task
- [ ] Generate plan using `sa-plan-template.md`
- [ ] Use Write tool (NOT bash) with absolute path
- [ ] Use Read tool to verify (NOT bash)
- [ ] Display summary with step/file counts
- [ ] Include version footer in plan file

---

## Related Commands

- `/sa-generate {feature-name}` - Phase 2: Generate implementation specs
- `/sa-implement {feature-name}` - Phase 3: Execute implementation

**Template**: `sa-plan-template.md` (full plan structure with all sections)
**Reference**: `knowledge-vault/30-Patterns/Structured Autonomy Workflow.md`

---

**Version**: 2.0
**Created**: 2026-01-10
**Updated**: 2026-02-28
**Location**: .claude/commands/sa-plan.md
