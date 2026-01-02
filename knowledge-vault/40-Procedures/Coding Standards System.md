---
title: Coding Standards System
type: procedure
created: 2026-01-02
updated: 2026-01-02
tags: [standards, hooks, database, enforcement]
status: active
---

# Coding Standards System

## Overview

Database-driven coding standards system that automatically applies language, framework, and pattern-specific standards to Claude Code across ALL projects.

## Architecture

```
Database (claude.coding_standards)
    ↓
SessionStart: generate_standards.py
    ↓
~/.claude/standards/ (generated files)
    ↓
CLAUDE.md @import directives (awareness)
    ↓
PreToolUse hooks: standards_validator.py (enforcement)
```

## Components

### 1. Database (Source of Truth)

**Table**: `claude.coding_standards`

**Schema**:
- `standard_id`: UUID primary key
- `category`: core | language | framework | pattern
- `name`: Human-readable name
- `file_path`: Relative path in ~/.claude/standards/
- `content`: Full markdown content
- `applies_to_patterns`: Array of glob patterns (**/*.md, **/*.cs)
- `validation_rules`: JSONB with max_lines, forbidden_patterns, etc.
- `active`: Boolean (allows soft-delete)
- `priority`: Integer (lower = higher priority)
- `description`: Short summary

### 2. File Generation (Self-Healing)

**Script**: `C:/Projects/claude-family/scripts/generate_standards.py`

**Runs**: Automatically on SessionStart hook

**Output**: `~/.claude/standards/`
```
~/.claude/standards/
├── README.md (auto-generated index)
├── core/
│   └── markdown-documentation.md
├── language/
│   ├── csharp.md
│   ├── typescript.md
│   └── rust.md
├── framework/
│   ├── react.md
│   ├── mui.md
│   └── azure-bicep.md
└── pattern/
    ├── security-aspnet.md
    ├── docker.md
    └── github-actions.md
```

**Self-Healing**: Files regenerate from database every session. Manual edits are temporary.

### 3. Awareness Layer (CLAUDE.md @imports)

**Global** (~/.claude/CLAUDE.md):
```markdown
## Coding Standards (Auto-Loaded)

@~/.claude/standards/core/markdown-documentation.md
```

**Project-Specific** (e.g., nimbus-mui/CLAUDE.md):
```markdown
## Coding Standards (Auto-Loaded)

@~/.claude/standards/core/markdown-documentation.md
@~/.claude/standards/language/typescript.md
@~/.claude/standards/language/rust.md
@~/.claude/standards/framework/react.md
@~/.claude/standards/framework/mui.md
```

**Loading**: Standards loaded at SessionStart via @import syntax

### 4. Enforcement Layer (Block-and-Correct)

**Script**: `C:/Projects/claude-family/scripts/standards_validator.py`

**Hook**: PreToolUse (Write/Edit operations)

**Pattern**: Block-and-correct
- Exit code 0: Operation allowed (passes validation)
- Exit code 2: Operation BLOCKED (Claude sees error, adjusts, retries)
- stderr: Helpful error message explaining violation

**Validations**:
1. **File size limits** (by file type):
   - Detailed docs: 300 lines max
   - Quick reference: 150 lines max
   - Working files (TODO, plans): 100 lines max
2. **Forbidden patterns** (future):
   - .unwrap() in Rust
   - hardcoded secrets
   - unvalidated SQL
3. **Required patterns** (future):
   - XML comments on C# public APIs
   - @description in Bicep
   - USER directive in Dockerfiles

## Current Standards (10 total)

### Core (1)
- **Markdown Documentation**: File size limits, structure, cross-references

### Language (3)
- **C#**: Naming conventions, async patterns, LINQ, XML comments
- **TypeScript**: No `any`, async/await, type safety, security
- **Rust**: Ownership, Result<T,E>, rustfmt/clippy, no unwrap

### Framework (3)
- **React**: Hooks, dependency arrays, memoization, component patterns
- **MUI**: Theming, sx prop, responsive design, accessibility
- **Azure Bicep**: IaC best practices, symbolic names, security, RBAC

### Pattern (3)
- **Security & ASP.NET APIs**: JWT, OWASP Top 10, input validation, RFC 7807
- **Docker**: Multi-stage builds, non-root user, scanning, optimization
- **GitHub Actions CI/CD**: Security, caching, matrix builds, OIDC

## How to Add a New Standard

### 1. Insert into Database

```sql
INSERT INTO claude.coding_standards (
    category, name, file_path, content, applies_to_patterns,
    validation_rules, active, priority, description
) VALUES (
    'language',  -- or 'framework', 'pattern', 'core'
    'Go',
    'language/go.md',
    '# Go Programming Standards...',
    ARRAY['**/*.go'],
    '{"required_patterns": ["gofmt", "go vet"]}'::jsonb,
    true,
    20,
    'Go programming standards - formatting, error handling, concurrency'
);
```

### 2. Regenerate Files

```bash
python C:/Projects/claude-family/scripts/generate_standards.py
```

Or wait for next SessionStart (auto-regenerates).

### 3. Update Project CLAUDE.md Files

Add @import directive for relevant projects:

```markdown
@~/.claude/standards/language/go.md
```

### 4. Test Enforcement

1. Restart Claude Code (loads new hook config)
2. Try violating a validation rule
3. Verify operation is BLOCKED with helpful error
4. Fix the violation and retry

## Common Operations

### View All Standards

```sql
SELECT category, name, file_path, active, priority
FROM claude.coding_standards
ORDER BY category, priority, name;
```

### Disable a Standard (Soft Delete)

```sql
UPDATE claude.coding_standards
SET active = false
WHERE name = 'Standard Name';
```

Then regenerate files.

### Update Standard Content

```sql
UPDATE claude.coding_standards
SET content = '# Updated content...',
    updated_at = CURRENT_TIMESTAMP
WHERE name = 'Standard Name';
```

Then regenerate files.

### Add Validation Rule

```sql
UPDATE claude.coding_standards
SET validation_rules = validation_rules || '{"max_lines": 500}'::jsonb
WHERE name = 'Standard Name';
```

## Troubleshooting

### Standards not loading

1. Check `~/.claude/standards/` exists and has files
2. Run `python scripts/generate_standards.py` manually
3. Check SessionStart hook logs: `~/.claude/hooks.log`
4. Verify CLAUDE.md has @import directives

### Validation not blocking violations

1. Check PreToolUse hook configured in database:
   ```sql
   SELECT * FROM claude.config_templates WHERE template_name = 'hooks-base';
   ```
2. Restart Claude Code to load new hook config
3. Check `~/.claude/hooks.log` for validator execution
4. Old `instruction_matcher.py` may be conflicting (archive it)

### File created despite size limit

**Cause**: PreToolUse hook changes require session restart

**Fix**:
1. Archive old `instruction_matcher.py`
2. Restart Claude Code
3. Test again in new session

## Migration from Old System

### Old System (Deprecated)
- File-based: `~/.claude/instructions/*.instructions.md`
- Hook: `instruction_matcher.py` (additionalContext injection)
- **Problem**: additionalContext doesn't work in PreToolUse hooks

### New System (Active)
- Database-driven: `claude.coding_standards` table
- Hook: `standards_validator.py` (block-and-correct pattern)
- **Solution**: Exit code 2 + stderr forces Claude to see error and retry

### Archive Old Files

```bash
mv C:/Projects/claude-family/scripts/instruction_matcher.py C:/Projects/claude-family/scripts/_archived/
mv ~/.claude/instructions ~/.claude/_archived_instructions
```

**Note**: Do this AFTER session restart when new hooks are active.

## Sources

Standards sourced from:
- [GitHub Copilot Awesome](https://github.com/github/awesome-copilot) - Community best practices
- Anthropic Claude Code documentation
- Microsoft/.NET documentation
- OWASP Top 10
- Docker best practices
- GitHub Actions security guide

## Related Documents

- `knowledge-vault/Claude Family/Claude Hooks.md` - Hook system overview
- `knowledge-vault/40-Procedures/Session Lifecycle - Overview.md` - SessionStart flow
- `claude-family/docs/SESSION_SUMMARY_STANDARDS_SYSTEM.md` - Implementation details

---

**Version**: 1.0
**Created**: 2026-01-02
**Status**: Active
**Maintainer**: Claude Family Infrastructure
