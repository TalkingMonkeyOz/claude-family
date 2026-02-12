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

## Session Facts (Your Notepad)

**NEW (2026-01-26)**: Session facts are your **working memory** for long conversations.

### Why Use Session Facts?

Long conversations get compressed. Earlier context gets lost. Use session facts as a **notepad** to:
- Store things the user tells you (credentials, endpoints, preferences)
- Track progress on multi-step tasks
- Record decisions made during the session
- Preserve discoveries/findings for later reference

### When to Store Facts

| Situation | Fact Type | Example |
|-----------|-----------|---------|
| User gives API key/credential | `credential` | `store_session_fact("api_key", "sk-...", "credential", is_sensitive=True)` |
| User tells you a URL/endpoint | `endpoint` | `store_session_fact("api_url", "https://...", "endpoint")` |
| User specifies config value | `config` | `store_session_fact("db_name", "production", "config")` |
| A decision is made | `decision` | `store_session_fact("auth_method", "JWT with refresh", "decision")` |
| You discover something | `note` | `store_session_fact("finding_rate_limit", "API limited to 60/min", "note")` |
| Multi-step task progress | `note` | `store_session_fact("task_progress", "Done: A,B. Next: C", "note")` |

**Valid fact_types**: `credential`, `config`, `endpoint`, `decision`, `note`, `data`, `reference`

### Session Facts Tools (project-tools MCP)

| Tool | Purpose |
|------|---------|
| `store_session_fact` | Store a fact (key, value, type) |
| `list_session_facts` | See all facts in current session (your notepad) |
| `recall_session_fact` | Get a specific fact by key |
| `recall_previous_session_facts` | Crash recovery - get facts from N previous sessions |

### Best Practice

**At any point**: Run `list_session_facts()` to see your notepad.

**Session feels long?** Check your notepad for context you stored earlier.

**After crash/restart**: Use `recall_previous_session_facts(n_sessions=3)` to recover.

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

### 2. **MANUAL Mode** (project-tools MCP)

The `vault-rag` MCP was removed (2026-01). For manual knowledge searches, use:

| Tool | Purpose |
|------|---------|
| `recall_knowledge` | Semantic search over `claude.knowledge` (290+ entries) |
| `store_knowledge` | Store new knowledge with auto-embedding |
| Read tool | Read vault documents directly by path |

**When to use manual mode**:
- Need more control over similarity thresholds
- Searching for specific knowledge types (gotcha, pattern, etc.)
- Storing new knowledge for future sessions

```python
# Manual knowledge search
recall_knowledge(query="WinForms dark theme patterns", limit=5, min_similarity=0.4)

# Read a vault doc directly
Read("C:/Projects/claude-family/knowledge-vault/40-Procedures/Add MCP Server SOP.md")
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

## Available RAG Tools

### Automatic (RAG Hook - every prompt)

The `rag_query_hook.py` handles all RAG automatically:
- Queries `claude.knowledge` (2 results, similarity >= 0.45)
- Queries `claude.vault_embeddings` (3 results, similarity >= 0.30)
- Injects context silently via `additionalContext`

### Manual (project-tools MCP)

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `recall_knowledge` | Semantic search over knowledge | Need more results or different threshold |
| `store_knowledge` | Store new knowledge | Learned something worth preserving |
| `link_knowledge` | Create relations | Connect related knowledge entries |
| `mark_knowledge_applied` | Track usage | After successfully using knowledge |

### Direct File Access (Read tool)

For vault documents, use the Read tool directly:
```python
Read("C:/Projects/claude-family/knowledge-vault/40-Procedures/Add MCP Server SOP.md")
```

---

## RAG Workflow Examples

### Example 1: User Asks How-To Question

**User**: "How do I add a new MCP server?"

**Claude's workflow**:
1. RAG hook **automatically** finds `Add MCP Server SOP.md` (injected into context)
2. Claude answers using the auto-injected SOP content
3. If more detail needed, Read the full doc directly:
   ```python
   Read("C:/Projects/claude-family/knowledge-vault/40-Procedures/Add MCP Server SOP.md")
   ```

### Example 2: User Asks About Domain Knowledge

**User**: "What are the database schema conventions?"

**Claude's workflow**:
1. RAG hook auto-injects relevant vault docs + knowledge entries
2. Claude answers from auto-injected context
3. If insufficient, use manual knowledge search:
   ```python
   recall_knowledge(query="database schema conventions", limit=5)
   ```

### Example 3: User Wants to Browse

**User**: "What procedures are documented?"

**Claude's workflow**:
1. Use Glob to list vault documents:
   ```python
   Glob("knowledge-vault/40-Procedures/*.md")
   ```
2. Present formatted list of available SOPs

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

### 3. **Combine Auto + Manual**
Auto RAG handles most cases. Use manual `recall_knowledge` for deeper searches:

```python
# Auto RAG didn't surface what you need? Search manually:
recall_knowledge(query="WinForms dark theme pattern", limit=5, min_similarity=0.3)
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
1. Auto RAG injects relevant vault knowledge
2. Grep finds code implementing the pattern in project

**Example**:
```python
# RAG auto-injected WinForms dark theme pattern
# Now find code implementing this pattern
Grep(pattern="DarkTheme", glob="**/*.cs")
```

### RAG + Read
1. Auto RAG surfaces relevant docs
2. Read tool gets full content when needed

**Example**:
```python
# RAG auto-injected Config Management SOP summary
# Read full SOP for detailed steps
Read("C:/Projects/claude-family/knowledge-vault/40-Procedures/Config Management SOP.md")
```

---

## Troubleshooting

### "No knowledge recalled"

**Cause**: Query too specific, embeddings outdated, or low similarity

**Solution**:
1. Use manual `recall_knowledge` with lower `min_similarity` (e.g., 0.3)
2. Re-run embedding pipeline: `python scripts/embed_vault_documents.py`
3. Check embeddings exist: query `claude.vault_embeddings` table

### "Wrong results returned"

**Cause**: Query ambiguous or too broad

**Solution**:
1. Make query more specific
2. Use `recall_knowledge` with `knowledge_type` filter
3. Browse vault directly with Glob tool

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

## Architecture Details

### Embedding Storage

Two embedding tables power the RAG system:

| Table | Content | Embedding Model |
|-------|---------|-----------------|
| `claude.vault_embeddings` | Vault documents (118+ files) | Voyage AI voyage-3 (1024 dim) |
| `claude.knowledge` (embedding column) | Learned knowledge (290+ entries) | Voyage AI voyage-3 (1024 dim) |

### Document Sources

The vault embeddings table supports multiple document sources:
- `vault`: Knowledge vault documents (knowledge-vault/)
- `project`: Project-specific documentation (CLAUDE.md, ARCHITECTURE.md)

### How Auto RAG Works

1. User sends prompt (>=10 chars)
2. `rag_query_hook.py` runs via UserPromptSubmit hook
3. Generates Voyage AI embedding for the prompt
4. Queries both tables via pgvector cosine similarity
5. Returns results via `additionalContext` (injected silently)

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

## Nimbus Project Context (NEW 2026-01-26)

**Feature**: For Nimbus projects, the RAG hook also queries `nimbus_context` schema for project-specific knowledge.

**Supported Projects**:
- monash-nimbus-reports
- nimbus-user-loader
- nimbus-customer-app
- ATO-Tax-Agent

**What Gets Queried** (keyword search, not semantic):

| Table | Content |
|-------|---------|
| `code_patterns` | Reusable code patterns for Nimbus API |
| `project_learnings` | Lessons learned from past work |
| `project_facts` | Known facts (e.g., API endpoints, limits) |
| `api_field_mappings` | OData↔REST field name mappings |

**Context Output Example**:
```
======================================================================
NIMBUS PROJECT CONTEXT (5 entries, 12ms)
======================================================================

🔧 PATTERN [api-pagination]
   Context: OData queries with large result sets
   Solution: Use $top and $skip parameters...

💡 LEARNING [rate-limits]
   Context: Heavy API usage
   API has 60 req/min limit per user...

📋 FACT [odata-endpoint]
   ODataBaseUrl: https://monash.nimbus.cloud/odata/v4/
```

**How It Works**:
1. Hook detects project is a Nimbus project (from cwd)
2. Extracts keywords from user prompt
3. Queries nimbus_context tables via ILIKE pattern matching
4. Returns matching patterns, learnings, facts
5. Injected after vault RAG but before skill suggestions

---

## Related Documents

- [[Vault Embeddings Management SOP]] - Maintaining embeddings
- [[Claude Tools Reference]] - All available MCP tools
- [[Knowledge Capture SOP]] - Adding content to vault
- [[Database Integration Guide]] - nimbus_context schema details

---

**Version**: 3.1
**Created**: 2025-12-30
**Updated**: 2026-02-10
**Location**: Claude Family/RAG Usage Guide.md
**Changes**: Verified vault-rag MCP removal (2026-01). RAG automatic via hook. Manual search via project-tools recall_knowledge.
