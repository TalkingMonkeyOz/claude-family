---
projects:
- claude-family
tags:
- system
- instructions
- automation
synced: false
---

# Coding Standards System

Two systems for automatically injecting coding standards into Claude's context.

---

## Overview

| System | Location | Source | Auto-Update |
|--------|----------|--------|-------------|
| **Database-Driven** | `~/.claude/standards/` | `claude.coding_standards` table | `generate_standards.py` |
| **Native Instructions** | `~/.claude/instructions/` | Manual files | No |

Both inject into Claude's context when editing matching files.

---

## Database-Driven Standards (Primary)

**12 standards** in `claude.coding_standards` table, auto-generated to `~/.claude/standards/`.

| Category | Standards |
|----------|-----------|
| core | markdown-documentation |
| language | csharp, typescript, rust |
| framework | react, mui, azure-bicep, azure-functions, azure-logic-apps |
| pattern | security-aspnet, docker, github-actions |

**Regenerate**: `python scripts/generate_standards.py`

**Add new**: Insert into `claude.coding_standards` table, then regenerate.

---

## Native Instructions (Legacy)

**9 files** in `~/.claude/instructions/` for Claude Code native loading.

| File                                  | Applies To              | Purpose                         |
| ------------------------------------- | ----------------------- | ------------------------------- |
| `csharp.instructions.md`              | `**/*.cs`               | C# conventions, async patterns  |
| `markdown.instructions.md`            | `**/*.md`               | Doc standards (size, structure) |
| `a11y.instructions.md`                | `**/*.cs`, `**/*.tsx`   | WCAG AA accessibility           |
| `sql-postgres.instructions.md`        | `**/*.sql`              | PostgreSQL best practices       |
| `playwright.instructions.md`          | `**/*.spec.ts`          | E2E testing patterns            |
| `winforms.instructions.md`            | `**/*.Designer.cs`      | WinForms layout                 |
| `winforms-dark-theme.instructions.md` | `**/*Form.cs`           | Dark theme colors               |
| `wpf-ui.instructions.md`              | `**/*.xaml`             | WPF UI patterns                 |
| `mvvm.instructions.md`                | `**/ViewModels/**/*.cs` | MVVM architecture               |

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

**Version**: 4.0 (Database-driven standards added)
**Created**: 2025-12-26
**Updated**: 2026-01-04
**Location**: Claude Family/Auto-Apply Instructions.md
