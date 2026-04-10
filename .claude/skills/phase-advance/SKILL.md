---
name: phase-advance
description: "Advance a project to its next phase after verifying all requirements are met"
user-invocable: true
disable-model-invocation: true
---

# Advance Project Phase

Move a project to its next phase after verifying requirements are met.

**Usage**: `/phase-advance [project_name]` (defaults to current project)

---

## 7-Stage Phase Model

```
idea -> planning -> design -> implementation -> testing -> production -> archived
```

## Phase Requirements

### idea -> planning
- [ ] Problem statement exists (even rough)
- [ ] User/stakeholder identified
- [ ] Project registered in `claude.projects`

### planning -> design
- [ ] PROBLEM_STATEMENT.md complete
- [ ] Success criteria defined
- [ ] Constraints documented
- [ ] At least one feature in `claude.features`

### design -> implementation
- [ ] CLAUDE.md exists and is current
- [ ] ARCHITECTURE.md exists
- [ ] At least one feature with build tasks
- [ ] Build tasks created for first feature

### implementation -> testing
- [ ] Core functionality complete
- [ ] Unit tests exist and pass
- [ ] No critical bugs open

### testing -> production
- [ ] All tests passing
- [ ] Documentation updated
- [ ] All critical features completed
- [ ] User has approved for production use

### any -> archived
- [ ] User confirms project should be archived
- [ ] Final documentation updated
- [ ] Archive reason documented

## Gate Overlay (Optional)

For projects using structured quality gates (e.g., Metis), gates overlay within phases:

| Phase | Gate | Question |
|-------|------|----------|
| planning | Gate 0 | Do we understand the problem? |
| planning | Gate 1 | Do we understand the domain? |
| design | Gate 2 | Have we designed the solution? |
| implementation | Gate 3 | Are we ready to build? |
| testing | Gate 4 | Are we ready to release? |

Gates are optional quality checkpoints, not required for phase advancement.

## Instructions

1. **Identify project** from argument or working directory

2. **Get current phase**:
```sql
SELECT project_id, project_name, phase, status
FROM claude.projects
WHERE project_name = '{project_name}';
```

3. **Determine next phase** based on progression above

4. **Verify requirements** — check each item, report met/missing

5. **If all met**: Ask user to confirm, then update:
```sql
UPDATE claude.projects
SET phase = '{next_phase}', updated_at = NOW()
WHERE project_name = '{project_name}';
```

6. **If not met**: Show what's missing, offer to help complete items

**BPMN model**: `lifecycle/project_lifecycle.bpmn` (phase_advancement process)
**Vault SOP**: `recall_memories("project lifecycle SOP")`

---

**Version**: 2.0
**Created**: 2026-03-15
**Updated**: 2026-03-22
**Location**: .claude/skills/phase-advance/SKILL.md