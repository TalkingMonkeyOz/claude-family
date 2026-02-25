#!/usr/bin/env python3
"""
Feature Embedding Script - Generate embeddings for features and build tasks

Reads features and build_tasks from database, generates embeddings using Voyage AI,
and stores them in vault_embeddings for semantic search.

This enables RAG queries like:
- "what was I working on?"
- "dark mode feature"
- "authentication tasks"

Usage:
    python embed_features.py [--project PROJECT] [--force]
    python embed_features.py --all  # All projects

Options:
    --project PROJECT    Embed features for specific project
    --all               Embed features from all projects
    --force             Re-embed even if unchanged
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
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('feature_embedder')

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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_database_uri
DB_CONNECTION = get_database_uri()
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
EMBEDDING_MODEL = "voyage-3"


def calculate_content_hash(content: str) -> str:
    """Calculate SHA256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def generate_embedding(text: str) -> List[float]:
    """Generate embedding using Voyage AI REST API."""
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


def build_feature_document(feature: Dict, tasks: List[Dict]) -> str:
    """Build a markdown document from feature and tasks for embedding."""
    doc_parts = []

    # Feature header
    doc_parts.append(f"# Feature: {feature['feature_name']}")
    doc_parts.append(f"**Project**: {feature['project_name']}")
    doc_parts.append(f"**Status**: {feature['status']}")
    doc_parts.append(f"**Code**: F{feature['short_code']}")
    doc_parts.append("")

    # Description
    if feature.get('description'):
        doc_parts.append("## Description")
        doc_parts.append(feature['description'])
        doc_parts.append("")

    # Plan data (if present)
    if feature.get('plan_data'):
        plan = feature['plan_data']
        if isinstance(plan, str):
            try:
                plan = json.loads(plan)
            except:
                plan = {}

        if plan.get('requirements'):
            doc_parts.append("## Requirements")
            for req in plan['requirements']:
                doc_parts.append(f"- {req}")
            doc_parts.append("")

        if plan.get('risks'):
            doc_parts.append("## Risks")
            for risk in plan['risks']:
                doc_parts.append(f"- {risk}")
            doc_parts.append("")

        if plan.get('notes'):
            doc_parts.append("## Notes")
            doc_parts.append(plan['notes'])
            doc_parts.append("")

    # Tasks
    if tasks:
        doc_parts.append("## Implementation Tasks")
        for task in tasks:
            status_icon = {
                'completed': '✅',
                'in_progress': '🔄',
                'pending': '⏳',
                'blocked': '🚫'
            }.get(task['status'], '○')

            doc_parts.append(f"### {status_icon} BT{task['short_code']}: {task['task_name']}")
            if task.get('task_description'):
                doc_parts.append(task['task_description'])
            if task.get('files_affected'):
                doc_parts.append(f"**Files**: {', '.join(task['files_affected'])}")
            if task.get('verification'):
                doc_parts.append(f"**Verify**: {task['verification']}")
            doc_parts.append("")

    return "\n".join(doc_parts)


def embed_feature(conn, feature: Dict, tasks: List[Dict], force: bool = False) -> int:
    """Embed a single feature with its tasks."""
    # Build the document
    doc_content = build_feature_document(feature, tasks)
    content_hash = calculate_content_hash(doc_content)

    # Create a unique path for this feature
    doc_path = f"features/{feature['project_name']}/F{feature['short_code']}"
    doc_title = f"Feature F{feature['short_code']}: {feature['feature_name']}"

    # Check if already embedded with same hash
    if not force:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT file_hash FROM claude.vault_embeddings WHERE doc_path = %s LIMIT 1",
                (doc_path,)
            )
            row = cur.fetchone()
            if row and row['file_hash'] == content_hash:
                logger.debug(f"Skipping F{feature['short_code']} (unchanged)")
                return 0
            elif row:
                # Hash changed, delete old embedding
                cur.execute("DELETE FROM claude.vault_embeddings WHERE doc_path = %s", (doc_path,))
                conn.commit()

    # Generate embedding
    logger.info(f"Embedding F{feature['short_code']}: {feature['feature_name']}")
    try:
        embedding = generate_embedding(doc_content)
    except Exception as e:
        logger.error(f"Failed to generate embedding for F{feature['short_code']}: {e}")
        return 0

    # Store embedding
    metadata = {
        'feature_id': str(feature['feature_id']),
        'project_name': feature['project_name'],
        'status': feature['status'],
        'task_count': len(tasks),
        'completed_tasks': sum(1 for t in tasks if t['status'] == 'completed')
    }

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO claude.vault_embeddings
            (doc_path, doc_title, chunk_index, chunk_text, embedding, metadata, file_hash, doc_source, project_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (doc_path, chunk_index)
            DO UPDATE SET
                doc_title = EXCLUDED.doc_title,
                chunk_text = EXCLUDED.chunk_text,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata,
                file_hash = EXCLUDED.file_hash,
                updated_at = NOW()
        """, (
            doc_path,
            doc_title,
            0,  # Features are single-chunk
            doc_content,
            embedding,
            json.dumps(metadata),
            content_hash,
            'feature',  # New doc_source type
            feature['project_name']
        ))
        conn.commit()

    return 1


def get_features(conn, project_name: Optional[str] = None) -> List[Dict]:
    """Get features with optional project filter."""
    query = """
        SELECT
            f.feature_id,
            f.short_code,
            f.feature_name,
            f.description,
            f.status,
            f.priority,
            f.plan_data,
            f.created_at,
            p.project_name
        FROM claude.features f
        JOIN claude.projects p ON f.project_id = p.project_id
    """
    params = []

    if project_name:
        query += " WHERE p.project_name = %s"
        params.append(project_name)

    query += " ORDER BY p.project_name, f.short_code"

    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def get_tasks_for_feature(conn, feature_id: str) -> List[Dict]:
    """Get all build tasks for a feature."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                task_id,
                short_code,
                task_name,
                task_description,
                status,
                step_order,
                files_affected,
                verification
            FROM claude.build_tasks
            WHERE feature_id = %s
            ORDER BY step_order, created_at
        """, (feature_id,))
        return cur.fetchall()


def main():
    parser = argparse.ArgumentParser(description='Generate embeddings for features')
    parser.add_argument('--project', help='Specific project to process')
    parser.add_argument('--all', action='store_true', help='Process all projects')
    parser.add_argument('--force', action='store_true', help='Re-embed even if unchanged')
    args = parser.parse_args()

    if not args.project and not args.all:
        parser.error("Must specify --project PROJECT or --all")

    # Verify Voyage API key
    if not VOYAGE_API_KEY:
        logger.error("VOYAGE_API_KEY environment variable not set")
        sys.exit(1)

    # Connect to database
    try:
        conn = psycopg.connect(DB_CONNECTION, row_factory=dict_row)
        logger.info("Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)

    # Get features
    project_filter = None if args.all else args.project
    features = get_features(conn, project_filter)
    logger.info(f"Found {len(features)} features")

    # Embed each feature
    embedded_count = 0
    for feature in features:
        tasks = get_tasks_for_feature(conn, str(feature['feature_id']))
        embedded_count += embed_feature(conn, feature, tasks, force=args.force)

    # Summary
    logger.info("=" * 60)
    logger.info(f"COMPLETE: Embedded {embedded_count} features")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as count
            FROM claude.vault_embeddings
            WHERE doc_source = 'feature'
        """)
        total = cur.fetchone()['count']

    logger.info(f"Total feature embeddings: {total}")
    logger.info("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
