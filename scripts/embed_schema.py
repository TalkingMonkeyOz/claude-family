#!/usr/bin/env python3
"""
Schema Embedding Pipeline - Generate and store embeddings for database schema metadata

Introspects PostgreSQL schema, generates rich text descriptions, embeds via embedding_provider,
and stores embeddings in claude.schema_registry for semantic search (RAG).

Features:
- Automatic schema introspection: Tables, columns, types, comments, constraints
- Smart updates: Only re-embeds when schema changes (via content hash)
- Relationship discovery: FKs, CHECK constraints, row counts
- Graceful degradation: Handles missing pgvector extension

Usage:
    python embed_schema.py [--force] [--dry-run] [--table TABLE_NAME]

Options:
    --force                 Re-embed all tables (ignores hash check)
    --dry-run              Show what would be embedded without calling API
    --table TABLE_NAME     Only process specific table
"""

import os

# CRITICAL: Disable tokenizers parallelism BEFORE any imports
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('schema_embedder')

# Try to import dependencies
try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    logger.error("psycopg not installed. Run: pip install psycopg")
    sys.exit(1)

# Configuration
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection
from embedding_provider import embed as embed_text
SCHEMA_NAME = "claude"

# Common column descriptions for heuristics
COMMON_COLUMNS = {
    'created_at': 'Timestamp when the record was created',
    'updated_at': 'Timestamp when the record was last updated',
    'id': 'Primary key (UUID)',
    'project_id': 'Foreign key to claude.projects',
    'session_id': 'Foreign key to claude.sessions',
    'feature_id': 'Foreign key to claude.features',
    'feedback_id': 'Foreign key to claude.feedback',
    'is_active': 'Whether this record is currently active',
    'is_archived': 'Whether this record has been archived',
    'status': 'Current lifecycle status',
    'priority': 'Priority level (1=critical, 5=low)',
    'description': 'Human-readable description',
    'embedding': 'Vector embedding (1024 dimensions)',
    'metadata': 'Additional metadata as JSONB',
    'content_hash': 'SHA256 hash of content for change detection',
    'created_by': 'Identity/system that created this record',
    'updated_by': 'Identity/system that last updated this record',
}


def ensure_schema_columns(conn) -> bool:
    """Check if embedding columns exist, add if missing."""
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Check if embedding column exists
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = %s
                    AND table_name = 'schema_registry'
                    AND column_name = 'embedding'
                )
            """, (SCHEMA_NAME,))
            result = cur.fetchone()
            has_embedding = result['exists'] if isinstance(result, dict) else result[0]

            if not has_embedding:
                logger.info("Adding embedding column to schema_registry...")
                cur.execute("""
                    ALTER TABLE claude.schema_registry
                    ADD COLUMN IF NOT EXISTS embedding vector(1024);
                """)
                logger.info("✓ Added embedding column")

            # Add other supporting columns
            cur.execute("""
                ALTER TABLE claude.schema_registry
                ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
            """)
            cur.execute("""
                ALTER TABLE claude.schema_registry
                ADD COLUMN IF NOT EXISTS column_descriptions JSONB;
            """)
            cur.execute("""
                ALTER TABLE claude.schema_registry
                ADD COLUMN IF NOT EXISTS fk_relationships JSONB;
            """)
            cur.execute("""
                ALTER TABLE claude.schema_registry
                ADD COLUMN IF NOT EXISTS row_count_actual INTEGER;
            """)

            logger.info("✓ Schema columns ready")
            return True
    except Exception as e:
        logger.error(f"Failed to ensure schema columns: {e}")
        return False
    finally:
        conn.autocommit = False


def generate_embedding(text: str) -> List[float]:
    """Generate embedding using the configured provider (FastEmbed local or Voyage AI API)."""
    try:
        result = embed_text(text)
        if result is None:
            raise RuntimeError("Embedding provider returned None")
        return result
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise


def get_table_comment(conn, table_name: str) -> str:
    """Get table comment from pg_description."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT obj_description(
                    (SELECT oid FROM pg_class WHERE relname = %s AND relnamespace =
                        (SELECT oid FROM pg_namespace WHERE nspname = %s)),
                    'pg_class'
                ) AS comment
            """, (table_name, SCHEMA_NAME))
            result = cur.fetchone()
            val = result['comment'] if isinstance(result, dict) else result[0]
            return val if val else ""
    except Exception as e:
        logger.warning(f"Failed to get comment for {table_name}: {e}")
        return ""


def get_columns_info(conn, table_name: str) -> Dict[str, Dict]:
    """Get detailed column information: type, nullable, default, comment."""
    columns = {}
    try:
        with conn.cursor() as cur:
            # Get column info from information_schema
            cur.execute("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    ordinal_position
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = %s
                ORDER BY ordinal_position
            """, (SCHEMA_NAME, table_name))

            for row in cur.fetchall():
                col_name = row['column_name']
                col_type = row['data_type']

                # Try to get column comment
                comment = ""
                try:
                    cur.execute("""
                        SELECT col_description(
                            (SELECT oid FROM pg_class
                             WHERE relname = %s AND relnamespace =
                                (SELECT oid FROM pg_namespace WHERE nspname = %s)),
                            %s::int
                        ) AS comment
                    """, (table_name, SCHEMA_NAME, row['ordinal_position']))
                    comment_result = cur.fetchone()
                    val = comment_result['comment'] if isinstance(comment_result, dict) else comment_result[0]
                    if val:
                        comment = val
                except Exception as e:
                    logger.debug(f"Failed to get comment for {table_name}.{col_name}: {e}")

                # Use heuristic if no comment
                if not comment and col_name in COMMON_COLUMNS:
                    comment = COMMON_COLUMNS[col_name]

                columns[col_name] = {
                    'type': col_type,
                    'nullable': row['is_nullable'] == 'YES',
                    'default': row['column_default'],
                    'comment': comment
                }
    except Exception as e:
        logger.error(f"Failed to get columns for {table_name}: {e}")

    return columns


def get_fk_relationships(conn, table_name: str) -> List[Dict]:
    """Get foreign key relationships for this table."""
    relationships = []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS referenced_table,
                    ccu.column_name AS referenced_column
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s
            """, (SCHEMA_NAME, table_name))

            for row in cur.fetchall():
                relationships.append({
                    'column': row['column_name'],
                    'references': f"{row['referenced_table']}.{row['referenced_column']}"
                })
    except Exception as e:
        logger.debug(f"Failed to get FKs for {table_name}: {e}")

    return relationships


def get_check_constraints(conn, table_name: str) -> List[str]:
    """Get CHECK constraints for this table."""
    constraints = []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cc.check_clause
                FROM information_schema.table_constraints tc
                JOIN information_schema.check_constraints cc
                    ON tc.constraint_name = cc.constraint_name
                    AND tc.constraint_schema = cc.constraint_schema
                WHERE tc.table_schema = %s
                AND tc.table_name = %s
                AND tc.constraint_type = 'CHECK'
            """, (SCHEMA_NAME, table_name))

            for row in cur.fetchall():
                constraints.append(row['check_clause'])
    except Exception as e:
        logger.debug(f"Failed to get CHECK constraints for {table_name}: {e}")

    return constraints


def get_row_count(conn, table_name: str) -> Optional[int]:
    """Get approximate row count from pg_stat_user_tables."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT n_live_tup AS row_count
                FROM pg_stat_user_tables
                WHERE schemaname = %s
                AND relname = %s
            """, (SCHEMA_NAME, table_name))
            result = cur.fetchone()
            return result['row_count'] if result else None
    except Exception as e:
        logger.debug(f"Failed to get row count for {table_name}: {e}")
        return None


def build_embeddable_text(table_name: str, columns: Dict, fks: List, checks: List,
                         row_count: Optional[int], comment: str) -> str:
    """Build rich text description for embedding."""
    parts = [
        f"Table: claude.{table_name}",
    ]

    if comment:
        parts.append(f"Purpose: {comment}")
    else:
        parts.append(f"Purpose: (no description provided)")

    # Columns section
    parts.append("\nColumns:")
    for col_name, col_info in columns.items():
        col_def = f"  - {col_name} ({col_info['type']})"
        if col_info['comment']:
            col_def += f": {col_info['comment']}"
        parts.append(col_def)

    # Foreign keys section
    if fks:
        parts.append("\nForeign Key Relationships:")
        for fk in fks:
            parts.append(f"  - {fk['column']} references {fk['references']}")

    # Check constraints section
    if checks:
        parts.append("\nConstraints:")
        for check in checks:
            parts.append(f"  - {check}")

    # Row count section
    if row_count is not None:
        parts.append(f"\nRow count: ~{row_count:,} rows")

    return "\n".join(parts)


def process_table(conn, table_name: str, force: bool = False, dry_run: bool = False) -> bool:
    """Process a single table and store embedding.

    Returns True if successfully embedded, False otherwise.
    """
    logger.info(f"Processing table: {SCHEMA_NAME}.{table_name}")

    try:
        # Get schema metadata
        comment = get_table_comment(conn, table_name)
        columns = get_columns_info(conn, table_name)
        fks = get_fk_relationships(conn, table_name)
        checks = get_check_constraints(conn, table_name)
        row_count = get_row_count(conn, table_name)

        if not columns:
            logger.warning(f"No columns found for {table_name}, skipping")
            return False

        # Build embeddable text
        embeddable_text = build_embeddable_text(table_name, columns, fks, checks, row_count, comment)
        content_hash = hashlib.sha256(embeddable_text.encode()).hexdigest()

        # Check if already embedded and unchanged
        if not force:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT content_hash FROM claude.schema_registry
                    WHERE table_name = %s LIMIT 1
                """, (table_name,))
                result = cur.fetchone()
                if result and result['content_hash'] == content_hash:
                    logger.info(f"  ✓ Skipping (unchanged, hash matches)")
                    return True
                elif result:
                    logger.info(f"  Schema changed - will re-embed")

        if dry_run:
            logger.info(f"  [DRY RUN] Would embed: {len(embeddable_text)} chars, hash {content_hash[:16]}...")
            return True

        # Generate embedding
        logger.info(f"  Generating embedding ({len(embeddable_text)} chars)...")
        embedding = generate_embedding(embeddable_text)
        logger.info(f"  ✓ Got {len(embedding)} dimensions")

        # Store in database
        logger.info(f"  Writing to database...")
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO claude.schema_registry
                (table_name, purpose, column_descriptions, fk_relationships,
                 row_count_actual, content_hash, embedding, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (table_name) DO UPDATE SET
                    purpose = EXCLUDED.purpose,
                    column_descriptions = EXCLUDED.column_descriptions,
                    fk_relationships = EXCLUDED.fk_relationships,
                    row_count_actual = EXCLUDED.row_count_actual,
                    content_hash = EXCLUDED.content_hash,
                    embedding = EXCLUDED.embedding,
                    last_reviewed = CURRENT_DATE
            """, (
                table_name,
                comment or "(no description)",
                json.dumps(columns),
                json.dumps(fks),
                row_count,
                content_hash,
                embedding,
                'embed_schema.py'
            ))
        conn.commit()
        logger.info(f"  ✓ Stored")
        return True

    except Exception as e:
        logger.error(f"Failed to process {table_name}: {e}")
        conn.rollback()
        return False


def get_claude_tables(conn) -> List[str]:
    """Get all tables in claude schema."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """, (SCHEMA_NAME,))
            return [row['table_name'] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get table list: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='Embed database schema for RAG search')
    parser.add_argument('--force', action='store_true', help='Re-embed all tables')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be embedded without calling API')
    parser.add_argument('--table', help='Only process specific table')
    args = parser.parse_args()

    # Connect to database
    try:
        conn = get_db_connection(strict=True)
        logger.info("Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)

    # Log embedding provider info
    from embedding_provider import get_provider_info
    provider_info = get_provider_info()
    logger.info(f"Embedding provider: {provider_info['provider']} (model: {provider_info['model']}, {provider_info['dimensions']} dims)")

    # Ensure schema columns exist
    if not ensure_schema_columns(conn):
        logger.error("Failed to prepare schema columns")
        sys.exit(1)

    # Get list of tables to process
    if args.table:
        tables = [args.table]
    else:
        tables = get_claude_tables(conn)
        logger.info(f"Found {len(tables)} tables in claude schema")

    # Process tables
    success_count = 0
    error_count = 0
    skip_count = 0

    for idx, table_name in enumerate(tables, 1):
        logger.info(f"\n[{idx}/{len(tables)}] {table_name}")
        try:
            if process_table(conn, table_name, force=args.force, dry_run=args.dry_run):
                success_count += 1
            else:
                skip_count += 1
        except Exception as e:
            logger.error(f"Unhandled error for {table_name}: {e}")
            error_count += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info(f"COMPLETE:")
    logger.info(f"  ✓ Embedded: {success_count} tables")
    if skip_count > 0:
        logger.info(f"  ⊘ Skipped: {skip_count} tables")
    if error_count > 0:
        logger.info(f"  ✗ Errors: {error_count} tables")
    logger.info("=" * 60)

    # Show stats
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) as total_tables,
                    COUNT(embedding) as embedded_tables,
                    COUNT(content_hash) as with_hash,
                    pg_size_pretty(pg_total_relation_size('claude.schema_registry')) as size
                FROM claude.schema_registry
            """)
            stats = cur.fetchone()
            logger.info(f"\nRegistry stats:")
            logger.info(f"  Total: {stats['total_tables']} tables")
            logger.info(f"  Embedded: {stats['embedded_tables']} with embeddings")
            logger.info(f"  With hashes: {stats['with_hash']}")
            logger.info(f"  Size: {stats['size']}")
    except Exception as e:
        logger.warning(f"Failed to get registry stats: {e}")

    conn.close()
    sys.exit(0 if error_count == 0 else 1)


if __name__ == "__main__":
    main()
