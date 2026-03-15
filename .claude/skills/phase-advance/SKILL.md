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

## Phase Progression

```
idea -> research -> planning -> implementation -> maintenance -> archived
```

## Phase Requirements

### idea -> research
- [ ] Problem statement exists (even rough)
- [ ] User/stakeholder identified

### research -> planning
- [ ] PROBLEM_STATEMENT.md complete
- [ ] Success criteria defined
- [ ] Constraints documented

### planning -> implementation
- [ ] CLAUDE.md exists and is current
- [ ] ARCHITECTURE.md exists
- [ ] At least one feature in `claude.features`
- [ ] Build tasks created for first feature

### implementation -> maintenance
- [ ] Core functionality complete
- [ ] Documentation updated
- [ ] All critical features completed

### maintenance -> archived
- [ ] User confirms project should be archived
- [ ] Final documentation updated
- [ ] Archive reason documented

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

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/phase-advance/SKILL.md
