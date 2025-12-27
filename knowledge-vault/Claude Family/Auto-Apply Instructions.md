---
projects:
- claude-family
tags:
- system
- instructions
- automation
synced: false
---

# Auto-Apply Instructions

Automatically inject coding standards into Claude's context based on file patterns.

---

## Concept

```
Edit *.cs file → csharp.instructions.md auto-injects → Claude follows C# guidelines
```

**Key**: Automatic and invisible. No manual invocation needed.

---

## How It Works

```
User edits file → PreToolUse hook → instruction_matcher.py → Matched instructions inject → Claude receives file + standards
```

**Search Order**: Project `.claude/instructions/` → Global `~/.claude/instructions/`

---

## Global Instructions (9 Files)

**Location**: `~/.claude/instructions/`

| File | Applies To | Purpose |
|------|-----------|---------|
| `csharp.instructions.md` | `**/*.cs` | C# conventions, async patterns |
| `markdown.instructions.md` | `**/*.md` | Doc standards (size, structure) |
| `a11y.instructions.md` | `**/*.cs`, `**/*.tsx` | WCAG AA accessibility |
| `sql-postgres.instructions.md` | `**/*.sql` | PostgreSQL best practices |
| `playwright.instructions.md` | `**/*.spec.ts` | E2E testing patterns |
| `winforms.instructions.md` | `**/*.Designer.cs` | WinForms layout |
| `winforms-dark-theme.instructions.md` | `**/*Form.cs` | Dark theme colors |
| `wpf-ui.instructions.md` | `**/*.xaml` | WPF UI patterns |
| `mvvm.instructions.md` | `**/ViewModels/**/*.cs` | MVVM architecture |

---

## Creating New Instructions

**Global** (all projects): `~/.claude/instructions/[name].instructions.md`
**Project-specific**: `{project}/.claude/instructions/[name].instructions.md`

**Template**:
```yaml
---
description: 'What these guidelines cover'
applyTo: '**/*.ext'  # Glob pattern
---

# Technology Guidelines

## Core Principles
- Rule 1
- Rule 2

## Common Pitfalls
- Avoid X
```

**Keep concise**: <100 lines (added to context on every edit)

---

## Project Overrides

To customize for one project:
1. Copy global file to `{project}/.claude/instructions/`
2. Modify rules
3. Same filename = override

**Example**: Project file wins over global if names match.

---

## Benefits

- **Consistency**: Standards applied uniformly
- **Customization**: Project-specific overrides
- **Auto-Config**: New instances get standards
- **Context Efficiency**: Only loads for relevant files

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Instructions not applying | Check `applyTo` glob matches file path, verify YAML valid |
| Project override not working | Filenames must match exactly (case-sensitive) |
| Hook not firing | Check PreToolUse in settings.local.json |

---

## Implementation

**Hook**: PreToolUse in `.claude/settings.local.json`
**Script**: `scripts/instruction_matcher.py`
**Method**: `additionalContext` injection

---

## Related

- [[Documentation Philosophy]] - Why structure matters
- [[Claude Hooks]] - All hooks
- [[Settings File]] - Hook configuration

---

**Version**: 3.0 (Condensed)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: Claude Family/Auto-Apply Instructions.md
