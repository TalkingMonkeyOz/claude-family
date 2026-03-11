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

**NEW (F177)**: Work Context Container (WCC) automatically detects activities and assembles context from 6 sources. See [[Project Tools MCP#Work Context Container]] for tools.

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
1. **Activity detection**: Check if user switched activities (session_fact override, name/alias match, word overlap, workfile component)
2. **If activity changed**: Assemble WCC context from 6 sources (workfiles, knowledge, features, facts, vault, BPMN)
3. **Otherwise**: Use cached WCC context (5-min TTL) or fall back to knowledge/vault RAG
4. Inject relevant context (WCC or knowledge + vault)
5. Log retrieval to `rag_usage_log`

**WCC behavior**: When active, per-source knowledge/vault queries SKIPPED (WCC replaces them). Token budget stays constant.

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
    ├─ detect_activity() → check session_fact, name/alias, word overlap, workfile
    └─ assemble_wcc() → query 6 sources in parallel (if activity changed)
    ↓
Claude Session (context injection — WCC or knowledge+vault)
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
| `claude.activities` | Named activities for WCC detection (NEW) |

**Deprecated**: `process_registry`, `process_triggers` (replaced by skills system)

**Quick queries**:
```sql
-- Knowledge for project
SELECT title, knowledge_type
FROM claude.knowledge
WHERE 'claude-family' = ANY(applies_to_projects);

-- Activities and access stats
SELECT name, aliases, (access_stats->>'access_count')::int as accesses
FROM claude.activities
WHERE project_id = (SELECT project_id FROM claude.projects WHERE project_name = 'claude-family')
ORDER BY (access_stats->>'last_accessed') DESC;

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
- [[Project Tools MCP]] - WCC tools reference
- [[RAG Usage Guide]] - WCC integration details

---

**Version**: 2.2 (Added Work Context Container - F177)
**Created**: 2025-12-20
**Updated**: 2026-03-10
**Location**: knowledge-vault/Claude Family/Knowledge System.md
**Changes**: Added WCC activity detection + assembly flow, activities table, activity query examples
