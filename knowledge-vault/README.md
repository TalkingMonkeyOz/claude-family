# Claude Family Knowledge Vault

**Type:** Obsidian vault with RAG embeddings
**Purpose:** Centralized knowledge repository for all Claude Family members
**Last Updated:** 2025-12-30

---

## Overview

The Knowledge Vault is the **single source of truth** for all Claude Family knowledge, patterns, procedures, and domain expertise. It uses Obsidian for editing and has RAG embeddings via Voyage AI for semantic search.

### RAG System Status

- ✅ **115 documents embedded** (88 vault + 27 project docs)
- ✅ **1,097 chunks indexed**
- ✅ **642 KB searchable text**
- ✅ **85% token reduction** (use RAG instead of loading full docs)
- ✅ **File versioning** for smart incremental updates

---

## Folder Structure

### Core Numbered Folders (Johnny Decimal Inspired)

```
knowledge-vault/
├── 00-Inbox/          Quick capture for new information
├── 10-Projects/       Project-specific knowledge and documentation
├── 20-Domains/        Domain expertise (APIs, databases, frameworks, etc.)
├── 30-Patterns/       Reusable patterns, gotchas, and solutions
└── 40-Procedures/     SOPs, workflows, and Family Rules (governance)
```

### Supporting Folders

```
knowledge-vault/
├── _templates/        Obsidian note templates
├── .obsidian/         Obsidian configuration (workspace, plugins)
├── Claude Family/     Meta-documentation about the vault itself
├── 40-Sessions/       Historical session notes (consider archiving)
├── 50-Archive/        Old or deprecated content
└── John's Notes/      User personal notes (not shared knowledge)
```

### Ad-Hoc Project Folders

```
knowledge-vault/
├── HTMX test for claude manager/    Experimental project notes
└── [Other temporary project folders]
```

---

## Folder Details

### 00-Inbox - Quick Capture

**Purpose:** Temporary holding area for new information that needs processing

**Contents:**
- Quick notes during sessions
- Ideas to be organized later
- Information to be moved to proper folders

**Maintenance:** Should be regularly reviewed and emptied (move to proper locations)

---

### 10-Projects - Project-Specific Knowledge

**Purpose:** Knowledge specific to individual projects

**Structure:**
```
10-Projects/
├── Claude Family Manager.md
├── claude-family/
│   ├── Identity System - Overview.md
│   └── Identity System - Implementation.md
└── [Other project folders]
```

**Contents:**
- Project architecture notes
- Implementation decisions
- Project-specific patterns
- Setup guides

---

### 20-Domains - Domain Expertise

**Purpose:** Reusable knowledge about technologies, frameworks, and domains

**Structure:**
```
20-Domains/
├── APIs/
│   ├── nimbus-rest-crud-pattern.md
│   ├── nimbus-odata-field-naming.md
│   └── nimbus-idorfilter-patterns.md
├── WinForms/
│   ├── winforms-async-patterns.md
│   ├── winforms-databinding.md
│   ├── winforms-designer-rules.md
│   └── winforms-layout-patterns.md
├── Database Architecture.md
├── Claude Code Hooks.md
├── Infrastructure Stats and Monitoring.md
└── MCP Server Management.md
```

**Contents:**
- Technology patterns and best practices
- Framework-specific knowledge
- API integration patterns
- Common gotchas and solutions

---

### 30-Patterns - Reusable Patterns

**Purpose:** Cross-domain patterns, techniques, and gotchas

**Contents:**
- Design patterns
- Common problem solutions
- Anti-patterns to avoid
- Lessons learned

**Note:** Currently light on content - good opportunity to capture more patterns

---

### 40-Procedures - SOPs and Governance

**Purpose:** Standard Operating Procedures and Family Rules

**Key Files:**
- `Family Rules.md` - **MANDATORY READ** - Claude Family coordination rules
- `Add MCP Server SOP.md` - How to add new MCP servers
- `Config Management SOP.md` - Database-driven configuration management
- `New Project SOP.md` - How to set up new projects
- `Vault Embeddings Management SOP.md` - RAG system maintenance
- `Documentation Standards.md` - How to write documentation

**Contents:**
- Mandatory workflows
- Best practices
- Step-by-step guides
- Governance rules

---

### Claude Family - Meta Documentation

**Purpose:** Documentation about the vault system itself and Claude Family infrastructure

**Key Files:**
- `Purpose.md` - Vault overview and philosophy
- `Claude Hooks.md` - Hook system documentation
- `Claude Tools Reference.md` - Available MCP tools
- `MCP Registry.md` - Registered MCP servers
- `MCP configuration.md` - MCP setup details
- `RAG Usage Guide.md` - How to use semantic search
- `Settings File.md` - Configuration management

**Contents:**
- System architecture
- How-to guides for using the vault
- Tool references

---

### 40-Sessions - Historical Session Notes

**Purpose:** Historical session summaries and notes

**Status:** ⚠️ **Consider Archiving**
- Session data now stored in `claude.sessions` database table
- May be redundant with database tracking
- Recommend moving to `50-Archive/` or removing

---

### 50-Archive - Deprecated Content

**Purpose:** Old content that's no longer current but kept for reference

**Contents:**
- Superseded documentation
- Old project notes
- Historical decisions

---

### John's Notes - Personal Notes

**Purpose:** User's personal notes not intended for shared knowledge base

**Status:** Personal - not embedded in RAG system

---

## Using the Vault

### For Knowledge Capture

1. **Quick notes** → `00-Inbox/`
2. **Project-specific** → `10-Projects/{project-name}/`
3. **Reusable tech knowledge** → `20-Domains/{technology}/`
4. **Patterns and gotchas** → `30-Patterns/`
5. **Procedures and rules** → `40-Procedures/`

### For Knowledge Retrieval

**Use RAG (Recommended):**
```python
# Via vault-rag MCP
semantic_search(query="how do I add an MCP server")
```

**Direct file access:**
- Navigate folders in Obsidian
- Use Claude Code Read tool
- Search by tags

---

## YAML Frontmatter Standard

All vault documents should include:

```yaml
---
synced: true
synced_at: '2025-12-30T12:00:00'
tags:
  - domain/technology
  - pattern/specific-type
projects:
  - project-name
---
```

**Fields:**
- `synced`: Whether document is synced to RAG
- `synced_at`: Last sync timestamp
- `tags`: Categorization tags
- `projects`: Related project UUIDs or names

---

## Maintenance

### Regular Tasks

1. **Empty 00-Inbox/** - Move notes to proper folders
2. **Update embeddings** - Run `python scripts/embed_vault_documents.py`
3. **Review 40-Sessions/** - Archive or remove old sessions
4. **Update frontmatter** - Ensure all docs have proper YAML

### Embedding Updates

```bash
# Incremental update (only changed files)
python scripts/embed_vault_documents.py

# Force re-embed everything
python scripts/embed_vault_documents.py --force
```

See `40-Procedures/Vault Embeddings Management SOP.md` for details.

---

## Best Practices

1. **One topic per file** - Keep documents focused
2. **Use descriptive names** - `winforms-databinding.md` not `notes.md`
3. **Add frontmatter** - Tags and metadata help retrieval
4. **Link related content** - Use `[[wiki-links]]` between documents
5. **Update, don't duplicate** - Edit existing docs rather than create new ones
6. **Use templates** - Start new docs from `_templates/`

---

## Statistics (2025-12-30)

- **Total folders:** 12 (9 numbered + 3 supporting)
- **Core folders:** 5 (00, 10, 20, 30, 40)
- **Documents:** 115 (88 vault + 27 project)
- **RAG chunks:** 1,097
- **Coverage:** 85% token reduction

---

## Questions?

- See `Claude Family/Purpose.md` for vault philosophy
- See `Claude Family/RAG Usage Guide.md` for search tips
- See `40-Procedures/Family Rules.md` for governance
- Ask in Claude Family chat

---

**Last Audit:** 2025-12-30
**Next Review:** 2026-01-06
