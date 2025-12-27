---
aliases:
- instruction-matcher
- awesome-copilot pattern
- auto-inject instructions
created: 2025-12-23
status: active
synced: false
tags:
- pattern
- instructions
- hooks
title: Auto-Apply Instructions System
type: pattern
updated: 2025-12-23
projects: []
---

# Auto-Apply Instructions System

Automatically inject coding standards into Claude's context based on file patterns. Inspired by the "awesome-copilot" pattern.

## How It Works

```
User edits file → Hook triggers → instruction_matcher.py → Matching instructions injected
```

When Claude uses Edit or Write tools on a file:
1. `instruction_matcher.py` hook runs
2. Scans instruction files for matching `applyTo` patterns
3. Injects matching instructions into Claude's context

## File Locations

| Location | Scope | Override Priority |
|----------|-------|-------------------|
| `~/.claude/instructions/*.instructions.md` | Global (all projects) | Lower |
| `{project}/.claude/instructions/*.instructions.md` | Project-specific | Higher |

Project-specific instructions override global ones with the same name.

## Instruction File Format

```yaml
---
description: 'Brief description of these guidelines'
applyTo: '**/*.cs'  # Glob pattern
---

# Instruction Content Here

Rules, conventions, patterns to follow...
```

### Multiple Patterns

```yaml
applyTo:
  - '**/*.xaml'
  - '**/ViewModels/**/*.cs'
```

## Current Global Instructions

| File | Pattern | Purpose |
|------|---------|---------|
| `csharp.instructions.md` | `**/*.cs` | C# conventions, async patterns |
| `wpf-ui.instructions.md` | `**/*.xaml`, `**/ViewModels/**/*.cs` | WPF-UI 3.0 rules |
| `mvvm.instructions.md` | `**/ViewModels/**/*.cs`, `**/Views/**/*.xaml` | MVVM patterns |
| `winforms.instructions.md` | `**/*.Designer.cs`, `**/Forms/**/*.cs` | WinForms rules |
| `winforms-dark-theme.instructions.md` | `**/*Form.cs`, `**/*Control.cs` | Dark theme colors |
| `a11y.instructions.md` | `**/*.cs`, `**/*.tsx` | WCAG AA accessibility |
| `sql-postgres.instructions.md` | `**/*.sql` | PostgreSQL best practices |
| `playwright.instructions.md` | `**/*.spec.ts`, `**/tests/**/*.ts` | E2E testing patterns |

## Implementation

### Hook Script

Location: `scripts/instruction_matcher.py`

```python
# Triggered on: Edit, Write tools
# Searches: ~/.claude/instructions/, .claude/instructions/
# Matches: file path against applyTo glob patterns
# Output: Matching instruction content to stdout (injected into context)
```

### Hook Configuration

In `.claude/settings.json` or global settings:

```json
{
  "hooks": {
    "Edit": [
      {
        "command": "python scripts/instruction_matcher.py \"$FILE_PATH\""
      }
    ],
    "Write": [
      {
        "command": "python scripts/instruction_matcher.py \"$FILE_PATH\""
      }
    ]
  }
}
```

## Creating New Instructions

1. **Global**: Create `~/.claude/instructions/{name}.instructions.md`
2. **Project**: Create `.claude/instructions/{name}.instructions.md`
3. Add YAML frontmatter with `applyTo` pattern
4. Write instruction content

### Example: React Instructions

```yaml
---
description: 'React component conventions'
applyTo:
  - '**/components/**/*.tsx'
  - '**/pages/**/*.tsx'
---

# React Component Guidelines

- Use functional components with hooks
- Props interface named {Component}Props
- Extract custom hooks to hooks/ directory
- Use React.memo for expensive renders
```

## Debugging

Check which instructions would apply:

```bash
python scripts/instruction_matcher.py "src/components/Button.tsx" --debug
```

## Related

- [[Claude Hooks]] - Hook system overview
- [[WinForms Designer Rules]] - Example instruction set
- [[instruction_matcher.py]] - Implementation details

---

**Created**: 2025-12-23
**Updated**: 2025-12-23
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: 30-Patterns/auto-apply-instructions.md