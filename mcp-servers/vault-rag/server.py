#!/usr/bin/env python3
"""
Vault RAG MCP Server

Provides semantic search over the knowledge-vault using pgvector embeddings.
Reduces context token usage by retrieving only relevant documents on-demand.

Expected impact: 85% reduction in vault documentation tokens (same as tool-search)

Usage:
    python server.py
"""

import os
import json
import time
from datetime import datetime
from typing import Any, Optional, List, Dict

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: mcp package not installed. Run: pip install mcp")
    raise

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg")
    raise

try:
    import voyageai
except ImportError:
    print("ERROR: voyageai not installed. Run: pip install voyageai")
    raise

# Initialize MCP server
mcp = FastMCP("vault-rag")

# Configuration
DB_CONNECTION = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation"
)
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
EMBEDDING_MODEL = "voyage-3"  # voyage-3 or voyage-3-lite
_client = None  # Lazy load client


def get_db_connection():
    """Get database connection with dict_row factory."""
    return psycopg.connect(DB_CONNECTION, row_factory=dict_row)


def generate_embedding(text: str) -> List[float]:
    """Generate embedding using Voyage AI."""
    global _client
    try:
        if _client is None:
            if not VOYAGE_API_KEY:
                raise RuntimeError("VOYAGE_API_KEY environment variable not set")
            _client = voyageai.Client(api_key=VOYAGE_API_KEY)

        result = _client.embed([text], model=EMBEDDING_MODEL, input_type="document")
        return result.embeddings[0]
    except Exception as e:
        raise RuntimeError(f"Failed to generate embedding: {e}")


def log_rag_usage(
    conn,
    session_id: Optional[str],
    project_name: Optional[str],
    query_type: str,
    query_text: str,
    results_count: int,
    top_similarity: Optional[float],
    docs_returned: List[str],
    latency_ms: int
):
    """Log RAG usage to tracking table."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO claude.rag_usage_log
                (session_id, project_name, query_type, query_text, results_count,
                 top_similarity, docs_returned, latency_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session_id,
                project_name,
                query_type,
                query_text,
                results_count,
                top_similarity,
                docs_returned,
                latency_ms
            ))
        conn.commit()
    except Exception as e:
        # Don't fail the main operation if logging fails
        print(f"[WARN] Failed to log RAG usage: {e}")


@mcp.tool()
def semantic_search(
    query: str,
    top_k: int = 5,
    min_similarity: float = 0.7,
    source: str = "all",
    project: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict:
    """
    Search the knowledge vault using semantic similarity.

    Use this to find relevant documentation, SOPs, and knowledge on-demand
    instead of loading everything into context.

    Args:
        query: Natural language query describing what you're looking for
               Examples: "How do I add an MCP server?", "Session lifecycle procedures",
                        "Database schema conventions", "WinForms dark theme"
        top_k: Maximum number of results to return (default 5)
        min_similarity: Minimum similarity score 0-1 (default 0.7)
        source: Filter by document source: "all", "vault", "project", or "global" (default "all")
        project: Filter by project name (only applicable for source="project")
        session_id: Session ID for logging (optional)

    Returns:
        Dict with matching documents and their content
    """
    start_time = time.time()

    try:
        # Generate query embedding
        query_embedding = generate_embedding(query)

        # Build WHERE clause with source filter
        where_clauses = ["1 - (embedding <=> %s::vector) >= %s"]
        params = [query_embedding, query_embedding, min_similarity]

        if source != "all":
            where_clauses.append("doc_source = %s")
            params.append(source)

        if project:
            where_clauses.append("project_name = %s")
            params.append(project)

        where_clause = " AND ".join(where_clauses)

        # Search for similar documents
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT
                        doc_path,
                        doc_title,
                        chunk_index,
                        chunk_text,
                        doc_source,
                        project_name,
                        1 - (embedding <=> %s::vector) as similarity_score,
                        metadata
                    FROM claude.vault_embeddings
                    WHERE {where_clause}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, params + [query_embedding, top_k])

                results = cur.fetchall()

            # Log usage
            latency_ms = int((time.time() - start_time) * 1000)
            docs_returned = [r['doc_path'] for r in results]
            top_similarity = results[0]['similarity_score'] if results else None

            log_rag_usage(
                conn,
                session_id,
                project,
                "manual_search",
                query,
                len(results),
                top_similarity,
                docs_returned,
                latency_ms
            )

        if not results:
            return {
                "found": False,
                "message": f"No documents found matching '{query}' with similarity >= {min_similarity}",
                "suggestions": "Try lowering min_similarity or rephrasing your query",
                "latency_ms": latency_ms
            }

        # Format results
        documents = []
        for row in results:
            documents.append({
                "doc_path": row['doc_path'],
                "doc_title": row['doc_title'],
                "chunk_index": row['chunk_index'],
                "content": row['chunk_text'],
                "doc_source": row['doc_source'],
                "project_name": row['project_name'],
                "similarity": round(row['similarity_score'], 3),
                "metadata": row['metadata']
            })

        return {
            "found": True,
            "count": len(documents),
            "query": query,
            "documents": documents,
            "latency_ms": latency_ms
        }

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "found": False,
            "error": str(e),
            "message": "Search failed - check Voyage AI key and database is accessible",
            "latency_ms": latency_ms
        }


@mcp.tool()
def get_document(doc_path: str) -> Dict:
    """
    Retrieve a complete document by its path.

    Use this when semantic_search finds a relevant document and you want
    to read the full content.

    Args:
        doc_path: Path to document (e.g., "40-Procedures/Add MCP Server SOP.md")

    Returns:
        Dict with document content and metadata
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        doc_path,
                        doc_title,
                        chunk_index,
                        chunk_text,
                        doc_source,
                        project_name,
                        metadata
                    FROM claude.vault_embeddings
                    WHERE doc_path = %s
                    ORDER BY chunk_index
                """, (doc_path,))

                chunks = cur.fetchall()

        if not chunks:
            return {
                "found": False,
                "message": f"Document '{doc_path}' not found in embeddings"
            }

        # Reassemble document from chunks
        full_text = "\n\n".join(chunk['chunk_text'] for chunk in chunks)

        return {
            "found": True,
            "doc_path": chunks[0]['doc_path'],
            "doc_title": chunks[0]['doc_title'],
            "doc_source": chunks[0]['doc_source'],
            "project_name": chunks[0]['project_name'],
            "content": full_text,
            "metadata": chunks[0]['metadata'],
            "chunks": len(chunks)
        }

    except Exception as e:
        return {
            "found": False,
            "error": str(e)
        }


@mcp.tool()
def list_vault_documents(folder: Optional[str] = None, source: str = "all", project: Optional[str] = None) -> Dict:
    """
    List all documents in the vault embeddings.

    Use this to discover what documentation is available.

    Args:
        folder: Optional folder filter (e.g., "40-Procedures", "20-Domains")
        source: Filter by document source: "all", "vault", "project", or "global" (default "all")
        project: Filter by project name (only applicable for source="project")

    Returns:
        Dict with list of available documents
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Build WHERE clause
                where_clauses = []
                params = []

                if folder:
                    where_clauses.append("doc_path LIKE %s")
                    params.append(f"{folder}%")

                if source != "all":
                    where_clauses.append("doc_source = %s")
                    params.append(source)

                if project:
                    where_clauses.append("project_name = %s")
                    params.append(project)

                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

                cur.execute(f"""
                    SELECT DISTINCT
                        doc_path,
                        doc_title,
                        doc_source,
                        project_name,
                        COUNT(*) as chunks,
                        MAX(updated_at) as last_updated
                    FROM claude.vault_embeddings
                    WHERE {where_clause}
                    GROUP BY doc_path, doc_title, doc_source, project_name
                    ORDER BY doc_path
                """, params)

                documents = cur.fetchall()

        return {
            "found": True,
            "count": len(documents),
            "folder": folder or "all",
            "source": source,
            "project": project,
            "documents": [
                {
                    "path": doc['doc_path'],
                    "title": doc['doc_title'],
                    "doc_source": doc['doc_source'],
                    "project_name": doc['project_name'],
                    "chunks": doc['chunks'],
                    "last_updated": doc['last_updated'].isoformat()
                }
                for doc in documents
            ]
        }

    except Exception as e:
        return {
            "found": False,
            "error": str(e)
        }


@mcp.tool()
def vault_stats() -> Dict:
    """
    Get statistics about the vault embeddings.

    Returns:
        Dict with embedding database statistics
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Overall stats
                cur.execute("""
                    SELECT
                        COUNT(DISTINCT doc_path) as total_documents,
                        COUNT(*) as total_chunks,
                        pg_size_pretty(pg_total_relation_size('claude.vault_embeddings')) as table_size,
                        MIN(created_at) as first_embedded,
                        MAX(updated_at) as last_updated
                    FROM claude.vault_embeddings
                """)
                overall = cur.fetchone()

                # Breakdown by source
                cur.execute("""
                    SELECT
                        doc_source,
                        COUNT(DISTINCT doc_path) as documents,
                        COUNT(*) as chunks
                    FROM claude.vault_embeddings
                    GROUP BY doc_source
                    ORDER BY doc_source
                """)
                by_source = cur.fetchall()

                # Project breakdown (for project docs)
                cur.execute("""
                    SELECT
                        project_name,
                        COUNT(DISTINCT doc_path) as documents,
                        COUNT(*) as chunks
                    FROM claude.vault_embeddings
                    WHERE doc_source = 'project'
                    GROUP BY project_name
                    ORDER BY project_name
                """)
                by_project = cur.fetchall()

        return {
            "total_documents": overall['total_documents'],
            "total_chunks": overall['total_chunks'],
            "table_size": overall['table_size'],
            "first_embedded": overall['first_embedded'].isoformat() if overall['first_embedded'] else None,
            "last_updated": overall['last_updated'].isoformat() if overall['last_updated'] else None,
            "embedding_model": EMBEDDING_MODEL,
            "vector_dimensions": 1024,
            "by_source": [
                {
                    "source": row['doc_source'],
                    "documents": row['documents'],
                    "chunks": row['chunks']
                }
                for row in by_source
            ],
            "by_project": [
                {
                    "project": row['project_name'],
                    "documents": row['documents'],
                    "chunks": row['chunks']
                }
                for row in by_project
            ] if by_project else []
        }

    except Exception as e:
        return {
            "error": str(e)
        }


def main():
    """Run the MCP server."""
    print("Vault RAG MCP Server starting...")

    # Verify Voyage API key
    if not VOYAGE_API_KEY:
        print("[WARN] VOYAGE_API_KEY not set - embeddings will fail")
    else:
        print(f"[OK] Voyage AI configured (model: {EMBEDDING_MODEL}, 1024 dimensions)")

    # Verify database is accessible
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM claude.vault_embeddings")
                count = cur.fetchone()['count']
                print(f"[OK] Database connected ({count} embeddings)")
    except Exception as e:
        print(f"[WARN] Database not accessible: {e}")

    print("Starting server...")
    mcp.run()


if __name__ == "__main__":
    main()
