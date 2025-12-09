# SOP-007: Slash Command Management

**Status**: Active
**Version**: 1.0
**Created**: 2025-12-08
**Owner**: Claude Family Infrastructure

---

## Purpose

Define the lifecycle for slash commands: creation, testing, distribution, and maintenance. Ensures commands are consistent, tested, and properly deployed across all projects.

---

## Scope

Applies to all slash commands in `.claude/commands/` directories across:
- claude-family (source of truth)
- ATO-Tax-Agent
- mission-control-web
- nimbus-user-loader

---

## Command Categories

| Category | Commands | Distribution |
|----------|----------|--------------|
| Session | session-start, session-end, session-resume, session-commit | ALL projects |
| Communication | broadcast, inbox-check, team-status | ALL projects |
| Feedback | feedback-check, feedback-create, feedback-list | ALL projects |
| Project | project-init, retrofit-project, phase-advance | claude-family only |
| Quality | check-compliance, review-docs, review-data | ALL projects |

---

## 1. Creating New Commands

### 1.1 Before Creating

1. **Check if similar command exists**
   ```sql
   SELECT file_path FROM claude.documents
   WHERE file_path LIKE '%.claude/commands/%'
   ORDER BY file_path;
   ```

2. **Check if process already registered**
   ```sql
   SELECT process_name, command_ref FROM claude.process_registry
   WHERE command_ref IS NOT NULL;
   ```

3. **Determine distribution scope**
   - Universal (all projects) vs Project-specific (one project)

### 1.2 Command Template

```markdown
# Command Name

**Purpose**: One-line description

**When to use**: Circumstances that trigger this command

---

## Steps

1. First step with clear instructions
2. Second step
3. ...

## Example Usage

\`\`\`
Example command or output
\`\`\`

---

## Related

- Related command 1
- Related SOP

---

**Version**: 1.0
**Created**: YYYY-MM-DD
```

### 1.3 Naming Convention

- Use lowercase with hyphens: `my-command.md`
- Prefix by category if helpful: `session-`, `feedback-`, `review-`
- Keep names short but descriptive

---

## 2. Testing Commands

### 2.1 Manual Testing (Required)

Before deploying, test the command:

1. **Syntax check**: Does it parse correctly?
2. **Execution check**: Does it do what it says?
3. **Error handling**: What happens with bad input?
4. **Side effects**: Does it modify anything unexpectedly?

### 2.2 Test Checklist

- [ ] Command file has valid markdown
- [ ] Instructions are clear and complete
- [ ] Any SQL queries work correctly
- [ ] Any scripts referenced exist
- [ ] Version and date are set

### 2.3 Recording Test Results

Log test in capability_usage:
```sql
INSERT INTO claude.capability_usage
(capability_type, capability_name, project_name, triggered_by, outcome, metadata)
VALUES ('slash_command', 'command-name', 'claude-family', 'testing', 'success',
        '{"tested_by": "claude-code-unified", "test_date": "2025-12-08"}');
```

---

## 3. Distribution Process

### 3.1 Universal Commands

Commands that go to ALL projects:

1. **Create in claude-family** first
2. **Test in claude-family**
3. **Copy to other projects**:
   ```bash
   # From claude-family directory
   cp .claude/commands/new-command.md ../ATO-Tax-Agent/.claude/commands/
   cp .claude/commands/new-command.md ../mission-control-web/.claude/commands/
   cp .claude/commands/new-command.md ../nimbus-user-loader/.claude/commands/
   ```
4. **Verify deployment** (see Section 5)

### 3.2 Project-Specific Commands

Commands for one project only:

1. Create directly in target project's `.claude/commands/`
2. Document in that project's CLAUDE.md
3. Do NOT copy to other projects

### 3.3 Distribution Tracking

Record distribution:
```sql
INSERT INTO claude.capability_usage
(capability_type, capability_name, project_name, triggered_by, outcome)
VALUES
('slash_command', 'new-command', 'ATO-Tax-Agent', 'distribution', 'success'),
('slash_command', 'new-command', 'mission-control-web', 'distribution', 'success'),
('slash_command', 'new-command', 'nimbus-user-loader', 'distribution', 'success');
```

---

## 4. Updating Commands

### 4.1 Update Process

1. **Update in claude-family first** (source of truth)
2. **Increment version** in command footer
3. **Update date** in command footer
4. **Test the update**
5. **Distribute to other projects** (if universal)
6. **Announce via broadcast** (if significant change)

### 4.2 Breaking Changes

If changing command behavior significantly:

1. Consider creating new command instead
2. Deprecate old command (add deprecation notice)
3. Announce via `/broadcast`
4. Remove deprecated command after 30 days

---

## 5. Verification

### 5.1 Manual Verification

Check command exists in project:
```bash
ls -la /path/to/project/.claude/commands/command-name.md
```

### 5.2 Scheduled Verification

Add to scheduled jobs to check consistency:
```sql
-- This should be a scheduled job
SELECT 'command-consistency-check' as job_name,
       'Compare slash commands across all projects' as description;
```

### 5.3 Consistency Check Script

Create `scripts/check_command_consistency.py`:
- Compare `.claude/commands/` across all projects
- Report missing commands
- Report version mismatches
- Report content differences

---

## 6. Maintenance

### 6.1 Regular Review

Monthly, review all commands:
- Are they still used?
- Are they accurate?
- Do they need updates?

### 6.2 Deprecation

To deprecate a command:

1. Add deprecation notice at top:
   ```markdown
   > **DEPRECATED**: Use `/new-command` instead. Will be removed 2025-02-01.
   ```

2. Update process_registry if applicable
3. Announce via broadcast
4. Remove after deprecation period

### 6.3 Removal

To remove a command:

1. Ensure it's been deprecated for 30+ days
2. Remove from all projects
3. Update any documentation referencing it
4. Log removal in capability_usage

---

## 7. Current Command Inventory

| Command | Category | Scope | Last Updated |
|---------|----------|-------|--------------|
| session-start | Session | Universal | 2025-12-07 |
| session-end | Session | Universal | 2025-12-07 |
| session-resume | Session | Universal | 2025-12-07 |
| session-commit | Session | Universal | - |
| broadcast | Communication | Universal | - |
| inbox-check | Communication | Universal | - |
| team-status | Communication | Universal | - |
| feedback-check | Feedback | Universal | - |
| feedback-create | Feedback | Universal | - |
| feedback-list | Feedback | Universal | - |
| project-init | Project | claude-family | - |
| retrofit-project | Project | claude-family | - |
| phase-advance | Project | claude-family | - |
| check-compliance | Quality | Universal | - |
| review-docs | Quality | Universal | - |
| review-data | Quality | Universal | - |

---

## 8. Quick Reference

### Create Command
1. Check if exists
2. Use template
3. Test locally
4. Distribute if universal

### Update Command
1. Update in claude-family
2. Increment version
3. Test
4. Distribute

### Verify Distribution
```bash
# Check all projects have command
for project in ATO-Tax-Agent mission-control-web nimbus-user-loader; do
  ls -la /c/Projects/$project/.claude/commands/command-name.md
done
```

---

## Related Documents

- SOP-004-PROJECT-INITIALIZATION.md - Initial command setup
- CAPABILITIES.md - Command inventory
- USAGE_WORKFLOWS.md - When commands are used

---

**Revision History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-08 | Initial version |

---

**Location**: C:\Projects\claude-family\docs\sops\SOP-007-SLASH-COMMAND-MANAGEMENT.md
