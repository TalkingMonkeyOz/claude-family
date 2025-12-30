---
title: Claude Code Hooks
category: domain-knowledge
domain: claude-code
created: 2025-12-28
updated: 2025-12-28
tags:
  - hooks
  - automation
  - claude-code
  - configuration
status: active
---

# Claude Code Hooks

**Domain**: Claude Code Automation
**Purpose**: Understanding and configuring Claude Code hooks system

---

## What Are Hooks?

Hooks are automated actions that run at specific points in the Claude Code lifecycle:

- **UserPromptSubmit**: Before processing user input
- **PreToolUse**: Before executing a tool
- **PostToolUse**: After a tool executes
- **PostToolUseFailure**: After a tool fails
- **SessionStart**: When session begins
- **SessionEnd**: When session ends
- **Stop**: When user stops/interrupts
- **SubagentStart**: When subagent starts
- **SubagentStop**: When subagent stops
- **PreCompact**: Before compaction
- **PermissionRequest**: When requesting permission
- **Notification**: For notifications

**Note**: Claude Code does **NOT** support `PreCommit` or `PostCommit` hooks (GitHub Issue #4834 is an open feature request). Use native Git hooks (`.git/hooks/pre-commit`) instead.

---

## Hook Types

### 1. Prompt Hook
Injects additional context/instructions into the conversation.

**Example:**
```json
{
  "type": "prompt",
  "prompt": "Remember to check column_registry before database writes.",
  "timeout": 2
}
```

**Use Case**: Gentle reminders, context injection
**Warning**: Can be chatty and visible to user

### 2. Command Hook
Executes a shell command/script.

**Example:**
```json
{
  "type": "command",
  "command": "python C:/path/to/script.py",
  "timeout": 5,
  "description": "Validate file before writing"
}
```

**Use Case**: Validation, automated checks, logging
**Best Practice**: Keep timeout short, handle errors gracefully

---

## Configuration Locations

Hooks can be configured in **two places**:

### Option 1: Project File (Immediate)
**File**: `.claude/hooks.json`
**Scope**: Project-specific
**Priority**: Takes precedence over database

**Pros:**
- Quick to edit
- Version controlled (if committed)
- Project-specific customization

**Cons:**
- Not centrally managed
- Can get overwritten by config regeneration

### Option 2: Database (Managed)
**Table**: `claude.workspaces`
**Column**: `startup_config->'hooks'`
**Scope**: Centrally managed, deployed to projects

**Pros:**
- Single source of truth
- Survives config regeneration
- Can be shared across projects via project types

**Cons:**
- Requires database update
- Less immediate than file edit

**Best Practice**: Store in database, regenerate files via startup script

---

## Common Patterns

### Pattern 1: Auto-Apply Coding Standards
**When**: PreToolUse on Write/Edit
**Why**: Enforce consistent code style

```json
{
  "matcher": "Write",
  "hooks": [
    {
      "type": "command",
      "command": "python instruction_matcher.py",
      "timeout": 5,
      "description": "Auto-inject coding standards"
    }
  ]
}
```

**Example**: Auto-add accessibility instructions when editing `.tsx` files

---

### Pattern 2: Database Write Validation
**When**: PreToolUse on `mcp__postgres__execute_sql`
**Why**: Prevent invalid data entry

```json
{
  "matcher": "mcp__postgres__execute_sql",
  "hooks": [
    {
      "type": "command",
      "command": "python validate_db_write.py",
      "timeout": 10,
      "description": "Check column_registry for valid values"
    }
  ]
}
```

**Example**: Ensure status values are valid before INSERT

---

### Pattern 3: Session Logging
**When**: SessionStart
**Why**: Track session history, load state

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python session_startup_hook.py",
      "timeout": 30,
      "description": "Log session, load todos"
    }
  ]
}
```

**Example**: Auto-create session record in database

---

### Pattern 4: Usage Tracking
**When**: PostToolUse on MCP tools
**Why**: Monitor MCP usage, optimize configurations

```json
{
  "matcher": "mcp__.*",
  "hooks": [
    {
      "type": "command",
      "command": "python mcp_usage_logger.py",
      "timeout": 30
    }
  ]
}
```

**Example**: Track which MCPs are actually used

---

## Anti-Patterns (Avoid These)

### ❌ Chatty UserPromptSubmit Hooks

**Problem:**
```json
{
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Evaluate: Does this benefit from a skill? ..."
        }
      ]
    }
  ]
}
```

**Why Bad:**
- Triggers on EVERY user message
- Creates verbose "Operation stopped by hook" messages
- Interrupts conversation flow
- User sees internal reasoning

**Fix:**
- Remove UserPromptSubmit prompt hooks
- Use targeted PreToolUse hooks instead
- Let skills be invoked explicitly by user or naturally by Claude

---

### ❌ Long-Running Validation Hooks

**Problem:**
```json
{
  "timeout": 300,  // 5 minutes!
  "command": "run_full_test_suite.sh"
}
```

**Why Bad:**
- Blocks user interaction
- Frustrating delays
- Defeats purpose of quick iteration

**Fix:**
- Keep timeout < 10 seconds
- Run heavy checks asynchronously
- Use native Git hooks for comprehensive pre-commit validation

---

### ❌ Hooks Without Error Handling

**Problem:**
Script crashes → hook fails → operation blocked → user confused

**Fix:**
```python
try:
    # Do validation
    if validation_failed:
        sys.exit(1)  # Block operation
except Exception as e:
    # Log error but don't block
    print(f"Warning: {e}", file=sys.stderr)
    sys.exit(0)  # Allow operation to continue
```

---

## Research Notes

### Issue Discovered: 2025-12-28

**Symptom**: Verbose "Operation stopped by hook" messages appearing on every user prompt

**Root Cause**: UserPromptSubmit hook with prompt-type evaluation

```json
{
  "type": "prompt",
  "prompt": "Evaluate: Does this task benefit from a skill? ..."
}
```

**Analysis**:
- Hook was injecting skill evaluation prompt on EVERY message
- Designed to replace old `process_router`
- Good intention (skills-first architecture)
- Poor implementation (too chatty)

**Solution**:
1. Removed UserPromptSubmit hook entirely
2. Updated database config to persist change
3. Skills now invoked explicitly or naturally

**Trade-off**:
- **Before**: Auto-suggested skills, but super noisy
- **After**: Quieter, but less automatic skill discovery

**Future**: Consider background/silent evaluation that doesn't interrupt UX

---

## Best Practices

### 1. Start Minimal
Only add hooks when you have a specific problem to solve.

### 2. Keep Timeouts Short
- Validation: 5-10s max
- Logging: 3-5s max
- Heavy operations: Use background processes

### 3. Test Locally First
- Create `.claude/hooks.json` in project
- Test thoroughly
- Then promote to database if widely applicable

### 4. Document Why
Always include `"description"` field explaining hook's purpose.

### 5. Monitor Performance
- Check hook execution time in logs
- Remove hooks that aren't providing value
- Use PostToolUse logging to track usage

---

## Hook Development Workflow

1. **Identify Need**: "I keep forgetting to check X before doing Y"
2. **Create Script**: Write validation/automation script
3. **Test Standalone**: Run script manually, verify it works
4. **Add to hooks.json**: Start with local file
5. **Test Hook**: Trigger the hook condition, verify behavior
6. **Refine**: Adjust timeout, error handling, messaging
7. **Promote to Database**: If useful across projects

---

## Related Documentation

- **MCP Configuration**: See [[MCP Server Management]]
- **Skills System**: See [[40-Procedures/Family Rules]]
- **Database Schema**: `claude.workspaces.startup_config`
- **Config Generation**: `scripts/generate_project_settings.py`

---

## Examples in Production

### claude-family Project

**Current Hooks** (as of 2025-12-28):

1. ✅ **PreToolUse[Write/Edit]**: Auto-apply coding standards
2. ✅ **PreToolUse[postgres]**: Database write validation
3. ✅ **SessionStart**: Log session, load state
4. ✅ **SessionEnd**: Cleanup, documentation checks
5. ✅ **PostToolUse[mcp]**: Usage tracking
6. ❌ **UserPromptSubmit**: REMOVED (too chatty)

**Configuration**: Stored in database, regenerated to file on startup

---

**Version**: 1.1
**Created**: 2025-12-28
**Updated**: 2025-12-29 (Corrected: PreCommit is NOT a valid hook type)
**Location**: 20-Domains/Claude Code Hooks.md
