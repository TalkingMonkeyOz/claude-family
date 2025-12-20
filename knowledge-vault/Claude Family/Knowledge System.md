---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T23:29:45.927007'
tags:
- knowledge
- architecture
- system
---

# Knowledge System

The Claude Family knowledge system captures, stores, and delivers institutional knowledge across sessions and instances.

---

## Overview

```
CAPTURE ──────> STORE ──────> DELIVER
(Obsidian)    (PostgreSQL)   (Hooks)
```

| Stage | Component | Purpose |
|-------|-----------|---------|
| Capture | Obsidian Vault | Human-readable markdown with YAML frontmatter |
| Store | `claude.knowledge` table | Queryable database storage |
| Deliver | Process Router Hook | Context injection at prompt time |

---

## Components

### 1. Obsidian Vault (Source of Truth)

**Location**: `C:\Projects\claude-family\knowledge-vault\`

| Folder | Purpose | Example |
|--------|---------|---------|
| `00-Inbox/` | Quick capture | Draft notes |
| `10-Projects/` | Project-specific | Claude Family Manager docs |
| `20-Domains/` | Domain knowledge | API patterns, DB architecture |
| `30-Patterns/` | Gotchas, solutions | Reusable patterns |
| `40-Procedures/` | SOPs, workflows | Family Rules |
| `Claude Family/` | Core system docs | Hooks, MCP, Orchestrator |

### 2. Sync Script

**Script**: `scripts/sync_obsidian_to_db.py`

Syncs vault markdown files to `claude.knowledge` table:
- Parses YAML frontmatter for metadata
- Extracts markdown content
- Upserts on change (update if exists, insert if new)
- Tracks sync status via `synced` frontmatter flag

```bash
# Dry run (see what would sync)
python scripts/sync_obsidian_to_db.py --dry-run

# Actually sync
python scripts/sync_obsidian_to_db.py

# Force resync everything
python scripts/sync_obsidian_to_db.py --force
```

### 3. Process Router (Delivery)

**Script**: `scripts/process_router.py`
**Hook**: `UserPromptSubmit`

When a user submits a prompt:
1. **TIER 1**: Check against `claude.process_triggers` (regex patterns)
2. **TIER 2**: If no match, LLM classification fallback
3. If match found, inject workflow guidance via `<process-guidance>` tag
4. Inject relevant standards (UI, API, DB) based on keywords
5. Log retrieval to `claude.knowledge_retrieval_log`

---

## Data Flow

```
┌──────────────────┐
│  Obsidian Vault  │  ← You edit markdown files here
│  (knowledge-vault/)
└────────┬─────────┘
         │ sync_obsidian_to_db.py
         ▼
┌──────────────────┐
│  claude.knowledge│  ← Database stores content + metadata
│  (PostgreSQL)    │
└────────┬─────────┘
         │ process_router.py (UserPromptSubmit hook)
         ▼
┌──────────────────┐
│  Claude Session  │  ← Knowledge delivered as context
│  (prompt context)│
└──────────────────┘
```

---

## Frontmatter Requirements

Every vault document should have YAML frontmatter:

```yaml
---
projects:
- claude-family          # Which projects this applies to
tags:
- knowledge              # Searchable tags
- reference
synced: false            # Set by sync script
synced_at: '2025-12-20'  # Set by sync script
---
```

**Required Fields:**
- `projects` - Array of project names (for filtering)

**Optional Fields:**
- `tags` - Array of searchable tags
- `synced` - Boolean (managed by sync script)
- `synced_at` - Timestamp (managed by sync script)

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `claude.knowledge` | Synced vault content |
| `claude.knowledge_retrieval_log` | Query tracking |
| `claude.process_registry` | Workflow definitions |
| `claude.process_triggers` | Keyword/regex triggers |
| `claude.enforcement_log` | When reminders fired |

```sql
-- Check what knowledge exists for a project
SELECT title, knowledge_type
FROM claude.knowledge
WHERE 'claude-family' = ANY(applies_to_projects)
ORDER BY updated_at DESC;

-- Check retrieval history
SELECT query_text, matched_knowledge, retrieved_at
FROM claude.knowledge_retrieval_log
ORDER BY retrieved_at DESC LIMIT 10;
```

---

## Verification

### Check Sync Status

```sql
-- Count synced vs unsynced
SELECT
  CASE WHEN source = 'obsidian' THEN 'vault' ELSE source END as source,
  COUNT(*)
FROM claude.knowledge
GROUP BY source;
```

### Check Process Triggers

```sql
-- Active triggers
SELECT t.trigger_pattern, p.process_name
FROM claude.process_triggers t
JOIN claude.process_registry p ON t.process_id = p.process_id
WHERE t.is_active = true
ORDER BY p.process_name;
```

### Test Knowledge Retrieval

1. Open a new Claude session
2. Ask about a topic covered in the vault
3. Check if `<process-guidance>` appears in response
4. Verify `claude.knowledge_retrieval_log` has entry

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Knowledge not showing | Not synced | Run `sync_obsidian_to_db.py` |
| Wrong project filter | Frontmatter missing | Add `projects:` to YAML |
| Process not triggering | No matching trigger | Add trigger pattern to `process_triggers` |
| Hook not running | Config issue | Check `.claude/settings.json` hooks config |

---

## Related Documents

- [[Purpose]] - Vault structure overview
- [[Database Architecture]] - Full schema reference
- [[Claude Hooks]] - Hook configuration
- [[Documentation Standards]] - How to write vault docs

---

**Version**: 1.0
**Created**: 2025-12-20
**Updated**: 2025-12-20
**Location**: knowledge-vault/Claude Family/Knowledge System.md