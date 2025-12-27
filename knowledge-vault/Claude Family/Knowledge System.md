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

### 3. Process Router (Delivery)

**Script**: `scripts/process_router.py`
**Hook**: UserPromptSubmit

On prompt submit:
1. Check `process_triggers` (regex)
2. LLM classification fallback
3. Inject workflow guidance
4. Log retrieval

---

## Data Flow

```
Obsidian Vault (edit .md files)
    ↓
sync_obsidian_to_db.py
    ↓
claude.knowledge (PostgreSQL)
    ↓
process_router.py (UserPromptSubmit hook)
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
| `claude.knowledge` | Vault content |
| `claude.knowledge_retrieval_log` | Query tracking |
| `claude.process_registry` | Workflow definitions |
| `claude.process_triggers` | Keyword/regex triggers |

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
| Knowledge not showing | Run `sync_obsidian_to_db.py` |
| Wrong project filter | Add `projects:` to YAML |
| Process not triggering | Add pattern to `process_triggers` |
| Hook not running | Check `.claude/settings.json` |

---

## Related

- [[Purpose]] - Vault structure
- [[Database Architecture]] - Schema
- [[Claude Hooks]] - Hook config
- [[Documentation Standards]] - Writing docs

---

**Version**: 2.0 (Condensed)
**Created**: 2025-12-20
**Updated**: 2025-12-27
**Location**: knowledge-vault/Claude Family/Knowledge System.md
