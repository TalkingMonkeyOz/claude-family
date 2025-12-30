# Vault RAG MCP Server

Semantic search over the knowledge-vault using pgvector embeddings and Ollama.

## Purpose

Provides on-demand retrieval of relevant documentation instead of loading everything into context. Expected token reduction: 85% (same as tool-search MCP).

## Architecture

```
Query → Ollama Embedding → Vector Similarity Search → PostgreSQL/pgvector → Ranked Results
```

- **Embedding Model**: nomic-embed-text (768 dimensions, 274 MB)
- **Vector DB**: PostgreSQL with pgvector v0.8.1
- **Index**: HNSW for fast cosine similarity search
- **Storage**: claude.vault_embeddings table

## Tools

### semantic_search(query, top_k=5, min_similarity=0.7)

Search the knowledge vault using semantic similarity.

**Examples**:
```python
# Find relevant SOPs
semantic_search("How do I add an MCP server?", top_k=3)

# Find WinForms patterns
semantic_search("WinForms dark theme implementation", min_similarity=0.6)

# Find database conventions
semantic_search("Database schema naming conventions")
```

**Returns**:
```json
{
  "found": true,
  "count": 3,
  "query": "How do I add an MCP server?",
  "documents": [
    {
      "doc_path": "40-Procedures/Add MCP Server SOP.md",
      "doc_title": "Add MCP Server SOP",
      "chunk_index": 0,
      "content": "# Add MCP Server SOP...",
      "similarity": 0.912,
      "metadata": {"title": "Add MCP Server SOP", ...}
    }
  ]
}
```

### get_document(doc_path)

Retrieve a complete document by path.

**Example**:
```python
get_document("40-Procedures/Add MCP Server SOP.md")
```

**Returns**: Full document reassembled from chunks

### list_vault_documents(folder=None)

List all documents in the vault embeddings.

**Examples**:
```python
list_vault_documents()  # All documents
list_vault_documents("40-Procedures")  # Only SOPs
list_vault_documents("20-Domains")  # Only domain knowledge
```

### vault_stats()

Get embedding database statistics.

**Returns**:
```json
{
  "total_documents": 6,
  "total_chunks": 53,
  "table_size": "792 kB",
  "embedding_model": "nomic-embed-text",
  "vector_dimensions": 768
}
```

## Installation

### 1. Prerequisites

```bash
# Ollama with nomic-embed-text model
ollama pull nomic-embed-text

# PostgreSQL with pgvector
psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Python dependencies
pip install mcp psycopg ollama
```

### 2. Add to Global MCP Config

Already configured in `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "vault-rag": {
      "type": "stdio",
      "command": "C:/venvs/mcp/Scripts/python.exe",
      "args": ["C:/Projects/claude-family/mcp-servers/vault-rag/server.py"],
      "env": {
        "DATABASE_URL": "postgresql://..."
      }
    }
  }
}
```

### 3. Restart Claude Code

Global MCPs load at startup (not during SessionStart).

## Embedding Pipeline

### Initial Embedding

```bash
# Embed specific folder (testing)
python scripts/embed_vault_documents.py --folder 40-Procedures

# Embed entire vault (production)
python scripts/embed_vault_documents.py
```

### Re-embedding

```bash
# Force re-embed (if documents changed)
python scripts/embed_vault_documents.py --force

# Embed in batches
python scripts/embed_vault_documents.py --batch-size 20
```

### Pipeline Details

- **Chunking**: 1000 characters per chunk, 200 character overlap
- **Frontmatter**: YAML metadata extracted and stored in JSONB
- **Deduplication**: Uses UNIQUE(doc_path, chunk_index)
- **Embedding**: 768-dimension vectors via Ollama

## Database Schema

```sql
CREATE TABLE claude.vault_embeddings (
    embedding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_path text NOT NULL,
    doc_title text,
    chunk_index integer NOT NULL DEFAULT 0,
    chunk_text text NOT NULL,
    embedding vector(768) NOT NULL,
    metadata jsonb,
    created_at timestamp NOT NULL DEFAULT NOW(),
    updated_at timestamp NOT NULL DEFAULT NOW(),
    UNIQUE(doc_path, chunk_index)
);

-- HNSW index for fast similarity search
CREATE INDEX vault_embeddings_vector_idx
ON claude.vault_embeddings
USING hnsw (embedding vector_cosine_ops);
```

## Usage Patterns

### SessionStart Hook Integration

```python
# Auto-load relevant context based on project
with mcp.use_tool("vault-rag", "semantic_search") as search:
    result = search(f"Project setup for {project_name}", top_k=3)
    if result["found"]:
        # Inject relevant docs into session context
        pass
```

### Ad-hoc Knowledge Retrieval

Instead of reading every SOP manually:

```python
# Before (inefficient)
Read("40-Procedures/Add MCP Server SOP.md")
Read("40-Procedures/Config Management SOP.md")
Read("40-Procedures/Session Lifecycle - Overview.md")

# After (efficient)
semantic_search("How do I configure MCPs?", top_k=2)
# Returns only the 2 most relevant documents
```

### Cross-Document Discovery

```python
# Find all documentation about a topic across folders
semantic_search("dark theme implementation")
# Might return:
# - 30-Patterns/winforms-dark-theme-pattern.md
# - 20-Domains/WinForms/winforms-layout-patterns.md
# - instructions/winforms-dark-theme.instructions.md
```

## Performance

| Metric | Value |
|--------|-------|
| Current embeddings | 53 chunks (6 docs) |
| Table size | 792 kB |
| Search latency | <100ms (HNSW index) |
| Expected full vault | ~5000 chunks (1000+ docs) |
| Expected size | ~80 MB |
| Token reduction | 85% (vs loading all docs) |

## Troubleshooting

### Ollama not accessible

```bash
# Check Ollama is running
ollama list

# Verify model
ollama pull nomic-embed-text
```

### Database connection failed

```bash
# Test connection
psql postgresql://postgres:...@localhost/ai_company_foundation

# Verify pgvector
psql -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

### No embeddings found

```bash
# Check table
psql -c "SELECT COUNT(*) FROM claude.vault_embeddings;"

# Run embedding pipeline
python scripts/embed_vault_documents.py --folder 40-Procedures
```

### Similarity scores too low

Adjust `min_similarity` parameter (default 0.7):

```python
semantic_search("query", min_similarity=0.5)  # More permissive
```

## Comparison to tool-search

| Feature | tool-search | vault-rag |
|---------|-------------|-----------|
| Purpose | Tool discovery | Knowledge retrieval |
| Search method | Keyword matching | Semantic similarity |
| Backend | JSON file | PostgreSQL/pgvector |
| Update method | Manual JSON edit | Embedding pipeline |
| Query type | "database query" | "How do I query the database?" |
| Result type | Tool schemas | Document content |

## Future Enhancements

1. **Auto-refresh**: Detect vault changes and re-embed automatically
2. **Similarity tuning**: Track retrieval quality and tune thresholds
3. **Session embeddings**: Embed session summaries for cross-session learning
4. **Code pattern search**: Embed code examples for pattern discovery
5. **Hybrid search**: Combine semantic + keyword search
6. **Re-ranking**: Use LLM to re-rank results by relevance

## Related

- `scripts/embed_vault_documents.py` - Embedding pipeline
- `40-Procedures/Add MCP Server SOP.md` - MCP installation procedure
- `docs/SESSION_SUMMARY_2025-12-30.md` - Implementation session notes
- `knowledge-vault/` - Source of embedded documents

---

**Version**: 1.0
**Created**: 2025-12-30
**Status**: Active (6 documents embedded, testing phase)
**Location**: mcp-servers/vault-rag/
