#!/usr/bin/env python3
"""
Vault Embedding Pipeline - Generate and store embeddings for vault documents

Reads markdown files from knowledge-vault, generates embeddings using Voyage AI,
and stores them in PostgreSQL with pgvector for semantic search.

Features:
- File versioning: Tracks file hash and modification time
- Smart updates: Only re-embeds when file content changes
- Incremental: Skips unchanged files automatically

Usage:
    python embed_vault_documents.py [--folder FOLDER] [--batch-size N] [--force]
    python embed_vault_documents.py --project PROJECT_NAME
    python embed_vault_documents.py --all-projects

Options:
    --folder FOLDER      Only process specific folder (e.g., 40-Procedures)
    --project PROJECT    Embed project documents (CLAUDE.md, ARCHITECTURE.md, etc.)
    --all-projects       Embed documents from all active projects
    --source SOURCE      Document source type: vault|project|global (default: auto-detect)
    --batch-size N       Number of docs to process per batch (default: 10)
    --force             Re-embed documents even if unchanged (ignores hash check)
"""

import os

# CRITICAL: Disable tokenizers parallelism BEFORE any imports
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
import gc
import hashlib
import json
import logging
import multiprocessing
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('vault_embedder')

# Try to import dependencies
try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    logger.error("psycopg not installed. Run: pip install psycopg")
    sys.exit(1)

try:
    import requests
except ImportError:
    logger.error("requests not installed. Run: pip install requests")
    sys.exit(1)

# Configuration
VAULT_PATH = Path("C:/Projects/claude-family/knowledge-vault")
DB_CONNECTION = "postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation"
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
EMBEDDING_MODEL = "voyage-3"  # voyage-3 or voyage-3-lite
CHUNK_SIZE = 1000  # Characters per chunk
CHUNK_OVERLAP = 200  # Character overlap between chunks


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file content."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter from markdown content."""
    frontmatter = {}
    body = content

    # Check for YAML frontmatter (--- at start)
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                import yaml
                from datetime import date, datetime
                frontmatter = yaml.safe_load(parts[1]) or {}
                # Convert date objects to strings for JSON serialization
                for key, value in frontmatter.items():
                    if isinstance(value, (date, datetime)):
                        frontmatter[key] = value.isoformat()
                    elif isinstance(value, list):
                        frontmatter[key] = [v.isoformat() if isinstance(v, (date, datetime)) else v for v in value]
                body = parts[2].strip()
            except ImportError:
                # If yaml not available, parse simple key: value pairs
                for line in parts[1].strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        frontmatter[key.strip()] = value.strip()
                body = parts[2].strip()
            except Exception as e:
                logger.warning(f"Failed to parse frontmatter: {e}")

    return frontmatter, body


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    logger.info(f"chunk_text: text_len={len(text)}, chunk_size={chunk_size}, overlap={overlap}")
    if len(text) <= chunk_size:
        logger.info(f"Text fits in one chunk, returning")
        return [text]

    chunks = []
    start = 0
    iterations = 0
    max_iterations = len(text) // (chunk_size - overlap) + 10  # Safety limit

    while start < len(text):
        iterations += 1
        if iterations > max_iterations:
            logger.error(f"INFINITE LOOP DETECTED! iterations={iterations}, start={start}, len={len(text)}")
            break

        end = start + chunk_size
        logger.info(f"Iteration {iterations}: start={start}, end={end}")

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            sentence_end = max(
                text.rfind('. ', start, end),
                text.rfind('! ', start, end),
                text.rfind('? ', start, end),
                text.rfind('\n\n', start, end)
            )
            if sentence_end > start:
                end = sentence_end + 1
                logger.info(f"  Adjusted end to sentence boundary: {end}")

        chunks.append(text[start:end].strip())
        old_start = start
        # Ensure we always move forward (prevent infinite loop)
        start = max(old_start + 1, end - overlap)
        logger.info(f"  New start: {start} (moved {start - old_start} chars)")

        if start >= len(text):
            logger.info(f"  Reached end, breaking")
            break

    logger.info(f"chunk_text complete: {len(chunks)} chunks in {iterations} iterations")
    return chunks


def generate_embedding(text: str) -> List[float]:
    """Generate embedding using Voyage AI REST API."""
    try:
        if not VOYAGE_API_KEY:
            raise RuntimeError("VOYAGE_API_KEY environment variable not set")

        response = requests.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {VOYAGE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "input": [text],
                "model": EMBEDDING_MODEL,
                "input_type": "document"
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise


def process_document(file_path: Path, conn, force: bool = False, doc_source: str = 'vault', project_name: Optional[str] = None, base_path: Optional[Path] = None) -> int:
    """Process a single document and store embeddings.

    Args:
        file_path: Path to the document file
        conn: Database connection
        force: Whether to re-embed unchanged files
        doc_source: Source type (vault|project|global)
        project_name: Project name for project documents
        base_path: Base path for calculating relative paths (defaults to VAULT_PATH)
    """
    if base_path is None:
        base_path = VAULT_PATH
    relative_path = str(file_path.relative_to(base_path))
    logger.info(f"ENTER process_document: {relative_path}")

    # Calculate file hash and get modification time
    file_hash = calculate_file_hash(file_path)
    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    logger.info(f"File hash: {file_hash[:16]}... | Modified: {file_mtime}")

    # Check if already embedded and hash unchanged
    if not force:
        logger.info(f"Checking if {relative_path} already embedded...")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT file_hash FROM claude.vault_embeddings WHERE doc_path = %s LIMIT 1",
                (relative_path,)
            )
            row = cur.fetchone()
            if row and row['file_hash'] == file_hash:
                logger.info(f"Skipping {relative_path} (unchanged, hash matches)")
                return 0
            elif row:
                logger.info(f"Hash changed - will re-embed {relative_path}")
                # Delete old embeddings
                cur.execute("DELETE FROM claude.vault_embeddings WHERE doc_path = %s", (relative_path,))
                conn.commit()

    logger.info(f"Will process {relative_path}")
    # Read document
    try:
        logger.info(f"Reading file...")
        content = file_path.read_text(encoding='utf-8')
        logger.info(f"Read {len(content)} chars")
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return 0

    # Extract frontmatter and body
    logger.info(f"Extracting frontmatter...")
    frontmatter, body = extract_frontmatter(content)
    doc_title = frontmatter.get('title', file_path.stem)
    logger.info(f"Title: {doc_title}")

    # Chunk the document
    logger.info(f"Chunking document...")
    chunks = chunk_text(body)
    logger.info(f"Processing {relative_path} ({len(chunks)} chunks)")

    # Generate and store embeddings for each chunk
    embedded_count = 0
    for idx, chunk in enumerate(chunks):
        try:
            # Generate embedding
            logger.info(f"  Embedding chunk {idx+1}/{len(chunks)}...")
            embedding = generate_embedding(chunk)
            logger.info(f"  Got {len(embedding)} dimensions")

            # Store in database
            logger.info(f"  Writing to DB...")
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO claude.vault_embeddings
                    (doc_path, doc_title, chunk_index, chunk_text, embedding, metadata, file_hash, file_modified_at, doc_source, project_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doc_path, chunk_index)
                    DO UPDATE SET
                        chunk_text = EXCLUDED.chunk_text,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        file_hash = EXCLUDED.file_hash,
                        file_modified_at = EXCLUDED.file_modified_at,
                        doc_source = EXCLUDED.doc_source,
                        project_name = EXCLUDED.project_name,
                        updated_at = NOW()
                """, (
                    relative_path,
                    doc_title,
                    idx,
                    chunk,
                    embedding,
                    json.dumps(frontmatter),
                    file_hash,
                    file_mtime,
                    doc_source,
                    project_name
                ))
                embedded_count += 1
            logger.info(f"  Written")

            # Commit after each chunk to free memory
            logger.info(f"  Committing...")
            conn.commit()
            logger.info(f"  Done!")

        except Exception as e:
            logger.error(f"Failed to embed chunk {idx} of {relative_path}: {e}")
            continue

    return embedded_count


def get_active_projects(conn) -> List[Dict]:
    """Query database for active projects."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT project_name, workspace_path
            FROM claude.workspaces
            WHERE status = 'active'
            ORDER BY project_name
        """)
        return cur.fetchall()


def get_project_docs(project_path: Path) -> List[Path]:
    """Get standard project documentation files."""
    doc_files = []
    standard_docs = ['CLAUDE.md', 'ARCHITECTURE.md', 'PROBLEM_STATEMENT.md', 'README.md']

    for doc_name in standard_docs:
        doc_path = project_path / doc_name
        if doc_path.exists():
            doc_files.append(doc_path)

    return doc_files


def process_project_documents(conn, project_name: str, project_path: str, force: bool = False) -> int:
    """Process all standard documentation files for a project."""
    logger.info(f"Processing project: {project_name}")
    path = Path(project_path)

    if not path.exists():
        logger.error(f"Project path not found: {project_path}")
        return 0

    doc_files = get_project_docs(path)
    if not doc_files:
        logger.warning(f"No standard docs found for {project_name}")
        return 0

    logger.info(f"Found {len(doc_files)} docs for {project_name}")

    total_chunks = 0
    for doc_file in doc_files:
        try:
            chunks_embedded = process_document(
                doc_file,
                conn,
                force=force,
                doc_source='project',
                project_name=project_name,
                base_path=path
            )
            total_chunks += chunks_embedded
            gc.collect()
        except Exception as e:
            logger.error(f"Failed to process {doc_file}: {e}")
            continue

    return total_chunks


def main():
    parser = argparse.ArgumentParser(description='Generate embeddings for vault documents')
    parser.add_argument('--folder', help='Specific folder to process (e.g., 40-Procedures)')
    parser.add_argument('--project', help='Process specific project documents')
    parser.add_argument('--all-projects', action='store_true', help='Process all active project documents')
    parser.add_argument('--source', default='vault', choices=['vault', 'project', 'global'],
                       help='Document source type')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size')
    parser.add_argument('--force', action='store_true', help='Re-embed existing documents')
    args = parser.parse_args()

    # Connect to database
    try:
        conn = psycopg.connect(DB_CONNECTION, row_factory=dict_row)
        logger.info("Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)

    # Verify Voyage API key
    if not VOYAGE_API_KEY:
        logger.error("VOYAGE_API_KEY environment variable not set")
        logger.error("Get your API key from: https://www.voyageai.com/")
        sys.exit(1)
    else:
        logger.info(f"Voyage AI configured (model: {EMBEDDING_MODEL}, 1024 dimensions)")

    total_chunks = 0

    # Handle project document processing
    if args.all_projects:
        logger.info("Processing all active projects")
        projects = get_active_projects(conn)
        logger.info(f"Found {len(projects)} active projects")

        for project in projects:
            total_chunks += process_project_documents(
                conn,
                project['project_name'],
                project['workspace_path'],
                force=args.force
            )

    elif args.project:
        logger.info(f"Processing project: {args.project}")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT project_name, workspace_path
                FROM claude.workspaces
                WHERE project_name = %s
            """, (args.project,))
            project = cur.fetchone()

        if not project:
            logger.error(f"Project not found: {args.project}")
            sys.exit(1)

        total_chunks += process_project_documents(
            conn,
            project['project_name'],
            project['workspace_path'],
            force=args.force
        )

    else:
        # Process vault documents
        if args.folder:
            search_path = VAULT_PATH / args.folder
            if not search_path.exists():
                logger.error(f"Folder not found: {search_path}")
                sys.exit(1)
        else:
            search_path = VAULT_PATH

        md_files = list(search_path.rglob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files")

        # Process documents
        for idx, file_path in enumerate(md_files, 1):
            logger.info(f"[{idx}/{len(md_files)}] {file_path.relative_to(VAULT_PATH)}")
            try:
                chunks_embedded = process_document(
                    file_path,
                    conn,
                    force=args.force,
                    doc_source=args.source
                )
                total_chunks += chunks_embedded

                # Force garbage collection after each document to free memory
                gc.collect()

            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue

    # Summary
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(DISTINCT doc_path) as docs,
                COUNT(*) as chunks,
                pg_size_pretty(pg_total_relation_size('claude.vault_embeddings')) as size
            FROM claude.vault_embeddings
        """)
        stats = cur.fetchone()

    logger.info("=" * 60)
    logger.info(f"COMPLETE: Embedded {total_chunks} new chunks")
    logger.info(f"Total: {stats['docs']} documents, {stats['chunks']} chunks, {stats['size']}")
    logger.info("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
