---
projects:
- claude-family
tags:
- documentation
- philosophy
- ai-research
synced: false
---

# Documentation Philosophy

**Key Insight**: Shorter documents with hierarchical links outperform large monolithic files
**Based on**: Stanford research (Liu et al. 2023) - "Lost in the Middle"

---

## The Problem: Lost in the Middle

LLMs exhibit **primacy and recency bias**:
- **Beginning**: HIGH attention ✅
- **End**: HIGH attention ✅
- **Middle**: LOW attention ❌ ← Information gets lost

**Research**:
- GPT-3.5-turbo: 20% accuracy drop with 30 docs vs 5
- Pinecone RAG: 95% accuracy using only 25% of tokens

**Solution**: Better structure, not bigger context

---

## Our Approach: 4-Layer Hierarchy

```
LAYER 1: CLAUDE.md (≤250 lines, project index)
    ↓
LAYER 2: Claude Family/ (≤150 lines, quick-refs)
    ↓
LAYER 3: Deep docs (≤300 lines, detailed guides)
    ↓
LAYER 4: PostgreSQL (searchable, versioned)
```

**Result**: Info always at beginning/end of context, never middle

---

## Core Principles

### 1. Keep Documents Short

| Type | Max Lines | Purpose |
|------|-----------|---------|
| CLAUDE.md | 250 | Project index |
| Quick-ref | 150 | Overview |
| Detailed | 300 | Deep dive |
| Working | 100 | TODO, plans |

### 2. Link, Don't Embed

**Bad**: Duplicate content across files
**Good**: Link to source of truth

```markdown
See [[Database Architecture]] for schema and
[[Family Rules#Database]] for procedures.
```

### 3. Self-Contained Chunks

- Don't reference "above" (Claude may read doc directly)
- Include enough context to understand standalone
- Link to related docs for depth

### 4. Version Everything

```markdown
---
**Version**: 1.0
**Created**: YYYY-MM-DD
**Updated**: YYYY-MM-DD
**Location**: path/to/file.md
```

---

## Document Types

| Type | Max Lines | Location |
|------|-----------|----------|
| Quick-ref | 150 | `Claude Family/` |
| Detailed | 300 | `10-Projects/`, `20-Domains/` |
| Procedure | 300 | `40-Procedures/` |
| Pattern | 200 | `30-Patterns/` |

---

## Core Files (Every Project)

1. **CLAUDE.md** - AI constitution
2. **PROBLEM_STATEMENT.md** - Problem definition
3. **ARCHITECTURE.md** - System design
4. **README.md** - Human overview

---

## Enforcement

**Auto-Apply Instructions**: `markdown.instructions.md` auto-injects on file edits

See [[Auto-Apply Instructions]] for details.

---

## Benefits

1. **Discoverability**: Info at edges, not middle
2. **Maintainability**: Small docs easier to update
3. **Context Efficiency**: Load only what's needed
4. **Consistency**: Standards enforced automatically
5. **Collaboration**: Fewer merge conflicts

---

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Large monolithic files | Split into linked docs |
| Duplicate content | Link to source of truth |
| Vague headings | Use descriptive titles |
| Missing version footers | Add footer to all .md |

---

## Related

- [[Auto-Apply Instructions]] - Enforcement system
- [[Documentation Standards]] - Vault standards
- [[Session Architecture]] - Example structure
- [[Purpose]] - Vault overview

---

**Version**: 2.0 (Condensed)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: knowledge-vault/Claude Family/Documentation Philosophy.md
