# SessionStart Hook & Duplicate Commands Fix

**Date**: 2025-12-29
**Status**: ✅ SessionStart Fixed, ⏸️ Duplicate Commands Awaiting Decision
**Impact**: SessionStart hook now works, duplicate commands identified

---

## Issue 1: SessionStart Hook Python Syntax Error ✅ FIXED

### Problem

SessionStart hook was failing with indentation error:
```
L SessionStart:startup hook error
```

### Root Cause

**File**: `.claude-plugins/claude-family-core/scripts/session_startup_hook.py`

Lines 381-384 had incorrect indentation (4 spaces instead of 8):

```python
# WRONG (4 spaces - outside try block)
    if session_id:
        context_lines.append(f"Session ID: {session_id} (auto-logged)")

# CORRECT (8 spaces - inside try block)
        if session_id:
            context_lines.append(f"Session ID: {session_id} (auto-logged)")
```

### Fix

**Commit**: session_startup_hook.py:378-384

Fixed indentation to properly nest within the try block.

### Testing

After fix, restart Claude Code and verify:
```bash
# Should see in session start output:
Session ID: xxxx-xxxx-xxxx (auto-logged)
MCP logging: enabled (session tracking active)

# Check hooks.log
tail ~/.claude/hooks.log
```

---

## Issue 2: Duplicate /session-resume Command ⏸️ AWAITING DECISION

### Problem

Two `/session-resume` commands appear in command list:
- `/session-resume` (user)
- `/session-resume` (project)

### Root Cause

Two command files with same name but **completely different implementations**:

#### User-Level (Global)
**Location**: `C:\Users\johnd\.claude\commands\session-resume.md`

**Approach**: Simple, file-based
- Reads `docs/TODO_NEXT_SESSION.md`
- Shows last session summary from file
- Git status for uncommitted files
- Checks inbox for messages

**Advantages**:
- Works for any project (no database required)
- Lightweight and fast
- Simple to understand

**Limitations**:
- No persistent todos
- No session history
- File-based only

#### Project-Level (claude-family)
**Location**: `C:\Projects\claude-family\.claude\commands\session-resume.md`

**Approach**: Database-driven, rich features
- Queries `claude.sessions` for session history
- Queries `claude.todos` for persistent todos
- Queries `claude.messages` for pending messages
- Shows full project state from database

**Advantages**:
- Comprehensive project state
- Persistent todos across sessions
- Full message accountability
- Rich metadata and tracking

**Limitations**:
- Requires Claude Family database infrastructure
- More complex
- Won't work for non-Claude-Family projects

### Analysis

**Scope Check**: Only `session-resume.md` is duplicated (no other command conflicts found)

**Behavior**: Claude Code loads both, project-level version likely takes precedence when in claude-family project.

### Resolution Options

#### Option A: Rename Project Command (Recommended)
- Keep user-level as `/session-resume` (simple, portable)
- Rename project-level to `/session-status` (database-driven, richer)
- Update project CLAUDE.md and skill references

**Pros**:
- Clear naming: "resume" = lightweight, "status" = comprehensive
- No breaking changes for other projects
- Both commands available with distinct purposes

**Cons**:
- Need to update references in docs/skills
- Users need to learn which to use when

#### Option B: Keep Both, Document Intent
- User-level: Quick file-based resume for simple projects
- Project-level: Full database resume for Claude Family projects
- Add documentation explaining which to use when
- Rely on Claude Code's project-level override behavior

**Pros**:
- No changes needed
- Project-specific overrides work naturally

**Cons**:
- Confusing to have duplicates
- Easy to invoke wrong one
- Maintenance burden (two implementations)

#### Option C: Delete User-Level
- Keep only database-driven version
- Force all projects to use Claude Family infrastructure

**Pros**:
- Single source of truth
- Consistent experience across projects

**Cons**:
- Breaks for non-Claude-Family projects
- Forces database dependency everywhere
- Not portable

### Recommended Decision

**Go with Option A**: Rename project command to `/session-status`

**Rationale**:
- Keeps intent clear and distinct
- Maintains backward compatibility for non-Claude-Family projects
- Provides both lightweight and comprehensive options
- Clear naming makes choice obvious

**Implementation**:
1. Rename `.claude/commands/session-resume.md` → `session-status.md`
2. Update references:
   - `CLAUDE.md` command list
   - `.claude/skills/session-management/skill.md`
   - Any other docs referencing `/session-resume` (project-level)
3. Test both commands work correctly

---

## Issue 3: Other Duplicate Commands Across Projects ⏸️ TO INVESTIGATE

### Scope

Check **all Claude Family projects** for duplicate commands:

```bash
# Find all project .claude/commands directories
find ~/Projects -type d -name commands -path "*/.claude/commands"

# For each project, compare with global commands
for project_dir in $(find ~/Projects -maxdepth 2 -type d -name ".claude"); do
    project_name=$(basename $(dirname $project_dir))
    commands_dir="$project_dir/commands"

    if [ -d "$commands_dir" ]; then
        echo "=== $project_name ==="
        comm -12 \
            <(ls C:/Users/johnd/.claude/commands/*.md 2>/dev/null | xargs -n1 basename | sort) \
            <(ls $commands_dir/*.md 2>/dev/null | xargs -n1 basename | sort)
    fi
done
```

### Fix Strategy

1. **Audit**: Run check across all projects
2. **Analyze**: For each duplicate, compare implementations
3. **Decide**: Rename, merge, or delete based on purpose
4. **Document**: Create SOP for command management
5. **Prevent**: Add validation to project scaffolding

### Command Management SOP (To Create)

**File**: `knowledge-vault/40-Procedures/Command Management SOP.md`

**Contents**:
- When to create global vs project commands
- Naming conventions to avoid conflicts
- Testing procedure for new commands
- Conflict resolution guidelines

---

## Files Modified

**Fixed**:
- `.claude-plugins/claude-family-core/scripts/session_startup_hook.py` - Indentation fix

**To Update** (if Option A chosen):
- `.claude/commands/session-resume.md` → `session-status.md` (rename)
- `CLAUDE.md` - Update command references
- `.claude/skills/session-management/skill.md` - Update command table
- Any docs referencing project-level `/session-resume`

**To Create**:
- `knowledge-vault/40-Procedures/Command Management SOP.md` - Command lifecycle and conflict resolution

---

## Next Steps

### Immediate
1. ✅ SessionStart hook indentation fixed
2. ✅ Duplicate command investigation complete
3. ⏸️ **User Decision Required**: Choose Option A, B, or C for `/session-resume` duplicate
4. ⏸️ Implement chosen solution
5. ⏸️ Test both commands work correctly

### Follow-up
6. ⏸️ Audit all Claude Family projects for duplicate commands
7. ⏸️ Create Command Management SOP
8. ⏸️ Add duplicate detection to project scaffolding
9. ⏸️ Update project templates with best practices

---

## Summary

### What's Fixed ✅
- SessionStart hook Python indentation error
- Root cause identified for both issues
- Documentation created

### What Needs Decision ⏸️
- Which option to choose for duplicate `/session-resume` commands
- Whether to audit all projects now or later
- Priority of Command Management SOP creation

**Status**: SessionStart hook working, awaiting user input on duplicate command strategy
