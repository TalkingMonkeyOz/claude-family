-- F98: Create Knowledge Routing and Book Reference Schema
-- Date: 2026-02-11
-- Purpose: Support book-based knowledge routing and semantic search (BT324 + BT326)
-- Migration tasks: BT324 (book reference system), BT326 (knowledge routing)

-- ============================================================================
-- PREREQUISITE CHECK: Verify pgvector extension exists
-- ============================================================================

-- Note: If pgvector is not available, run:
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- TABLE 1: claude.books (BT324)
-- ============================================================================

CREATE TABLE IF NOT EXISTS claude.books (
    book_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    author VARCHAR(300),
    isbn VARCHAR(20),
    year INTEGER,
    topics TEXT[] DEFAULT '{}',
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_books_topics ON claude.books USING GIN (topics);
CREATE INDEX IF NOT EXISTS idx_books_title ON claude.books (title);

-- ============================================================================
-- TABLE 2: claude.book_references (BT324)
-- ============================================================================

CREATE TABLE IF NOT EXISTS claude.book_references (
    ref_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES claude.books(book_id) ON DELETE CASCADE,
    chapter VARCHAR(200),
    page_range VARCHAR(50),
    concept VARCHAR(500) NOT NULL,
    description TEXT,
    quote TEXT,
    tags TEXT[] DEFAULT '{}',
    embedding VECTOR(1024),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_book_refs_book ON claude.book_references (book_id);
CREATE INDEX IF NOT EXISTS idx_book_refs_tags ON claude.book_references USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_book_refs_concept ON claude.book_references (concept);
-- Vector index for semantic search (requires pgvector extension)
CREATE INDEX IF NOT EXISTS idx_book_refs_embedding ON claude.book_references USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- ============================================================================
-- TABLE 3: claude.knowledge_routes (BT326)
-- ============================================================================

CREATE TABLE IF NOT EXISTS claude.knowledge_routes (
    route_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_pattern VARCHAR(500) NOT NULL,
    knowledge_source VARCHAR(500) NOT NULL,
    knowledge_type VARCHAR(50) NOT NULL CHECK (knowledge_type IN ('sop', 'pattern', 'book', 'domain', 'tool')),
    description TEXT,
    priority INTEGER DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_routes_active ON claude.knowledge_routes (active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_knowledge_routes_type ON claude.knowledge_routes (knowledge_type);

-- ============================================================================
-- COLUMN REGISTRY ENTRIES (Data Gateway)
-- ============================================================================

-- Books table topics
INSERT INTO claude.column_registry (id, table_name, column_name, data_type, description, valid_values, created_at, updated_at)
VALUES (gen_random_uuid(), 'books', 'topics', 'text[]', 'Array of topic tags for the book', NULL, NOW(), NOW())
ON CONFLICT (table_name, column_name) DO UPDATE
SET updated_at = NOW();

-- Book references tags
INSERT INTO claude.column_registry (id, table_name, column_name, data_type, description, valid_values, created_at, updated_at)
VALUES (gen_random_uuid(), 'book_references', 'tags', 'text[]', 'Array of concept tags for the reference', NULL, NOW(), NOW())
ON CONFLICT (table_name, column_name) DO UPDATE
SET updated_at = NOW();

-- Knowledge routes type constraint
INSERT INTO claude.column_registry (id, table_name, column_name, data_type, description, valid_values, created_at, updated_at)
VALUES (gen_random_uuid(), 'knowledge_routes', 'knowledge_type', 'varchar', 'Type of knowledge source', '["sop", "pattern", "book", "domain", "tool"]', NOW(), NOW())
ON CONFLICT (table_name, column_name) DO UPDATE
SET updated_at = NOW();

-- Knowledge routes priority constraint
INSERT INTO claude.column_registry (id, table_name, column_name, data_type, description, valid_values, created_at, updated_at)
VALUES (gen_random_uuid(), 'knowledge_routes', 'priority', 'integer', 'Route priority 1-5 (1=highest)', '[1, 2, 3, 4, 5]', NOW(), NOW())
ON CONFLICT (table_name, column_name) DO UPDATE
SET updated_at = NOW();

-- ============================================================================
-- SEED INITIAL KNOWLEDGE ROUTES (BT326)
-- ============================================================================

INSERT INTO claude.knowledge_routes (route_id, task_pattern, knowledge_source, knowledge_type, description, priority)
VALUES
(gen_random_uuid(), 'update CLAUDE.md', 'vault:40-Procedures/Config Management SOP.md', 'sop', 'Config changes go through DB-driven process', 1),
(gen_random_uuid(), 'update CLAUDE.md', 'tool:update_claude_md', 'tool', 'MCP tool for atomic CLAUDE.md updates', 1),
(gen_random_uuid(), 'create new project', 'vault:40-Procedures/New Project SOP.md', 'sop', 'Full project initialization procedure', 1),
(gen_random_uuid(), 'add MCP server', 'vault:40-Procedures/Add MCP Server SOP.md', 'sop', 'MCP server installation and config', 1),
(gen_random_uuid(), 'database schema', 'vault:20-Domains/Database Integration Guide.md', 'domain', 'Database architecture and conventions', 2),
(gen_random_uuid(), 'winforms', 'vault:20-Domains/WinForms Best Practices.md', 'domain', 'WinForms dark theme and patterns', 2),
(gen_random_uuid(), 'hook', 'vault:Claude Family/Claude Hooks.md', 'domain', 'Hook architecture and debugging', 2),
(gen_random_uuid(), 'agent delegation', 'vault:30-Patterns/Agent Selection Decision Tree.md', 'pattern', 'When and how to delegate to agents', 2),
(gen_random_uuid(), 'session workflow', 'vault:40-Procedures/Session Lifecycle - Overview.md', 'sop', 'Session start/end procedures', 2),
(gen_random_uuid(), 'RAG knowledge retrieval', 'vault:Claude Family/RAG Usage Guide.md', 'domain', 'How RAG and knowledge system works', 2)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables created
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'claude' AND table_name IN ('books', 'book_references', 'knowledge_routes')
ORDER BY table_name;

-- Verify indexes created
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'claude' AND indexname LIKE 'idx_%routes%' OR indexname LIKE 'idx_books%' OR indexname LIKE 'idx_book_refs%'
ORDER BY indexname;

-- Verify column registry entries
SELECT table_name, column_name, data_type
FROM claude.column_registry
WHERE table_name IN ('books', 'book_references', 'knowledge_routes')
ORDER BY table_name, column_name;

-- Verify knowledge routes seeded
SELECT COUNT(*) as route_count FROM claude.knowledge_routes;

-- ============================================================================
-- NOTES
-- ============================================================================

-- BT324 (Books System):
--   - claude.books: Store book metadata (title, author, ISBN, topics, summary)
--   - claude.book_references: Store references to specific concepts with embeddings for semantic search
--   - Supports GIN indexes on topics and tags arrays for efficient filtering
--   - Vector embedding support for semantic search across book references

-- BT326 (Knowledge Routing):
--   - claude.knowledge_routes: Route tasks/patterns to appropriate knowledge sources
--   - Supports 5 knowledge types: sop, pattern, book, domain, tool
--   - Priority system (1-5) to rank which knowledge source to use first
--   - Active flag to enable/disable routes without deletion
--   - 10 seed routes covering core infrastructure knowledge

-- pgvector requirement:
--   - VECTOR(1024) type used for embeddings (same as vault_embeddings table)
--   - ivfflat index for efficient semantic similarity search
--   - If pgvector not available, the VECTOR column will fail; ensure extension is created first
