# Advance Project Phase

Move a project to its next phase after verifying requirements are met.

## Parameters
- **project_name**: $ARGUMENTS (optional - defaults to current project)

## Phase Progression

```
idea → research → planning → implementation → maintenance → archived
```

## Phase Requirements

### idea → research
- [ ] Problem statement exists (even rough)
- [ ] User/stakeholder identified

### research → planning
- [ ] PROBLEM_STATEMENT.md complete
- [ ] Success criteria defined
- [ ] Constraints documented

### planning → implementation
- [ ] CLAUDE.md exists and is current
- [ ] ARCHITECTURE.md exists
- [ ] At least one feature in `claude.features`
- [ ] Build tasks created for first feature

### implementation → maintenance
- [ ] Core functionality complete
- [ ] Documentation updated
- [ ] All critical features completed

### maintenance → archived
- [ ] User confirms project should be archived
- [ ] Final documentation updated
- [ ] Archive reason documented

## Instructions

When executing this command:

1. **Identify project**:
   - If argument provided, use that project name
   - Otherwise, detect from current working directory

2. **Get current phase**:
```sql
SELECT project_id, project_name, phase, status
FROM claude.projects
WHERE project_name = '{project_name}';
```

3. **Determine next phase** based on progression above

4. **Verify requirements** for the transition:
   - Check each requirement in the checklist above
   - Report which are met (✓) and which are missing (✗)

5. **If all requirements met**:
   - Ask user to confirm phase advance
   - Update database:
```sql
UPDATE claude.projects
SET phase = '{next_phase}', updated_at = NOW()
WHERE project_name = '{project_name}';
```
   - Log to activity feed:
```sql
INSERT INTO claude.activity_feed (event_type, event_data, created_at)
VALUES ('phase_advance',
        '{"project": "{project_name}", "from": "{current_phase}", "to": "{next_phase}"}'::jsonb,
        NOW());
```

6. **If requirements not met**:
   - Show user what's missing
   - Offer to help complete missing items
   - Do NOT advance phase

7. **Report result**:
   - Confirm new phase or explain blockers
   - Show governance status from `claude.project_governance`

## Example Usage

```
/phase-advance my-project
```

Or in the project directory:
```
/phase-advance
```

## Example Output

```
Project: my-project
Current Phase: planning
Next Phase: implementation

Requirements Check:
✓ CLAUDE.md exists
✓ ARCHITECTURE.md exists
✓ Features defined (3 features)
✗ Build tasks missing - no tasks for Feature #1

BLOCKED: Cannot advance until build tasks are created.
Would you like me to help create build tasks for your features?
```

---

**Created**: 2025-12-06
**See also**: `/project-init`, `/check-compliance`
