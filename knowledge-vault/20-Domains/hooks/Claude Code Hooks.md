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

### settings.local.json (Generated from DB)
**File**: `.claude/settings.local.json`
**Scope**: Project-specific, auto-generated
**Source**: `claude.config_templates` + `claude.project_type_configs` + `claude.workspaces.startup_config`

**IMPORTANT**: Claude Code reads hooks from `settings.local.json`, NOT from `hooks.json`. A separate `hooks.json` file is NOT supported.

**Best Practice**: Store in database, regenerate files via `generate_project_settings.py`.

See [[Claude Hooks]] for the full enforcement chain and config flow.

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

1. ✅ **SessionStart**: Log session, load state, auto-archive stale todos
2. ✅ **UserPromptSubmit**: CORE_PROTOCOL injection + RAG context (silent, not chatty)
3. ✅ **PreToolUse[Write/Edit/Task/Bash]**: Task discipline enforcement (blocks if no tasks)
4. ✅ **PreToolUse[Write/Edit]**: Coding standards injection + validation
5. ✅ **PreToolUse[postgres]**: Database write validation (claude-family only)
6. ✅ **PostToolUse**: Todo sync, task sync, MCP usage logging
7. ✅ **SubagentStart**: Agent spawn logging
8. ✅ **PreCompact**: Inject active work items before compaction
9. ✅ **SessionEnd**: Auto-close session in database

**Configuration**: Stored in database, regenerated to file on startup

---

**Version**: 1.2
**Created**: 2025-12-28
**Updated**: 2026-02-18 (Fixed: hooks in settings.local.json not hooks.json, updated production hooks list)
**Location**: 20-Domains/Claude Code Hooks.md
