---
description: 'Global documentation standards for all markdown files'
applyTo: '**/*.md'
source: 'AI-readable documentation research (Liu et al. 2023, Anthropic best practices)'
---

# Markdown Documentation Standards

## Core Principles

1. **Keep it short** - Target 250-500 tokens per document (~1000-2000 characters)
2. **Link don't embed** - Reference other docs, don't duplicate content
3. **Self-contained chunks** - Each document makes sense alone
4. **Version everything** - Track changes with footer metadata

## File Size Limits

| File Type | Max Lines | Max Tokens | Purpose |
|-----------|-----------|------------|---------|
| CLAUDE.md | 250 | ~1000 | AI constitution |
| Quick-ref | 150 | ~500 | One-pager overview |
| Detailed | 300 | ~1200 | Deep dive |
| Working (TODO, plans) | 100 | ~400 | Temporal files |

**Why?** Research shows LLMs suffer from "lost in the middle" problem - information in the middle of long documents gets missed. Shorter, linked documents are more discoverable.

## Required Footer (All .md files)

Every markdown file MUST end with a version footer:

```markdown
---
**Version**: X.Y
**Created**: YYYY-MM-DD
**Updated**: YYYY-MM-DD
**Location**: path/to/file.md
```

- Increment minor version (0.1 → 0.2) for small changes
- Increment major version (1.0 → 2.0) for restructuring/major updates
- Update the **Updated** date every time you edit

## YAML Frontmatter (Vault documents)

Documents in `knowledge-vault/` MUST have YAML frontmatter:

```yaml
---
projects:
- project-name
tags:
- relevant-tags
---
```

## Document Types

| Type | Purpose | Location | Max Lines |
|------|---------|----------|-----------|
| **Quick-ref** | One-pager overview | `Claude Family/` | 150 |
| **Detailed** | Deep dive | `10-Projects/`, `20-Domains/` | 300 |
| **Procedure** | How-to steps | `40-Procedures/` | 300 |
| **Pattern** | Reusable solution | `30-Patterns/` | 200 |
| **Working** | Temporal (TODO, plans) | `docs/` | 100 |
| **Core** | Essential project file | Project root | 250 |

## Core Files (Every Project)

Every project MUST have these 4 files in the root:

1. **CLAUDE.md** - AI constitution (≤250 lines)
2. **PROBLEM_STATEMENT.md** - What, for whom, why
3. **ARCHITECTURE.md** - System design overview
4. **README.md** - Human-friendly overview

## Linking Strategy

- **Internal links**: Use wiki-links `[[Document Name]]` for vault docs
- **Section links**: Reference sections with `[[Document#Section]]`
- **External links**: Use markdown links `[Text](path/to/file.md)`
- **Don't duplicate**: Link to detailed docs instead of copying content

## Headers and Structure

- Use descriptive headers, not vague ones ("Session Lifecycle" not "Overview")
- Use `---` horizontal rules to separate major sections
- Use tables for structured data (easier to scan than prose)
- Put critical info first or last (beginning and end have highest attention)

## Avoid

- ❌ Large monolithic files (>300 lines)
- ❌ Duplicate content across multiple docs
- ❌ Vague headings ("Overview", "Details", "More")
- ❌ Context-dependent docs that can't stand alone
- ❌ Missing version footers
- ❌ Burying important info in the middle

## When Creating New Docs

Before creating a new document, ask:
1. Does this already exist? (Search vault and docs/ first)
2. Is this reusable knowledge? → `knowledge-vault/`
3. Is this project-specific? → `docs/`
4. Is this temporal? → Working file in `docs/`, keep it small
5. Can I link to existing docs instead of duplicating?

## Testing Your Docs

After writing, test discoverability:
- Can Claude find the info with a natural question?
- Is each section self-contained?
- Are links working and relevant?
- Is the document ≤ target size?

If Claude can't find it, restructure or add better cross-links.

---

**Based on:** "Lost in the Middle: How Language Models Use Long Contexts" (Liu et al. 2023), Anthropic Context Engineering for AI Agents
