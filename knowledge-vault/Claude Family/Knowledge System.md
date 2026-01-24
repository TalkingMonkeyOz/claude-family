---
projects:
- claude-family
synced: false
synced_at: '2025-12-27T00:00:00.000000'
tags:
- knowledge
- architecture
- system
---

# Knowledge System

Captures, stores, and delivers institutional knowledge across sessions.

**Flow**: CAPTURE (Obsidian) → STORE (PostgreSQL) → DELIVER (Hooks)

---

## Components

### 1. Obsidian Vault (Source)

**Location**: `C:\Projects\claude-family\knowledge-vault\`

| Folder | Purpose |
|--------|---------|
| `00-Inbox/` | Quick capture |
| `10-Projects/` | Project-specific docs |
| `20-Domains/` | Domain knowledge (API, DB) |
| `30-Patterns/` | Gotchas, solutions |
| `40-Procedures/` | SOPs, workflows |
| `Claude Family/` | System docs |

### 2. Sync Script

**Script**: `scripts/sync_obsidian_to_db.py`

Syncs markdown → `claude.knowledge` table:
- Parses YAML frontmatter
- Extracts content
- Upserts on change
- Tracks sync status

```bash
# Dry run
python scripts/sync_obsidian_to_db.py --dry-run

# Sync
python scripts/sync_obsidian_to_db.py

# Force resync all
python scripts/sync_obsidian_to_db.py --force
```

### 3. RAG System (Delivery)

**Script**: `scripts/rag_query_hook.py`
**Hook**: UserPromptSubmit

On prompt submit:
1. Query `claude.knowledge` embeddings (Voyage AI)
2. Query `claude.vault_embeddings` for vault docs
3. Inject relevant context (top 2 knowledge + top 3 vault)
4. Log retrieval to `rag_usage_log`

**Note**: Process router (process_registry) is deprecated. Skills system replaced it.

---

## Data Flow

```
Obsidian Vault (edit .md files)
    ↓
embed_vault_documents.py (Voyage AI embeddings)
    ↓
claude.vault_embeddings + claude.knowledge (PostgreSQL)
    ↓
rag_query_hook.py (UserPromptSubmit hook)
    ↓
Claude Session (context injection)
```

---

## Frontmatter Requirements

```yaml
---
projects:
- claude-family
tags:
- knowledge
synced: false            # Managed by sync script
synced_at: '2025-12-20'  # Managed by sync script
---
```

**Required**: `projects` (array)
**Optional**: `tags`, `synced`, `synced_at`

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `claude.knowledge` | Vault content + embeddings |
| `claude.vault_embeddings` | Document chunk embeddings |
| `claude.rag_usage_log` | RAG query tracking |
| `claude.skill_content` | Skills repository |

**Deprecated**: `process_registry`, `process_triggers` (replaced by skills system)

**Quick queries**:
```sql
-- Knowledge for project
SELECT title, knowledge_type
FROM claude.knowledge
WHERE 'claude-family' = ANY(applies_to_projects);

-- Recent retrievals
SELECT query_text, matched_knowledge
FROM claude.knowledge_retrieval_log
ORDER BY retrieved_at DESC LIMIT 10;
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Knowledge not showing | Run `embed_vault_documents.py` |
| Wrong project filter | Add `projects:` to YAML |
| Low RAG similarity | Check embedding quality in `rag_usage_log` |
| Hook not running | Check `.claude/settings.json` |

---

## Related

- [[Purpose]] - Vault structure
- [[Database Architecture]] - Schema
- [[Claude Hooks]] - Hook config
- [[Documentation Standards]] - Writing docs

---

**Version**: 2.1 (RAG system update, removed process_registry refs)
**Created**: 2025-12-20
**Updated**: 2026-01-19
**Location**: knowledge-vault/Claude Family/Knowledge System.md
