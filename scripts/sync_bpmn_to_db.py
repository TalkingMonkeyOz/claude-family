#!/usr/bin/env python3
"""Thin wrapper to sync BPMN processes from disk to database registry.

Used by Tauri backend to trigger registry sync from the UI.
Imports the sync logic from the bpmn-engine MCP server.

Usage:
    python scripts/sync_bpmn_to_db.py [project_name]
"""

import sys
import os
import hashlib
import json

# Add bpmn-engine server to path so we can use its XML helpers
_BPMN_SERVER_DIR = os.path.join(os.path.dirname(__file__), '..', 'mcp-servers', 'bpmn-engine')
sys.path.insert(0, _BPMN_SERVER_DIR)

from server import _parse_xml, _extract_process_elements, BPMN_TAG

# Use shared config for DB connection (handles .env loading, psycopg v2/v3 detection)
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPTS_DIR)
from config import get_db_connection


def _parse_bpmn_file(full_path: str) -> dict:
    """Parse a BPMN file and return a dict with process metadata.

    Returns dict with keys: process_id, name, elements, flows.
    Returns None if the file cannot be parsed or contains no process element.
    """
    from pathlib import Path
    try:
        root = _parse_xml(Path(full_path))
        process_els = list(root.iter(f"{BPMN_TAG}process"))
        if not process_els:
            return None
        # Use the first process element
        process_el = process_els[0]
        process_id = process_el.get("id", os.path.splitext(os.path.basename(full_path))[0])
        name = process_el.get("name", process_id)
        elements, flows = _extract_process_elements(process_el)
        return {
            "process_id": process_id,
            "name": name,
            "elements": elements,
            "flows": flows,
        }
    except Exception as e:
        return None


def sync_bpmn_processes(project: str = '') -> dict:
    """Sync BPMN files to claude.bpmn_processes table."""
    conn = get_db_connection()
    if not conn:
        return {'synced': 0, 'skipped': 0, 'errors': ['DB connection unavailable'], 'total': 0}
    cur = conn.cursor()

    # Get project paths from workspaces
    if project:
        cur.execute(
            "SELECT project_name, project_path FROM claude.workspaces WHERE project_name = %s AND is_active = true",
            (project,)
        )
    else:
        cur.execute(
            "SELECT project_name, project_path FROM claude.workspaces WHERE is_active = true AND project_path IS NOT NULL"
        )

    rows = cur.fetchall()
    synced = 0
    skipped = 0
    errors = []

    for row in rows:
        # Support both dict-row (psycopg3/RealDictCursor) and plain tuple rows
        if isinstance(row, dict):
            project_name = row['project_name']
            project_path = row['project_path']
        else:
            project_name, project_path = row
        if not project_path or not os.path.isdir(project_path):
            continue

        # Find .bpmn files
        processes_dir = os.path.join(project_path, 'processes')
        if not os.path.isdir(processes_dir):
            # Also check mcp-servers/bpmn-engine/processes for claude-family
            alt_dir = os.path.join(project_path, 'mcp-servers', 'bpmn-engine', 'processes')
            if os.path.isdir(alt_dir):
                processes_dir = alt_dir
            else:
                continue

        for root, _dirs, files in os.walk(processes_dir):
            for fname in files:
                if not fname.endswith('.bpmn'):
                    continue

                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, project_path).replace('\\', '/')

                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    file_hash = hashlib.sha256(content.encode()).hexdigest()

                    # Check if already synced with same hash
                    cur.execute(
                        "SELECT file_hash FROM claude.bpmn_processes WHERE file_path = %s AND project_name = %s",
                        (rel_path, project_name)
                    )
                    existing = cur.fetchone()
                    existing_hash = existing['file_hash'] if isinstance(existing, dict) else (existing[0] if existing else None)
                    if existing_hash and existing_hash == file_hash:
                        skipped += 1
                        continue

                    # Parse the BPMN file
                    parsed = _parse_bpmn_file(full_path)
                    if not parsed:
                        errors.append(f"Failed to parse: {rel_path}")
                        continue

                    process_id = parsed.get('process_id', fname.replace('.bpmn', ''))
                    process_name = parsed.get('name', process_id)

                    # Determine level from process_id or path
                    level = None
                    if process_id.startswith('L0_'):
                        level = 'L0'
                    elif process_id.startswith('L1_'):
                        level = 'L1'
                    elif process_id.startswith('L2_'):
                        level = 'L2'

                    # Determine category from directory
                    rel_dir = os.path.dirname(rel_path)
                    category = os.path.basename(rel_dir) if rel_dir else None

                    elements = json.dumps(parsed.get('elements', []))
                    flows = json.dumps(parsed.get('flows', []))

                    cur.execute("""
                        INSERT INTO claude.bpmn_processes
                            (process_id, process_name, level, category, project_name,
                             file_path, file_hash, elements, flows, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, NOW())
                        ON CONFLICT (process_id) DO UPDATE SET
                            process_name = EXCLUDED.process_name,
                            level = EXCLUDED.level,
                            category = EXCLUDED.category,
                            file_path = EXCLUDED.file_path,
                            file_hash = EXCLUDED.file_hash,
                            elements = EXCLUDED.elements,
                            flows = EXCLUDED.flows,
                            updated_at = NOW()
                    """, (process_id, process_name, level, category, project_name,
                          rel_path, file_hash, elements, flows))

                    synced += 1

                except Exception as e:
                    errors.append(f"{rel_path}: {e}")

    conn.commit()
    cur.close()
    conn.close()

    return {
        'synced': synced,
        'skipped': skipped,
        'errors': errors,
        'total': synced + skipped + len(errors),
    }


if __name__ == '__main__':
    project_filter = sys.argv[1] if len(sys.argv) > 1 else ''
    result = sync_bpmn_processes(project_filter)
    print(f"Synced: {result['synced']}, Skipped: {result['skipped']}, Errors: {len(result['errors'])}")
    if result['errors']:
        for err in result['errors']:
            print(f"  ERROR: {err}")
