# Structured Autonomy: Create Feature Plan (V2)

**Phase**: Planning
**Purpose**: Research codebase and create a structured implementation plan for a feature.
**Usage**: `/sa-plan-v2 {feature-name}`

Example: `/sa-plan-v2 dark-mode-toggle` creates `plans/dark-mode-toggle/plan.md`

---

## Overview

Phase 1 of the **Structured Autonomy Workflow** - research and planning for cost-effective feature development.

**Pattern**: Plan → Generate → Implement (73% cheaper than all-premium approach)

**Key improvements over v1**:
- Uses analyst-sonnet (better research, DB/vault access)
- Write tool for file creation (not bash mkdir/touch)
- Read tool for verification (not bash test/cat)
- More comprehensive plan template

See: `knowledge-vault/30-Patterns/Structured Autonomy Workflow.md`

---

## Implementation Steps

### 1. Parse Feature Name

Extract from command argument or prompt user if missing.

**Normalization**: lowercase, spaces → hyphens (e.g., "Dark Mode" → "dark-mode")

**Output**: Feature name, directory path, file path

---

### 2. Research Codebase

Spawn analyst-sonnet for comprehensive research:

```python
mcp__orchestrator__spawn_agent(
    agent_type="analyst-sonnet",
    task=f"""Research codebase for {feature_name}:

1. Find existing patterns (similar features, architecture, testing)
2. Identify key files and structure (entry points, components, state)
3. Document dependencies (UI libs, state management, styling, testing)
4. Find code examples to follow
5. Identify technology stack and conventions

Provide comprehensive analysis with specific file paths and examples.""",
    workspace_dir="C:/Projects/{project_name}"
)
```

**Why analyst-sonnet?** Database/vault access, cost-effective, thorough analysis.

**Save the output** - used to populate plan sections.

---

### 3. Generate Plan Content

Use the comprehensive template from sa-plan.md with these sections:

**Required Sections**:
- Requirements (Functional + Non-Functional)
- Current State Analysis (Patterns, Architecture, Dependencies)
- Implementation Strategy (Approach + Steps)
- Files Affected (table with paths, status, purpose)
- Risks & Mitigations
- Dependencies & Prerequisites
- Verification Checklist
- Success Criteria
- Rollback Plan

**Populate with research**: Copy patterns with code examples, list specific files, create step-by-step plan.

**Template reference**: See Step 4 in `.claude/commands/sa-plan.md`

---

### 4. Write Plan File

**CRITICAL**: Use Write tool (NOT bash):

```python
Write(
    file_path=f"C:/Projects/{project_name}/plans/{feature_name}/plan.md",
    content=populated_plan_content
)
```

**Why?** Auto-creates directories, cross-platform, proper error handling.

**Do NOT use**: `mkdir`, `touch`, `echo >`, `cat <<EOF`

---

### 5. Verify Creation

Use Read tool to confirm file exists:

```python
Read(
    file_path=f"C:/Projects/{project_name}/plans/{feature_name}/plan.md",
    limit=20  # Check first 20 lines
)
```

**Do NOT use**: `test -f`, `cat`, `ls`

---

### 6. Display Summary

Show comprehensive summary:

```
✅ Feature Plan Created: {feature-name}

📁 Location: plans/{feature-name}/plan.md

📋 Plan Summary:
- Implementation steps: {count}
- Files affected: {count} ({new} new, {modified} modified)
- Key technologies: {comma-separated list}
- Complexity: {Low/Medium/High}

🔍 Research:
- Agent: analyst-sonnet
- Files analyzed: {count}
- Patterns found: {count}

➡️  Next Steps:
1. Review plan at plans/{feature-name}/plan.md
2. Run `/sa-generate {feature-name}` for implementation specs
3. Or edit plan and re-run when ready

💡 Tips:
- Review "Current State Analysis" for patterns
- Check "Risks & Mitigations" before starting
- Verify all prerequisites are met
```

---

## Error Handling

### Missing Feature Name
Prompt: "What feature would you like to plan?"

### Plan Already Exists
Ask: "Plan exists. Overwrite (1), Skip to /sa-generate (2), or Cancel (3)?"

### Research Agent Fails
Offer: Retry, try coder-haiku, manual research, or cancel

### No Patterns Found
Add to plan: "No similar features found. Using standard patterns for {tech stack}."

### Write Tool Fails
Display error with troubleshooting: disk space, permissions, special characters

---

## Tool Usage Rules

**CRITICAL - Always Follow**:

✅ **DO**:
- Use Write tool for file creation
- Use Read tool for verification
- Use absolute paths
- Include version footer in plan file
- Spawn analyst-sonnet for research

❌ **DO NOT**:
- Use bash mkdir/touch/echo for files
- Use bash test/cat for verification
- Use relative paths
- Skip error handling
- Spawn multiple agents

---

## Best Practices

**Effective Research**:
- Be specific in agent task (tech stack, similar features)
- Request code examples, not just descriptions
- Ask for conventions and patterns

**Quality Plans**:
- Actionable steps (clear enough to hand off)
- Specific files (exact paths, not "update components")
- Logical order (respect dependencies)
- Independent steps (can be rolled back)
- Clear verification (how to know it worked)

**Cost Optimization**:
- One comprehensive research pass
- Use analyst-sonnet (not opus)
- Reuse research for /sa-generate

---

## Plan Template Structure

**Metadata**: Status, dates, feature name, project name

**Planning Sections**:
1. Requirements (Functional + Non-Functional)
2. Current State Analysis (Patterns + Architecture + Dependencies + Integration)
3. Implementation Strategy (Approach + Detailed Steps)
4. Files Affected (Table)
5. Risks & Mitigations (Table)
6. Dependencies & Prerequisites
7. Verification Checklist (Code + Functionality + Testing + A11y + Performance + Docs)
8. Success Criteria (Definition of Done + Acceptance Test)
9. Rollback Plan

**Footer**: Next Phase pointer, version info

**Full template**: See `.claude/commands/sa-plan.md` Step 4

---

## Implementation Checklist

When executing this command:

- [ ] Parse and normalize feature name
- [ ] Handle missing argument
- [ ] Spawn analyst-sonnet with detailed task
- [ ] Save research output
- [ ] Generate plan using template
- [ ] Populate with research findings
- [ ] Use Write tool (NOT bash)
- [ ] Use Read tool to verify (NOT bash)
- [ ] Display comprehensive summary
- [ ] Handle error cases
- [ ] Include version footer in plan
- [ ] Check for existing plan

---

## Related Commands

- `/sa-generate {feature-name}` - Phase 2: Generate implementation specs
- `/sa-implement {feature-name}` - Phase 3: Execute implementation (future)
- `/todo` - Track implementation tasks
- `/feedback-create` - Capture issues or improvements

---

## References

- **Pattern**: `knowledge-vault/30-Patterns/Structured Autonomy Workflow.md`
- **Original**: `.claude/commands/sa-plan.md`
- **Standards**: `~/.claude/standards/core/markdown-documentation.md`

---

**Version**: 1.0
**Created**: 2026-01-10
**Updated**: 2026-01-10
**Location**: .claude/commands/sa-plan-v2.md
