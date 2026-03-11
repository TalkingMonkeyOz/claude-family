---
title: Vault Embeddings Management SOP
tags: [sop, vault, embeddings, rag, maintenance]
created: 2025-12-30
updated: 2025-12-30
---

# Vault Embeddings Management SOP

## Purpose

Maintain up-to-date semantic search embeddings for the knowledge vault, enabling efficient RAG (Retrieval Augmented Generation) queries via the `vault-rag` MCP server.

## Overview

The vault embedding system:
- **Converts** markdown files to vector embeddings (Voyage AI, 1024 dimensions)
- **Stores** embeddings in PostgreSQL (`claude.vault_embeddings`)
- **Tracks** file versions via SHA256 hash and modification time
- **Enables** semantic search instead of loading all vault docs into context

**Key benefit**: 85% reduction in vault documentation tokens (only load relevant docs on-demand)

---

## File Versioning System

### How It Works

Each embedded document is tracked with:
- **`file_hash`**: SHA256 hash of file content
- **`file_modified_at`**: Filesystem modification timestamp
- **`created_at`**: When first embedded
- **`updated_at`**: When last re-embedded

The embedding script automatically:
1. Calculates current file hash
2. Compares with stored hash
3. **Skips** if unchanged
4. **Re-embeds** if content changed
5. **Deletes old chunks** and stores new embeddings

### Benefits

- ✅ Incremental updates (only changed files)
- ✅ No manual tracking needed
- ✅ Automatic staleness detection
- ✅ Cost savings (only re-embed what changed)

---

## When to Run Embeddings

### Initial Setup

After cloning or setting up a new environment:

```bash
cd C:/Projects/claude-family
export VOYAGE_API_KEY="your-key-here"
python scripts/embed_vault_documents.py
```

**Time**: ~5-10 minutes for full vault (88 files, ~768 chunks)
**Cost**: ~$0.30 (one-time via Voyage AI)

### After Vault Changes

Run embeddings after:
- Creating new vault documents
- Editing existing procedures, patterns, or domain knowledge
- Reorganizing vault structure
- Bulk imports from external sources

**The script is smart**: Only changed files will be re-embedded.

### Scheduled Maintenance

**Recommended**: Weekly or bi-weekly check:

```bash
# Dry run - shows what would be re-embedded
python scripts/embed_vault_documents.py --force --dry-run

# Update embeddings
python scripts/embed_vault_documents.py
```

---

## How to Update Embeddings

### Update All (Incremental)

Processes all vault files, skips unchanged:

```bash
cd C:/Projects/claude-family
export VOYAGE_API_KEY="your-api-key"
python scripts/embed_vault_documents.py
```

### Update Specific Folder

After major changes to one domain:

```bash
# Examples:
python scripts/embed_vault_documents.py --folder "40-Procedures"
python scripts/embed_vault_documents.py --folder "20-Domains"
python scripts/embed_vault_documents.py --folder "Claude Family"
```

### Force Re-Embed Everything

Ignores hash checking (useful after schema changes):

```bash
python scripts/embed_vault_documents.py --force
```

**Warning**: Re-embeds ALL files, costs ~$0.30

---

## Checking Embedding Status

### Quick Stats

```sql
SELECT
    COUNT(DISTINCT doc_path) as documents,
    COUNT(*) as total_chunks,
    pg_size_pretty(pg_total_relation_size('claude.vault_embeddings')) as table_size
FROM claude.vault_embeddings;
```

### Find Stale Embeddings

Documents where file modified after last embedding:

```sql
-- NOTE: Requires file_modified_at to be populated
-- (Run embedding script once to populate)

SELECT
    doc_path,
    doc_title,
    file_modified_at as embedded_version,
    'Check filesystem' as current_file_mtime
FROM claude.vault_embeddings
GROUP BY doc_path, doc_title, file_modified_at
ORDER BY file_modified_at DESC;
```

### Recently Updated

```sql
SELECT
    doc_path,
    COUNT(*) as chunks,
    MAX(updated_at) as last_embedded
FROM claude.vault_embeddings
GROUP BY doc_path
ORDER BY MAX(updated_at) DESC
LIMIT 10;
```

---

## Voyage AI Setup

### Get API Key

1. Visit: https://www.voyageai.com/
2. Sign up / Log in
3. Go to: https://dashboard.voyageai.com/
4. Copy API key

### Set Environment Variable

**Temporary (current session)**:
```bash
export VOYAGE_API_KEY="pa-your-key-here"
```

**Permanent (add to `.bashrc` or `.bash_profile`)**:
```bash
echo 'export VOYAGE_API_KEY="pa-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**Windows PowerShell**:
```powershell
$env:VOYAGE_API_KEY="pa-your-key-here"
```

---

## Searching the Vault (Current Approach)

> **Note**: The `vault-rag` MCP server was removed (2026-01). RAG is now fully automatic via the UserPromptSubmit hook. For manual searches, use project-tools MCP.

### Automatic (Default)

Every user prompt triggers `rag_query_hook.py` which queries:
1. **Knowledge table** (`claude.knowledge`) - 2 most relevant entries (similarity >= 0.45)
2. **Vault embeddings** (`claude.vault_embeddings`) - 3 most relevant docs (similarity >= 0.30)

Results are silently injected into context.

### Manual Search

Use the `project-tools` MCP:

```
recall_knowledge(query="How do I add an MCP server?")
```

### Embedding Stats

Check embedding coverage via SQL:

```sql
SELECT COUNT(*) as docs, COUNT(DISTINCT file_path) as files
FROM claude.vault_embeddings;
```

---

## Troubleshooting

### "No embeddings found"

**Cause**: Vault not embedded yet
**Fix**: Run `python scripts/embed_vault_documents.py`

### "VOYAGE_API_KEY not set"

**Cause**: Environment variable missing
**Fix**: `export VOYAGE_API_KEY="your-key"`

### "Payment method required" error

**Cause**: Voyage AI requires payment method for higher rate limits
**Fix**: Add payment method at https://dashboard.voyageai.com/billing

### Memory issues during embedding

**Cause**: Windows multiprocessing spawning too many processes
**Fix**: Process vault folder-by-folder:

```bash
python scripts/embed_vault_documents.py --folder "10-Projects"
python scripts/embed_vault_documents.py --folder "20-Domains"
python scripts/embed_vault_documents.py --folder "30-Patterns"
python scripts/embed_vault_documents.py --folder "40-Procedures"
```

### Hash mismatch after reorganizing

**Cause**: File moved but path changed
**Fix**: Use `--force` to re-embed:

```bash
python scripts/embed_vault_documents.py --force
```

---

## Cost & Performance

### Embedding Costs (Voyage AI)

- **Model**: voyage-3 (1024 dimensions)
- **Cost**: ~$0.10 per 1M tokens
- **Full vault**: ~88 files, ~150K tokens = **$0.30 total**
- **Incremental updates**: Only changed files (typically < $0.05)

### Performance

- **Full embed**: 5-10 minutes (88 files)
- **Incremental**: 1-2 minutes (5-10 changed files)
- **Query speed**: < 100ms for semantic search
- **Storage**: ~5MB for 768 chunks

---

## Related Documents

- [[Knowledge Capture SOP]] - Capturing knowledge into the vault
- [[Add MCP Server SOP]] - Setting up MCP servers
- [[Documentation Standards]] - Vault markdown formatting

---

**Version**: 1.0
**Last Updated**: 2025-12-30
**Owner**: Claude Family Infrastructure
