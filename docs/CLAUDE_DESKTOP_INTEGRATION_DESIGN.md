# Claude Desktop Integration Design

**Date:** 2025-12-27
**Status:** PROPOSED - Awaiting Decision
**Decision Required:** Manual vs Database-Driven Config Management

---

## Problem Statement

Claude Desktop is a valuable member of the Claude Family but currently has **manual configuration** while Claude Code projects use **database-driven configuration**. This creates:

1. **Config Drift**: Desktop config manually updated, can diverge from standards
2. **No Session Tracking**: Desktop sessions not logged to database
3. **Limited Visibility**: Hard to see what Desktop has done
4. **Manual MCP Updates**: Adding MCPs requires editing JSON file by hand

**Question:** Should we extend the database-driven config system to Claude Desktop?

---

## Current State

### What Exists Today

**Handoff System** ✅
- Directory: `C:\Projects\claude-family\handoff\`
- Messaging via `claude.messages` table
- File-based spec passing
- Documentation in place

**Desktop Config** ⚠️
- Location: `%APPDATA%\Claude\claude_desktop_config.json`
- Manually maintained
- Has: postgres, filesystem, memory, sequential-thinking MCPs
- Access to vault and projects folders

**No Integration:**
- ❌ No entry in `claude.workspaces` table
- ❌ No identity in `claude.identities` table
- ❌ Sessions not tracked in `claude.sessions`
- ❌ Config not generated from database

---

## Integration Options

### Option 1: Keep Desktop Separate (MINIMAL)

**Rationale:**
- Desktop is used differently than Code (ideation vs implementation)
- Desktop doesn't need project-specific configs (no "current directory")
- Desktop MCP needs rarely change
- Manual config is fine for one instance

**What We Do:**
- ✅ Keep handoff system as-is
- ✅ Keep manual config file
- ✅ Desktop can query database for project status
- ✅ Desktop sends messages to Code instances
- ❌ No session tracking
- ❌ No database-driven config

**Pros:**
- Simple, no changes needed
- Desktop remains flexible
- Lower maintenance overhead

**Cons:**
- Inconsistent with Claude Family philosophy (database-driven)
- No tracking of Desktop activities
- Manual config maintenance
- Can't generate reports on Desktop usage

---

### Option 2: Lightweight Integration (RECOMMENDED)

**Rationale:**
- Track Desktop sessions for visibility
- Create identity for Desktop
- Keep config manual (Desktop is special)
- Enable reporting and coordination

**What We Do:**

#### 1. Create Desktop Identity
```sql
INSERT INTO claude.identities (
    identity_id,
    identity_name,
    identity_type,
    description,
    created_at
) VALUES (
    gen_random_uuid(),
    'claude-desktop',
    'claude_instance',
    'Claude Desktop - ideation, design, advisor role',
    NOW()
);
```

#### 2. Create Workspace Entry (No Project)
```sql
INSERT INTO claude.workspaces (
    project_name,
    project_path,
    project_type,
    is_active,
    added_at,
    notes
) VALUES (
    'claude-desktop',
    '%APPDATA%\Claude',
    'desktop',  -- new type
    true,
    NOW(),
    'Claude Desktop app - no project-specific config needed'
);
```

#### 3. Track Sessions (User-Initiated)
Desktop can log sessions via SQL:
```sql
-- At conversation start
INSERT INTO claude.sessions (session_id, identity_id, project_name, session_start)
SELECT gen_random_uuid(), identity_id, 'claude-desktop', NOW()
FROM claude.identities
WHERE identity_name = 'claude-desktop'
RETURNING session_id;

-- At conversation end (manual)
UPDATE claude.sessions
SET session_end = NOW(),
    session_summary = 'Summary of what was discussed',
    tasks_completed = ARRAY['Task 1', 'Task 2']
WHERE session_id = '{session_id from above}';
```

#### 4. Keep Config Manual
- Desktop config stays at `%APPDATA%\Claude\claude_desktop_config.json`
- Updated manually when needed
- Document MCP list in knowledge vault for reference

**Pros:**
- Session tracking for visibility
- Identity exists for messaging
- Minimal complexity
- Desktop retains flexibility
- Can report on Desktop activities

**Cons:**
- Config still manual (but acceptable)
- User must manually start/end sessions (or we prompt)
- Not fully database-driven

---

### Option 3: Full Database-Driven (COMPLEX)

**Rationale:**
- Complete consistency across all Claude instances
- Central config management
- Automated config distribution

**What We Do:**

#### 1. Add Desktop Project Type
```sql
INSERT INTO claude.project_type_configs (
    project_type,
    default_mcp_servers,
    default_skills,
    default_instructions,
    config_template_id
) VALUES (
    'desktop',
    ARRAY['postgres', 'filesystem', 'memory', 'sequential-thinking'],
    ARRAY[],  -- Desktop doesn't use skills
    ARRAY[],  -- No auto-apply instructions for Desktop
    NULL
);
```

#### 2. Generate Desktop Config
Create `scripts/generate_desktop_config.py`:
```python
def generate_desktop_config(identity_name='claude-desktop'):
    # 1. Read from project_type_configs WHERE project_type = 'desktop'
    # 2. Read mcp_configs for each server
    # 3. Generate claude_desktop_config.json
    # 4. Write to %APPDATA%\Claude\claude_desktop_config.json
    pass
```

#### 3. Auto-Sync on Startup
Desktop would need a startup hook (if possible) to run:
```bash
python C:\Projects\claude-family\scripts\generate_desktop_config.py
```

**Challenge:** Desktop doesn't have hooks like Code CLI does!

#### 4. Manual Sync Alternative
User runs sync script periodically:
```bash
# Weekly or when MCPs change
python C:\Projects\claude-family\scripts\generate_desktop_config.py
claude-desktop-restart-required
```

**Pros:**
- Complete consistency
- Central MCP management
- Database is source of truth for all configs

**Cons:**
- Desktop can't auto-sync (no hooks)
- Requires manual script runs or external scheduling
- Adds complexity for marginal benefit
- Overwrites manual Desktop customizations

---

## Recommended Approach: **Option 2 (Lightweight Integration)**

### Why This is Best

1. **Tracking without Complexity**: We get visibility into Desktop usage without overengineering
2. **Respects Desktop's Role**: Desktop is for ideation/design, not coding - different needs
3. **Manual Config is Fine**: Desktop MCPs rarely change, manual is acceptable
4. **Enables Coordination**: Identity and sessions allow proper inter-Claude messaging
5. **Pragmatic**: Balance between "do nothing" and "do everything"

---

## Implementation Plan (Option 2)

### Phase 1: Database Setup (15 minutes)

**Task 1.1: Create Desktop Identity**
```sql
INSERT INTO claude.identities (identity_name, identity_type, description)
VALUES ('claude-desktop', 'claude_instance', 'Claude Desktop - ideation and design');
```

**Task 1.2: Add Desktop Project Type**
```sql
INSERT INTO claude.project_type_configs (
    project_type,
    default_mcp_servers,
    default_skills,
    default_instructions
) VALUES (
    'desktop',
    ARRAY['postgres', 'filesystem', 'memory', 'sequential-thinking', 'orchestrator'],
    ARRAY[],
    ARRAY[]
);
```

**Task 1.3: Create Workspace Entry**
```sql
INSERT INTO claude.workspaces (
    project_name,
    project_path,
    project_type,
    is_active
) VALUES (
    'claude-desktop',
    '%APPDATA%\\Claude',
    'desktop',
    true
);
```

### Phase 2: Documentation (30 minutes)

**Task 2.1: Update Handoff README**
Add section "Logging Your Sessions":
```markdown
## For Claude Desktop: Logging Sessions

To help the family track your work, log your sessions:

**At conversation start:**
[SQL to insert session]

**At conversation end:**
[SQL to update session with summary]
```

**Task 2.2: Create Desktop Session Guide**
Create `knowledge-vault/Claude Family/Claude Desktop Sessions.md`:
- How to log sessions
- When to log (start of each conversation)
- What to include in summary
- How to check past sessions

**Task 2.3: Update MCP Registry**
Document Desktop's MCPs in `knowledge-vault/Claude Family/MCP Registry.md`:
```markdown
### Claude Desktop
- postgres (global)
- filesystem (vault + projects access)
- memory (shared graph)
- sequential-thinking (complex problem solving)
```

### Phase 3: Tooling (Optional, 30 minutes)

**Task 3.1: Desktop Session Helper**
Create `scripts/desktop_session_helper.py`:
```python
# Generates SQL for Desktop to copy/paste for session logging
# Makes it easier than writing SQL manually

def start_session():
    print("Copy/paste this SQL into Claude Desktop:")
    print(generate_start_session_sql())

def end_session(session_id, summary, tasks):
    print("Copy/paste this SQL:")
    print(generate_end_session_sql(session_id, summary, tasks))
```

Desktop user runs:
```bash
python scripts/desktop_session_helper.py start
# Copies SQL, pastes into Desktop, executes
```

---

## Future Enhancements (Not Now)

### If Desktop Gets Hooks Someday
- Auto-session logging (like Code CLI)
- Config sync from database
- Automatic message checking

### If We Get More Desktop Users
- Multiple Desktop identities (Desktop-Personal, Desktop-Work)
- Desktop-specific skills
- Desktop activity dashboards in Mission Control Web

---

## Decision Matrix

| Criteria | Option 1 (Separate) | Option 2 (Lightweight) ⭐ | Option 3 (Full) |
|----------|-------------------|-------------------------|----------------|
| Session tracking | ❌ No | ✅ Yes | ✅ Yes |
| Config management | ⚠️ Manual | ⚠️ Manual | ✅ Database |
| Implementation effort | ✅ None | ✅ Low | ❌ High |
| Maintenance | ✅ Low | ✅ Low | ⚠️ Medium |
| Consistency with family | ❌ Low | ⚠️ Medium | ✅ High |
| Respects Desktop differences | ✅ Yes | ✅ Yes | ⚠️ Forces uniformity |
| Reporting capability | ❌ None | ✅ Good | ✅ Excellent |
| **Recommended?** | No | **YES** | No |

---

## Risk Assessment

### Option 2 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| User forgets to log sessions | High | Low | Make it easy with helper script |
| Manual config drift | Low | Low | Desktop MCPs rarely change |
| Desktop needs differ from Code | Medium | Low | Separate project_type handles this |

**Overall Risk: LOW**

---

## Implementation Checklist

- [ ] **Decision**: User approves Option 2 (Lightweight Integration)
- [ ] **Phase 1**: Database setup (15 min)
  - [ ] Create Desktop identity
  - [ ] Add Desktop project type
  - [ ] Create workspace entry
- [ ] **Phase 2**: Documentation (30 min)
  - [ ] Update handoff README with session logging
  - [ ] Create Desktop Session Guide
  - [ ] Update MCP Registry with Desktop MCPs
- [ ] **Phase 3**: Tooling (optional, 30 min)
  - [ ] Create desktop_session_helper.py script
  - [ ] Test script generates valid SQL
  - [ ] Document script usage
- [ ] **Verification**:
  - [ ] Desktop can insert session records
  - [ ] Desktop shows in identities table
  - [ ] Desktop workspace visible in database
  - [ ] Session queries return Desktop sessions

---

## Success Criteria

✅ Desktop has an identity in `claude.identities`
✅ Desktop has a workspace entry in `claude.workspaces`
✅ Desktop can log sessions to `claude.sessions`
✅ Desktop sessions appear in reporting/queries
✅ Config remains manual (no breaking changes)
✅ Documentation updated with session logging guide
✅ Helper script makes logging easy

---

## Alternative: Do Nothing (Reject Integration)

**If we decide integration isn't worth it:**
- Desktop remains fully manual
- No session tracking
- No database entry
- Handoff system continues as-is
- Accept this limitation and move on

**When this makes sense:**
- Desktop is rarely used
- Session tracking not valuable
- Prefer simplicity over consistency

---

## Next Steps

1. **User Decision**: Choose Option 1, 2, or 3 (recommend Option 2)
2. **If Option 2**: Execute implementation checklist
3. **If Option 1**: Close this todo, accept manual Desktop
4. **If Option 3**: Create detailed implementation spec

---

## Related Documents

- [[Claude Desktop Start Here]] - Onboarding for Desktop
- [[Handoff System]] - File + message passing
- [[Config Management SOP]] - How Code CLI config works
- [[Session Lifecycle]] - Session tracking for Code CLI
- [[Identity System]] - Identity management

---

**Status:** AWAITING DECISION
**Recommended:** Option 2 (Lightweight Integration)
**Estimated Effort:** 1-2 hours total
**Created:** 2025-12-27
**Author:** Claude Code (claude-family project)
