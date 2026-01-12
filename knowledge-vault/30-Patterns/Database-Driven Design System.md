---
projects:
  - claude-manager-mui
  - claude-family
tags:
  - design-system
  - mui
  - database-driven
  - patterns
synced: true
---

# Database-Driven Design System Pattern

## Overview

Store design system rules in `claude.coding_standards` and auto-generate to `~/.claude/standards/` for consistent UI guidance across sessions.

## Implementation

### 1. Database Record

```sql
INSERT INTO claude.coding_standards (
    name,
    category,
    file_path,
    description,
    applies_to_patterns,
    content,
    priority,
    active
) VALUES (
    'mui-design-system',
    'framework',  -- Valid: core, pattern, language, framework
    'framework/mui-design-system.md',
    'MUI design system - colors, typography, spacing',
    ARRAY['**/*.tsx', '**/*.ts'],
    '# Your design system content here...',
    10,
    true
);
```

### 2. Generate File

```bash
python scripts/generate_standards.py
```

Creates: `~/.claude/standards/framework/mui-design-system.md`

### 3. Reference in Project CLAUDE.md

```markdown
## Coding Standards (Auto-Loaded)

@~/.claude/standards/framework/mui-design-system.md
```

## Benefits

- **Self-healing**: Regenerates on SessionStart
- **Consistent**: Same design rules across all sessions
- **Centralized**: Edit database, files update automatically
- **Discoverable**: Standards auto-apply based on file patterns

## Current Implementation

**Project**: claude-manager-mui
**Standard ID**: `9a53b0b3-b41c-496a-8e5d-6ccc8936d9ea`
**File**: `~/.claude/standards/framework/mui-design-system.md`

Contains:
- Color palette (light/dark mode)
- Typography scale
- Spacing grid (8px base)
- Component patterns
- DON'Ts list

## Related

- [[Config Management SOP]] - How database-driven config works
- [[Vault Embeddings Management SOP]] - RAG integration

---

**Version**: 1.0
**Created**: 2026-01-11
**Updated**: 2026-01-11
**Location**: knowledge-vault/30-Patterns/Database-Driven Design System.md
