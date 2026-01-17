---
projects:
- claude-family
tags:
- hooks
- context-injection
- infrastructure
synced: false
---

# PreToolUse Context Injection System

Automatic injection of relevant standards and context BEFORE Claude writes code or executes queries.

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Tool Called    │────▶│  context_injector    │────▶│  Standards      │
│  (Write, Edit,  │     │  _hook.py            │     │  Injected       │
│   SQL, etc.)    │     │                      │     │  to Context     │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
                               │                            ▲
                               │ Query                      │ Load
                               ▼                            │
                        ┌──────────────────────┐     ┌──────────────────┐
                        │  claude.context_rules│     │  ~/.claude/      │
                        │  (database)          │     │  standards/      │
                        └──────────────────────┘     └──────────────────┘
```

## How It Works

1. **PreToolUse hook fires** when Claude uses Write, Edit, or SQL tools
2. **Hook queries `claude.context_rules`** for matching rules by:
   - `tool_patterns` - must contain the tool name (e.g., `['Write', 'Edit']`)
   - `file_patterns` - optional glob patterns (e.g., `['**/*.md']`)
3. **Hook composes context** from matched rules:
   - `inject_static_context` - immediate inline text
   - `inject_standards` - load files from `~/.claude/standards/`
4. **Returns `additionalContext`** to Claude before tool execution

## Database Schema

```sql
-- Key columns in claude.context_rules
tool_patterns TEXT[]      -- Tools that trigger rule: ['Write', 'Edit']
file_patterns TEXT[]      -- Optional glob patterns: ['**/*.md']
inject_standards TEXT[]   -- Standard files to load: ['markdown']
inject_static_context TEXT -- Inline context to inject
priority INTEGER          -- Higher = applied first (default 50)
active BOOLEAN           -- Enable/disable rule
```

## Current Rules

| Rule | Tools | Files | Injects |
|------|-------|-------|---------|
| documentation-standards | Write, Edit | `**/*.md` | markdown standard + inline |
| database-operations | mcp__postgres__* | - | sql-postgres standard + inline |
| csharp-development | Write, Edit | `**/*.cs` | csharp standard |
| wpf-development | Write, Edit | `**/*.xaml` | wpf-ui standard |

## Adding a New Rule

```sql
INSERT INTO claude.context_rules (
    name, description, tool_patterns, file_patterns,
    inject_standards, inject_static_context, priority, active
) VALUES (
    'my-new-rule',
    'Inject X standard when writing Y files',
    ARRAY['Write', 'Edit'],           -- Tools to match
    ARRAY['**/*.py'],                  -- File patterns (optional)
    ARRAY['python'],                   -- Standards to load
    '⚠️ Remember to follow PEP8!',     -- Inline context
    60,                                -- Priority (higher = first)
    true                               -- Active
);
```

## Standards Files

Located in `~/.claude/standards/` with subdirectories:
- `core/` - Core standards (markdown, etc.)
- `framework/` - Framework-specific (wpf-ui, etc.)
- `language/` - Language-specific (csharp, sql-postgres, etc.)

## Hook Chain Order

```
PreToolUse → context_injector_hook.py → standards_validator.py → Tool Executes
              (inject context)           (validate/block)
```

The injector runs BEFORE the validator, so Claude sees standards before writing.

## Files

| File | Purpose |
|------|---------|
| `scripts/context_injector_hook.py` | PreToolUse hook script |
| `claude.context_rules` | Rule definitions (DB) |
| `claude.config_templates` | Hook configuration (DB) |
| `~/.claude/standards/**/*.md` | Standard files to inject |

## Logs

Check `~/.claude/hooks.log` for injection activity:
```
2026-01-17 00:38:02 - context_injector - INFO - Found 1 matching rules: ['documentation-standards']
2026-01-17 00:38:02 - context_injector - INFO - Injecting 2066 chars of context
```

## MUI Management

Context rules can be viewed/edited in Claude Manager MUI:
- Global Settings → Context Rules tab
- Shows all rules with tool/file patterns
- Edit rules, toggle active state

**Note**: Full CRUD requires Rust backend implementation (currently read-only from DB).

## Related

- [[Config Management SOP]] - How config deployment works
- [[Claude Hooks]] - Hook system overview
- [[Claude Code 2.1.x Integration]] - additionalContext feature

---

**Version**: 1.0
**Created**: 2026-01-17
**Updated**: 2026-01-17
**Location**: knowledge-vault/20-Domains/PreToolUse Context Injection.md
