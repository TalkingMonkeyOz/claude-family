---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T23:29:45.919068'
tags:
- standards
- documentation
- procedures
---

# Documentation Standards

Standards for creating and maintaining documentation across the Claude Family ecosystem.

---

## Document Locations

| Type | Location | When to Use |
|------|----------|-------------|
| **Vault docs** | `knowledge-vault/` | Persistent knowledge, cross-session reference |
| **Project docs** | `docs/` | Project-specific plans, specs, SOPs |
| **CLAUDE.md** | Project root | AI constitution, quick reference |
| **Code comments** | Source files | Implementation-specific notes |

### Decision Guide

```
Is this knowledge reusable across sessions?
├── YES → Put in Vault
│         ├── Domain knowledge? → 20-Domains/
│         ├── Reusable pattern? → 30-Patterns/
│         ├── Procedure/SOP? → 40-Procedures/
│         └── Project-specific? → 10-Projects/
│
└── NO → Put in docs/
         ├── Architectural decision? → docs/adr/
         ├── Standard operating procedure? → docs/sops/
         ├── Development standard? → docs/standards/
         └── Project plan/spec? → docs/ (root)
```

---

## Vault Structure

| Folder | Purpose | Naming Pattern |
|--------|---------|----------------|
| `00-Inbox/` | Quick capture, unsorted | Any |
| `10-Projects/` | Project-specific knowledge | `{project-name}/topic.md` |
| `20-Domains/` | Domain expertise | `{domain}/topic.md` |
| `30-Patterns/` | Reusable patterns | `gotchas/*.md`, `solutions/*.md` |
| `40-Procedures/` | SOPs, workflows | `{procedure-name}.md` |
| `Claude Family/` | Core system docs | `{Component Name}.md` |
| `_templates/` | Document templates | Not synced |

---

## Frontmatter Standard

Every vault document MUST have YAML frontmatter:

```yaml
---
projects:
- claude-family        # Required: which projects this applies to
- other-project        # Can list multiple
tags:
- reference            # Optional: searchable tags
- database
synced: false          # Managed by sync script
synced_at: ''          # Managed by sync script
---
```

### Frontmatter Rules

1. **Always include `projects:`** - Required for filtering
2. **Use lowercase project names** - Match database values
3. **Don't manually edit `synced` fields** - Managed by sync script
4. **Tags are optional** - Use for additional discoverability

---

## Document Structure

### Standard Template

```markdown
---
projects:
- claude-family
tags:
- topic
synced: false
---

# Document Title

Brief description (1-2 sentences).

---

## Overview

High-level summary. What is this? Why does it matter?

---

## Section 1

Content with tables, code blocks, lists.

---

## Section 2

More content.

---

## Related Documents

- [[Related Doc 1]] - Brief description
- [[Related Doc 2]] - Brief description

---

**Version**: 1.0
**Created**: YYYY-MM-DD
**Updated**: YYYY-MM-DD
**Location**: path/to/this/file.md
```

### Structure Guidelines

1. **Start with overview** - Quick context for readers
2. **Use horizontal rules** - `---` between major sections
3. **Include tables** - For structured data, quick reference
4. **Add code examples** - Practical, copy-pasteable
5. **End with related docs** - Wiki-links for navigation
6. **Include version footer** - Track changes

---

## Naming Conventions

### File Names

| Pattern | Example | Use For |
|---------|---------|---------|
| `Title Case.md` | `Knowledge System.md` | Main concept docs |
| `kebab-case.md` | `api-patterns.md` | Technical reference |
| `UPPERCASE.md` | `ARCHITECTURE.md` | Project docs only |

### Wiki-Links

Use `[[Document Name]]` for internal links:

```markdown
See [[Knowledge System]] for details.
```

Link to specific sections with `#`:

```markdown
See [[Database Architecture#Sessions]]
```

---

## Writing Style

### Principles

1. **Scannable** - Use tables, bullet points, headers
2. **Actionable** - Include examples, commands, code
3. **Linked** - Reference related docs with wiki-links
4. **Versioned** - Update version footer on changes

### Formatting

| Element | Format | Example |
|---------|--------|---------|
| Commands | Backticks | `python script.py` |
| File paths | Backticks | `docs/standards/` |
| Table names | Backticks | `claude.knowledge` |
| Document refs | Wiki-links | `[[Document Name]]` |
| Code blocks | Triple backticks | With language hint |

---

## Document Lifecycle

### Create

1. Check if doc already exists (search vault first)
2. Create in appropriate folder
3. Add frontmatter with `projects:` array
4. Write content following template
5. Add wiki-links to related docs
6. Run sync: `python scripts/sync_obsidian_to_db.py`

### Update

1. Make edits in Obsidian or editor
2. Update `Version` in footer
3. Update `Updated` date
4. Re-sync if content changed: `python scripts/sync_obsidian_to_db.py`

### Archive

1. Move to `docs/archive/YYYY-MM/` folder
2. Add note to top: `> **Archived**: Superseded by X`
3. Remove from vault (if it was synced)

---

## Project Docs vs Vault Docs

| Aspect | Project Docs (`docs/`) | Vault Docs (`knowledge-vault/`) |
|--------|------------------------|--------------------------------|
| **Scope** | Single project | Cross-project |
| **Lifetime** | May become stale | Evergreen |
| **Synced to DB** | No | Yes |
| **Format** | Any markdown | YAML frontmatter required |
| **Examples** | Plans, specs, ADRs | Patterns, gotchas, procedures |

### When to Consolidate

Move project doc to vault when:
- It's referenced by multiple projects
- It contains reusable patterns
- It's a procedure others should follow

---

## Related Documents

- [[Knowledge System]] - How vault syncs to database
- [[Knowledge Capture SOP]] - Step-by-step capture process
- [[Purpose]] - Vault overview

---

**Version**: 1.0
**Created**: 2025-12-20
**Updated**: 2025-12-20
**Location**: knowledge-vault/40-Procedures/Documentation Standards.md