---
title: RAG Usage Guide - When Claude Should Use Semantic Search
tags: [claude-family, rag, mcp, semantic-search, best-practices, project-docs, session-preload, logging, knowledge-recall]
created: 2025-12-30
updated: 2026-01-18
---

# RAG Usage Guide - When Claude Should Use Semantic Search

## Purpose

Guide for Claude instances on when RAG (semantic search) is used for vault knowledge retrieval and **knowledge recall**.

**Key benefit**: 85% reduction in vault documentation tokens by loading only relevant docs on-demand.

**NEW (2026-01-18)**: Knowledge recall now works alongside vault RAG! Learned patterns, gotchas, and facts are automatically recalled on every prompt.

---

## Two Search Systems (Both Automatic)

The RAG hook now queries **TWO** systems on every user prompt:

| System | Table | What It Searches | Similarity Threshold |
|--------|-------|------------------|---------------------|
| **Knowledge Recall** | `claude.knowledge` | Learned patterns, gotchas, facts, preferences | 0.45 (higher = less noise) |
| **Vault RAG** | `claude.vault_embeddings` | Documentation from knowledge-vault/ | 0.30 (broader coverage) |

**Context injection order**:
1. Session context (if session keywords detected)
2. Knowledge recall (2 most relevant entries)
3. Vault RAG (3 most relevant docs)

**Why two systems?**
- **Knowledge**: High-signal learned information (patterns, gotchas) - replaces memory MCP
- **Vault**: Comprehensive documentation - SOPs, domain knowledge, procedures

---

## Knowledge System (NEW 2026-01-18)

### What Is Knowledge Recall?

Knowledge recall provides **memory-like functionality** using the `claude.knowledge` table with Voyage AI embeddings.

**Replaces**: The memory MCP (which was rarely used and had no database integration)

**Capabilities**:
- Semantic search over 290+ learned knowledge entries
- Auto-recall on every prompt via RAG hook
- Confidence tracking (increases on successful application)
- Typed relations between knowledge entries
- Project-specific and global knowledge

### Knowledge Types

| Type | Purpose | Example |
|------|---------|---------|
| pattern | Reusable code/design patterns | WinForms dark theme pattern |
| gotcha | Things that often go wrong | Designer file serialization rules |
| learned | Discovered during work | API rate limit workaround |
| preference | User/project preferences | Prefer composition over inheritance |
| fact | Factual information | PostgreSQL max connections = 100 |
| procedure | Step-by-step processes | How to add MCP server |

### MCP Tools (project-tools)

The `project-tools` MCP server provides knowledge operations:

| Tool | Purpose |
|------|---------|
| `store_knowledge` | Store new knowledge with auto-embedding |
| `recall_knowledge` | Semantic search (manual, more control than auto) |
| `link_knowledge` | Create typed relations (extends, contradicts, etc.) |
| `get_related_knowledge` | Traverse knowledge graph |
| `mark_knowledge_applied` | Track success/failure (adjusts confidence) |

**Example - Store knowledge**:
```python
store_knowledge(
    title="WinForms Designer can't parse lambdas",
    description="Never use lambda expressions in InitializeComponent...",
    knowledge_type="gotcha",
    knowledge_category="winforms",
    confidence_level=90
)
```

**Example - Recall knowledge**:
```python
recall_knowledge(
    query="WinForms designer problems",
    limit=3,
    min_similarity=0.5
)
```

### Knowledge Relations

The `claude.knowledge_relations` table enables typed relationships:

| Relation Type | Meaning |
|---------------|---------|
| extends | Builds upon another entry |
| contradicts | Conflicts with (newer may supersede) |
| supports | Provides evidence for |
| supersedes | Replaces older knowledge |
| depends_on | Requires another entry first |
| relates_to | General association |
| part_of | Component of larger concept |
| caused_by | Root cause relationship |

**Example**:
```python
link_knowledge(
    from_knowledge_id="uuid-of-dark-theme-v2",
    to_knowledge_id="uuid-of-dark-theme-v1",
    relation_type="supersedes",
    notes="V2 adds system theme detection"
)
```

### Embedding Knowledge

All 290 knowledge entries have embeddings (100% coverage).

**Update embeddings**:
```bash
# Embed knowledge entries (incremental)
python scripts/embed_knowledge.py

# Force re-embed all
python scripts/embed_knowledge.py --force
```

---

## How RAG Works (Three Modes)

### 1. **AUTOMATIC Mode** (Primary - UserPromptSubmit Hook) ✨

**Trigger**: Every user prompt (>=10 characters) automatically triggers RAG query

**What happens**:
1. Hook (`rag_query_hook.py`) runs silently on every user question
2. Generates Voyage AI embedding for your question
3. Searches vault embeddings with pgvector similarity
4. Returns top 3 docs with similarity >= 0.45
5. **Silently injects context** into Claude's view (no visible output!)

**User experience**: Completely transparent - you won't see any RAG activity, but Claude will have relevant vault docs in context automatically.

**Logs**:
- `~/.claude/hooks.log` (execution logs)
- `claude.rag_usage_log` table (query analytics)

**Threshold**: `min_similarity = 0.45` (lower = more results, higher = more precise)

### 2. **MANUAL Mode** (vault-rag MCP Tools)

Use manual MCP tools when you need:
- Deeper searches (top_k > 3)
- Lower similarity thresholds
- Full document retrieval
- Folder browsing
- Vault statistics

---

## When to Use Manual RAG (vault-rag MCP)

**Note**: Most common questions are now handled AUTOMATICALLY! Only use manual tools for specialized searches.

### ✅ Use Semantic Search For:

#### 1. **"How do I..." Questions**
User needs procedural knowledge from vault SOPs:

**Examples**:
- "How do I add an MCP server?"
- "How do I start a new project?"
- "How do I configure database-driven settings?"
- "How do I write a new skill?"

**Action**: Use `semantic_search` tool with the question as query

```python
# Example
semantic_search(query="How do I add an MCP server?", top_k=3)
# Returns: Chunks from "40-Procedures/Add MCP Server SOP.md"
```

#### 2. **Domain Knowledge Lookup**
User asks about technical patterns or domain-specific info:

**Examples**:
- "What are the WinForms dark theme patterns?"
- "How does the database architecture work?"
- "What are the Claude Code hooks?"
- "What's the MCP server registry?"

**Action**: Use `semantic_search` for discovery, then `get_document` for full content

```python
# Discovery
semantic_search(query="WinForms dark theme", top_k=3)
# Returns: 20-Domains/WinForms/winforms-dark-theme.md

# Full document
get_document("20-Domains/WinForms/winforms-dark-theme.md")
```

#### 3. **Searching for Patterns**
User needs reusable patterns or gotchas:

**Examples**:
- "Are there any Windows Bash gotchas?"
- "What patterns exist for auto-apply instructions?"
- "Any patterns for post-compaction hooks?"

**Action**: Search the `30-Patterns/` folder

```python
semantic_search(query="Windows Bash gotchas", top_k=5)
list_vault_documents(folder="30-Patterns")  # Browse available patterns
```

#### 4. **Finding Relevant SOPs**
You need a procedure but unsure which SOP covers it:

**Examples**:
- "Is there an SOP for knowledge capture?"
- "What's the session lifecycle procedure?"
- "How should I manage configurations?"

**Action**: Search procedures folder

```python
semantic_search(query="knowledge capture procedure", top_k=3)
list_vault_documents(folder="40-Procedures")  # List all SOPs
```

#### 5. **Architectural Understanding**
User asks about system design or infrastructure:

**Examples**:
- "How does the orchestrator MCP work?"
- "What's the purpose of the knowledge vault?"
- "How do Claude hooks enforce procedures?"

**Action**: Search Claude Family infrastructure docs

```python
semantic_search(query="orchestrator MCP architecture", top_k=5)
list_vault_documents(folder="Claude Family")
```

---

## When NOT to Use RAG

### ❌ Don't Use Semantic Search For:

#### 1. **Answer Already in Context**
If the information is already in the current conversation:

**Example**:
- User: "What did we just decide about the database schema?"
- ❌ Don't search vault
- ✅ Reference conversation history

#### 2. **Code in Current Project**
Questions about the active codebase:

**Example**:
- "Where is the error handling in the API?"
- ❌ Don't search vault
- ✅ Use `Grep` or `Read` tools on project files

#### 3. **Specific File Already Known**
You already know which project file to read:

**Example**:
- "What's in ARCHITECTURE.md?"
- ❌ Don't search vault
- ✅ Use `Read` tool directly: `Read("C:/Projects/claude-family/ARCHITECTURE.md")`

#### 4. **Real-time Code Analysis**
Debugging or analyzing code execution:

**Example**:
- "Why is this function failing?"
- ❌ Don't search vault
- ✅ Use debugging tools, LSP, or code inspection

#### 5. **Information Not in Vault**
Questions about external systems, current events, or non-vault topics:

**Example**:
- "What's the latest version of Node.js?"
- ❌ Don't search vault
- ✅ Use WebSearch or general knowledge

---

## RAG Tools Reference

### semantic_search

**Purpose**: Find relevant chunks by natural language query

**Parameters**:
- `query` (required): Natural language question/description
- `top_k` (optional): Max results (default 5)
- `min_similarity` (optional): Min score 0-1 (default 0.7)

**Returns**: Matching chunks with similarity scores

**Example**:
```python
semantic_search(
    query="How do I configure MCP servers?",
    top_k=5,
    min_similarity=0.6
)
```

**Use when**: You need to find relevant docs but don't know exact path

---

### get_document

**Purpose**: Retrieve full document by path

**Parameters**:
- `doc_path` (required): Path from semantic_search result

**Returns**: Complete document content (all chunks reassembled)

**Example**:
```python
# After semantic_search finds: "40-Procedures/Add MCP Server SOP.md"
get_document("40-Procedures/Add MCP Server SOP.md")
```

**Use when**: semantic_search identified the right doc, now you need full content

---

### list_vault_documents

**Purpose**: Browse available documents

**Parameters**:
- `folder` (optional): Filter by folder (e.g., "40-Procedures")

**Returns**: List of all documents with metadata

**Example**:
```python
list_vault_documents()  # All documents
list_vault_documents(folder="20-Domains")  # Domain knowledge only
```

**Use when**: User wants to know what documentation exists

---

### vault_stats

**Purpose**: Check embedding database status

**Parameters**: None

**Returns**: Document count, chunk count, table size, model info

**Example**:
```python
vault_stats()
# Returns: {total_documents: 88, total_chunks: 768, table_size: "11 MB", ...}
```

**Use when**: Debugging RAG system or checking if embeddings are current

---

## RAG Workflow Examples

### Example 1: User Asks How-To Question

**User**: "How do I add a new MCP server?"

**Claude's workflow**:
1. Recognize as "how-to" procedural question
2. Use semantic search:
   ```python
   result = semantic_search("How do I add a new MCP server?", top_k=3)
   ```
3. Check top result: `40-Procedures/Add MCP Server SOP.md` (similarity: 0.645)
4. Get full document:
   ```python
   doc = get_document("40-Procedures/Add MCP Server SOP.md")
   ```
5. Answer user's question using the SOP content
6. Provide file path reference for user: `knowledge-vault/40-Procedures/Add MCP Server SOP.md`

---

### Example 2: User Asks About Domain Knowledge

**User**: "What are the database schema conventions?"

**Claude's workflow**:
1. Recognize as domain knowledge question
2. Search for database-related docs:
   ```python
   result = semantic_search("database schema conventions", top_k=5)
   ```
3. Top results show:
   - `20-Domains/Database Architecture.md`
   - `40-Procedures/Documentation Standards.md`
4. Get the most relevant document:
   ```python
   doc = get_document("20-Domains/Database Architecture.md")
   ```
5. Answer using the domain knowledge
6. Optionally reference related docs found in search

---

### Example 3: User Wants to Browse

**User**: "What procedures are documented?"

**Claude's workflow**:
1. Recognize as browsing request (not search)
2. List procedures:
   ```python
   docs = list_vault_documents(folder="40-Procedures")
   ```
3. Present formatted list:
   ```
   Available SOPs (40-Procedures):
   - Add MCP Server SOP.md
   - Config Management SOP.md
   - Documentation Standards.md
   - Family Rules.md
   - Knowledge Capture SOP.md
   ...
   ```

---

### Example 4: Uncertain About Vault Content

**User**: "Is there documentation about session lifecycle?"

**Claude's workflow**:
1. Uncertain if doc exists → Use semantic search to check
2. Search:
   ```python
   result = semantic_search("session lifecycle", top_k=3)
   ```
3. Results show multiple matches:
   - `40-Procedures/Session Lifecycle - Overview.md`
   - `40-Procedures/Session Lifecycle - Session Start.md`
   - `40-Procedures/Session Lifecycle - Session End.md`
4. Confirm to user: "Yes, there are 3 session lifecycle docs..."
5. Ask if they want a specific one or overview

---

## Best Practices

### 1. **Search Before Assuming**
If unsure whether vault has relevant info, search rather than saying "I don't know"

**Bad**:
- User: "How do I write a skill?"
- Claude: "I don't have that information"

**Good**:
- User: "How do I write a skill?"
- Claude: *searches* → Finds skill documentation → Answers question

---

### 2. **Use Specific Queries**
More specific queries = better results

**Less effective**: `semantic_search("database")`
**More effective**: `semantic_search("database schema naming conventions")`

---

### 3. **Combine Tools**
Use semantic_search to discover, then get_document to retrieve full content

```python
# Discovery
matches = semantic_search("WinForms dark theme", top_k=3)

# Get top match full content
doc = get_document(matches["documents"][0]["doc_path"])
```

---

### 4. **Adjust Similarity Threshold**
If no results, try lowering `min_similarity`:

```python
# First try (strict)
result = semantic_search("topic", min_similarity=0.7)

# If no results, broaden search
if not result["found"]:
    result = semantic_search("topic", min_similarity=0.5)
```

---

### 5. **Reference Source Files**
Always tell user where you found the information:

**Example**:
```
According to the Add MCP Server SOP
(knowledge-vault/40-Procedures/Add MCP Server SOP.md):

1. Update claude.mcp_servers table...
2. Run generate_project_settings.py...
```

---

## Integration with Other Tools

### RAG + Grep
1. RAG finds which vault doc has the pattern
2. Grep finds code implementing the pattern in project

**Example**:
```python
# Find pattern in vault
pattern_doc = semantic_search("WinForms dark theme pattern")

# Read pattern
pattern = get_document("20-Domains/WinForms/winforms-dark-theme.md")

# Find code implementing this pattern
code = Grep(pattern="DarkTheme", glob="**/*.cs")
```

---

### RAG + Read
1. RAG identifies relevant vault doc
2. Read tool gets project-specific CLAUDE.md or config

**Example**:
```python
# General procedure from vault
sop = semantic_search("config management procedure")

# Project-specific config
project_config = Read("C:/Projects/claude-family/CLAUDE.md")
```

---

## Troubleshooting

### "No documents found"

**Cause**: Query too specific or embeddings not current

**Solution**:
1. Try broader query
2. Lower min_similarity
3. Check vault_stats() to verify embeddings exist
4. Re-run embedding pipeline if vault recently changed

---

### "Wrong results returned"

**Cause**: Query ambiguous or too broad

**Solution**:
1. Make query more specific
2. Add context to query (e.g., "How do I configure MCP servers in claude-family project?")
3. Increase top_k to see more results
4. Filter by folder if you know domain:
   ```python
   # Instead of semantic_search across all docs
   list_vault_documents(folder="40-Procedures")
   # Then search within that folder
   ```

---

### "RAG too slow"

**Cause**: Large result sets or network latency

**Solution**:
1. Reduce top_k (default 5 is usually enough)
2. Increase min_similarity to get fewer, better matches
3. Use list_vault_documents for browsing instead of search

---

## Performance & Cost

### Query Performance
- **Semantic search**: < 100ms (local PostgreSQL + pgvector)
- **Document retrieval**: < 50ms
- **Voyage AI embedding**: ~500ms (only when searching, cached locally)

### Token Savings
- **Without RAG**: ~50K tokens (entire vault loaded into context)
- **With RAG**: ~5-10K tokens (only relevant docs)
- **Savings**: **85% reduction** in vault-related tokens

### Cost
- **Embedding updates**: ~$0.30 for full vault (one-time)
- **Incremental updates**: < $0.05 (only changed files)
- **Query cost**: $0 (uses stored embeddings)

---

## New Features (2025-12-30)

### Project Document Support

The vault-rag system now indexes project documents (CLAUDE.md, ARCHITECTURE.md, PROBLEM_STATEMENT.md) alongside vault knowledge.

**Document Sources**:
- `vault`: Knowledge vault documents (knowledge-vault/)
- `project`: Project-specific documentation
- `global`: Cross-project documentation

**Filtering by Source**:
```python
# Search only vault knowledge
semantic_search("database patterns", source="vault")

# Search only project docs
semantic_search("project architecture", source="project", project="claude-family")

# Search both (default)
semantic_search("configuration", source="all")
```

**Why This Matters**:
- Project docs now searchable alongside vault
- Can find project-specific info (CLAUDE.md) and general knowledge (SOPs) in one search
- Reduces need to manually read CLAUDE.md repeatedly

**Examples**:
```python
# Find project-specific conventions
semantic_search("claude-family coding standards", source="project", project="claude-family")

# Compare vault SOP vs project implementation
vault_sop = semantic_search("config management", source="vault")
project_doc = semantic_search("config", source="project", project="claude-family")
```

---

### SessionStart Automatic Pre-loading

**Feature**: Relevant vault docs are automatically injected at session start.

**How It Works**:
1. Session starts → system queries project type and phase
2. Generates semantic search: "{project_type} {phase} procedures and standards"
3. Pre-loads top 3 most relevant docs (min similarity 0.6)
4. Injects into initial context automatically

**Benefits**:
- No manual search needed for common project info
- Fresh, relevant knowledge every session
- Adapts to project type and phase

**What Gets Pre-loaded**:
- For `infrastructure` projects: Infrastructure patterns, governance, procedures
- For `web-app` projects: Frontend patterns, API design, testing guides
- For `desktop-app` projects: WinForms patterns, accessibility, packaging

**Configuration**:
Pre-loading happens automatically if:
- ✅ VOYAGE_API_KEY is set
- ✅ Database connection available
- ✅ Vault embeddings exist
- ✅ Session (not resume) start

**Logging**:
All pre-loads logged to `claude.rag_usage_log`:
```sql
SELECT * FROM claude.rag_usage_log
WHERE query_type = 'session_preload'
ORDER BY created_at DESC
LIMIT 5;
```

**Example Pre-loaded Context**:
```
============================================================
PRE-LOADED KNOWLEDGE (3 docs, 245ms)
============================================================

📄 Config Management SOP (0.712 similarity)
   Path: 40-Procedures/Config Management SOP.md

Database-driven configuration system...
[Content preview]

------------------------------------------------------------

📄 Session Lifecycle - Overview (0.685 similarity)
   Path: 40-Procedures/Session Lifecycle - Overview.md

Session management procedures...
[Content preview]

------------------------------------------------------------
```

---

### RAG Usage Logging

**Feature**: All RAG operations are logged to `claude.rag_usage_log` for tracking and optimization.

**Logged Data**:
- Query text and type (manual_search | session_preload)
- Results count and top similarity score
- Document paths returned
- Latency in milliseconds
- Session ID and project name

**Query Types**:
- `manual_search`: Explicit semantic_search tool calls
- `session_preload`: Automatic SessionStart pre-loading

**Schema**:
```sql
CREATE TABLE claude.rag_usage_log (
    log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid REFERENCES claude.sessions,
    project_name text,
    query_type text NOT NULL,  -- 'session_preload', 'manual_search'
    query_text text,
    results_count integer,
    top_similarity float,
    docs_returned text[],
    latency_ms integer,
    created_at timestamp DEFAULT NOW()
);
```

**Analyzing Usage**:
```sql
-- Most common queries
SELECT query_text, COUNT(*) as times_searched
FROM claude.rag_usage_log
WHERE query_type = 'manual_search'
GROUP BY query_text
ORDER BY times_searched DESC
LIMIT 10;

-- Average latency by query type
SELECT query_type, AVG(latency_ms) as avg_latency_ms
FROM claude.rag_usage_log
GROUP BY query_type;

-- Documents most frequently returned
SELECT UNNEST(docs_returned) as doc_path, COUNT(*) as times_returned
FROM claude.rag_usage_log
WHERE docs_returned IS NOT NULL
GROUP BY doc_path
ORDER BY times_returned DESC
LIMIT 10;

-- Sessions with low similarity (may need better embeddings)
SELECT session_id, query_text, top_similarity
FROM claude.rag_usage_log
WHERE top_similarity < 0.5
ORDER BY created_at DESC;
```

**Why This Matters**:
- Identify which docs are most useful
- Track RAG performance over time
- Find queries with poor results (optimize embeddings)
- Measure pre-loading effectiveness

---

## Embedding Project Documents

**New**: The embedding script now supports project documentation.

**Commands**:
```bash
# Embed a single project
python scripts/embed_vault_documents.py --project claude-family

# Embed all active projects
python scripts/embed_vault_documents.py --all-projects

# Embed vault only (original behavior)
python scripts/embed_vault_documents.py --folder 40-Procedures
```

**What Gets Embedded**:
For each project, these standard files:
- CLAUDE.md
- ARCHITECTURE.md
- PROBLEM_STATEMENT.md
- README.md (if exists)

**Database Storage**:
```sql
-- Project docs have doc_source='project' and project_name set
SELECT doc_path, doc_source, project_name
FROM claude.vault_embeddings
WHERE doc_source = 'project'
LIMIT 5;
```

**Workflow**:
1. Script queries `claude.workspaces` for active projects
2. For each project, finds standard documentation files
3. Generates embeddings (Voyage AI voyage-3)
4. Stores with `doc_source='project'` and `project_name` set
5. Logging and file hash tracking (incremental updates only)

**Example**:
```bash
# First time: Embed all project docs
python scripts/embed_vault_documents.py --all-projects

# Later: Update only changed files
python scripts/embed_vault_documents.py --all-projects
# Skips unchanged files automatically (hash tracking)
```

---

## Related Documents

- [[Vault Embeddings Management SOP]] - Maintaining embeddings
- [[Claude Tools Reference]] - All available MCP tools
- [[Knowledge Capture SOP]] - Adding content to vault

---

**Version**: 2.0
**Last Updated**: 2026-01-18
**Owner**: Claude Family Infrastructure
**Changes**: Added knowledge recall system (replaces memory MCP), project-tools MCP integration
