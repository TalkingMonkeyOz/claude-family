#!/usr/bin/env python3
"""
System Maintenance Engine

Implements the detection and repair pipeline from the BPMN model:
  mcp-servers/bpmn-engine/processes/infrastructure/system_maintenance.bpmn

Monitors 5 subsystems for staleness and optionally repairs them:
  1. Schema registry   - claude.schema_registry vs information_schema.tables
  2. Vault embeddings  - claude.vault_embeddings vs knowledge-vault/ .md files
  3. BPMN registry     - claude.bpmn_processes vs processes/**/*.bpmn files
  4. Memory embeddings - claude.knowledge tier='mid' entries missing embeddings
  5. Column registry   - claude.column_registry vs pg_catalog CHECK constraints

Architecture:
  - Detection is FAST (lightweight DB queries only, no Voyage AI calls)
  - Repair uses subprocess calls to existing scripts or direct DB+API calls
  - Each subsystem is independent: failures don't block others
  - Imported by MCP tool (full detect+repair) and SessionStart hook (detect-only)

Usage:
    python system_maintenance.py [--scope SCOPE] [--repair]

Options:
    --scope    full | detect_only | schema | vault | bpmn | memory | column_registry
    --repair   Enable auto-repair (default: detect-only)
"""

import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add scripts directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg
from embedding_provider import embed as _embed_text

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('system_maintenance')

# ============================================================================
# Constants
# ============================================================================

SCRIPTS_DIR = Path(__file__).parent.resolve()
VAULT_PATH = Path(r'C:\Projects\claude-family\knowledge-vault')
BPMN_PROCESSES_DIR = Path(r'C:\Projects\claude-family\mcp-servers\bpmn-engine\processes')


BPMN_NS = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}

# Level/category inference map (mirrors server_v2.py _LEVEL_CATEGORY_MAP)
_LEVEL_CATEGORY_MAP = {
    "L0_": ("L0", "architecture"),
    "L1_": ("L1", "architecture"),
    "processes/architecture/": ("L0", "architecture"),
    "processes/lifecycle/": ("L2", "lifecycle"),
    "processes/development/": ("L2", "development"),
    "processes/infrastructure/": ("L2", "infrastructure"),
    "processes/nimbus/": ("L2", "nimbus"),
}


# ============================================================================
# Helpers
# ============================================================================

def _fetchall(conn, query: str, params=None) -> list:
    """Execute a SELECT query and return all rows as dicts."""
    _, version, dict_row_factory, cursor_class = detect_psycopg()
    if version == 3:
        with conn.cursor(row_factory=dict_row_factory) as cur:
            cur.execute(query, params or ())
            return cur.fetchall()
    else:
        with conn.cursor(cursor_factory=cursor_class) as cur:
            cur.execute(query, params or ())
            return cur.fetchall()


def _fetchone(conn, query: str, params=None) -> Optional[dict]:
    """Execute a SELECT query and return the first row as a dict."""
    _, version, dict_row_factory, cursor_class = detect_psycopg()
    if version == 3:
        with conn.cursor(row_factory=dict_row_factory) as cur:
            cur.execute(query, params or ())
            return cur.fetchone()
    else:
        with conn.cursor(cursor_factory=cursor_class) as cur:
            cur.execute(query, params or ())
            return cur.fetchone()


def _execute(conn, query: str, params=None):
    """Execute a non-SELECT query."""
    with conn.cursor() as cur:
        cur.execute(query, params or ())


def _sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file's content."""
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha.update(chunk)
    return sha.hexdigest()


def _generate_embedding(text: str) -> Optional[list]:
    """Generate embedding using the configured provider (FastEmbed or Voyage AI). Returns None on failure."""
    try:
        return _embed_text(text)
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return None


def _infer_bpmn_level_category(process_id: str, file_path: str) -> tuple:
    """Infer BPMN level and category from process_id and file path."""
    norm_path = file_path.replace("\\", "/")
    for prefix, (level, category) in _LEVEL_CATEGORY_MAP.items():
        if process_id.startswith(prefix) or prefix in norm_path:
            return level, category
    return "L2", "unknown"


def _parse_bpmn_file(file_path: str) -> Optional[dict]:
    """Parse a BPMN file and extract process metadata.

    Mirrors _parse_bpmn_file from mcp-servers/project-tools/server_v2.py.
    Returns None on parse failure.
    """
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Find the first executable process (or any process)
        process = root.find(".//bpmn:process[@isExecutable='true']", BPMN_NS)
        if process is None:
            process = root.find(".//bpmn:process", BPMN_NS)
        if process is None:
            return None

        process_id = process.get("id", "")
        process_name = process.get("name", process_id)

        # Extract elements
        elements = []
        element_types = [
            "startEvent", "endEvent", "userTask", "scriptTask", "serviceTask",
            "exclusiveGateway", "parallelGateway", "callActivity",
        ]
        for etype in element_types:
            for elem in process.findall(f"bpmn:{etype}", BPMN_NS):
                elements.append({
                    "id": elem.get("id", ""),
                    "type": etype,
                    "name": elem.get("name", ""),
                })

        # Extract sequence flows
        flows = []
        for flow in process.findall("bpmn:sequenceFlow", BPMN_NS):
            cond_elem = flow.find("bpmn:conditionExpression", BPMN_NS)
            flows.append({
                "id": flow.get("id", ""),
                "from": flow.get("sourceRef", ""),
                "to": flow.get("targetRef", ""),
                "condition": cond_elem.text if cond_elem is not None else None,
            })

        # Build description from element names
        element_names = [e["name"] for e in elements if e["name"]]
        description = f"{process_name}: {', '.join(element_names[:10])}"

        level, category = _infer_bpmn_level_category(process_id, file_path)

        return {
            "process_id": process_id,
            "process_name": process_name,
            "level": level,
            "category": category,
            "description": description,
            "elements": elements,
            "flows": flows,
        }
    except Exception as e:
        logger.debug(f"BPMN parse error for {file_path}: {e}")
        return None


# ============================================================================
# DETECTION FUNCTIONS (fast, lightweight DB queries — no Voyage AI)
# ============================================================================

def check_schema_staleness(conn) -> dict:
    """Compare information_schema.tables count vs claude.schema_registry count.

    Also spot-checks for tables in information_schema not in the registry.
    Fast: COUNT queries and a LEFT JOIN only — no file I/O, no Voyage AI.

    Returns:
        {
            'stale': bool,
            'new_tables': int,
            'changed_tables': int,
            'details': list[str]
        }
    """
    try:
        # Count tables in information_schema
        live_row = _fetchone(conn, """
            SELECT COUNT(*) AS cnt
            FROM information_schema.tables
            WHERE table_schema = 'claude'
            AND table_type = 'BASE TABLE'
        """)
        live_count = live_row['cnt'] if live_row else 0

        # Count tables in schema_registry
        registry_row = _fetchone(conn, """
            SELECT COUNT(*) AS cnt FROM claude.schema_registry
        """)
        registry_count = registry_row['cnt'] if registry_row else 0

        # Tables in information_schema but NOT in registry (new tables)
        missing_rows = _fetchall(conn, """
            SELECT t.table_name
            FROM information_schema.tables t
            LEFT JOIN claude.schema_registry r ON r.table_name = t.table_name
            WHERE t.table_schema = 'claude'
            AND t.table_type = 'BASE TABLE'
            AND r.table_name IS NULL
        """)
        new_tables = len(missing_rows)
        new_table_names = [r['table_name'] for r in missing_rows]

        # Tables in registry with no content_hash (considered "changed" — never embedded)
        unhashed_row = _fetchone(conn, """
            SELECT COUNT(*) AS cnt FROM claude.schema_registry
            WHERE content_hash IS NULL OR embedding IS NULL
        """)
        changed_tables = unhashed_row['cnt'] if unhashed_row else 0

        stale = (new_tables + changed_tables) > 0

        details = []
        if new_table_names:
            details.append(f"New tables not in registry: {new_table_names}")
        if changed_tables > 0:
            details.append(f"{changed_tables} registry entries missing embedding or hash")

        logger.debug(
            f"Schema staleness: live={live_count} registry={registry_count} "
            f"new={new_tables} changed={changed_tables}"
        )
        return {
            'stale': stale,
            'new_tables': new_tables,
            'changed_tables': changed_tables,
            'details': details,
        }
    except Exception as e:
        logger.error(f"check_schema_staleness failed: {e}")
        return {'stale': False, 'new_tables': 0, 'changed_tables': 0,
                'details': [f"Error: {e}"], 'error': str(e)}


def check_vault_staleness(conn) -> dict:
    """Count vault_embeddings entries where embedding IS NULL.

    Also checks for .md files in knowledge-vault/ not in vault_embeddings at all.
    Fast: COUNT query + file glob + set comparison.

    Returns:
        {
            'stale': bool,
            'unembedded_count': int,
            'missing_files': list[str]
        }
    """
    try:
        # Count DB records with no embedding
        unembedded_row = _fetchone(conn, """
            SELECT COUNT(*) AS cnt FROM claude.vault_embeddings
            WHERE embedding IS NULL
        """)
        unembedded_count = unembedded_row['cnt'] if unembedded_row else 0

        # Get all doc_paths stored in the DB
        db_rows = _fetchall(conn, """
            SELECT DISTINCT doc_path FROM claude.vault_embeddings
        """)
        db_paths = {r['doc_path'] for r in db_rows}

        # Find .md files on disk not in the DB at all
        missing_files = []
        if VAULT_PATH.exists():
            md_files = list(VAULT_PATH.rglob("*.md"))
            for md_file in md_files:
                try:
                    rel_path = str(md_file.relative_to(VAULT_PATH))
                    # Normalize path separator to forward slash (how embed_vault_documents.py stores them)
                    rel_path = rel_path.replace("\\", "/")
                    if rel_path not in db_paths:
                        missing_files.append(rel_path)
                except ValueError:
                    pass

        stale = (unembedded_count > 0) or (len(missing_files) > 0)

        logger.debug(
            f"Vault staleness: unembedded={unembedded_count} "
            f"missing_files={len(missing_files)}"
        )
        return {
            'stale': stale,
            'unembedded_count': unembedded_count,
            'missing_files': missing_files[:20],  # Cap to avoid huge payloads
        }
    except Exception as e:
        logger.error(f"check_vault_staleness failed: {e}")
        return {'stale': False, 'unembedded_count': 0, 'missing_files': [],
                'error': str(e)}


def check_bpmn_staleness(conn) -> dict:
    """Compare .bpmn files on disk vs claude.bpmn_processes records.

    Detects .bpmn files not in the registry at all, or where the file has been
    modified more recently than the registry entry's updated_at timestamp.
    Fast: file mtime comparison + DB fetch — no file parsing.

    Returns:
        {
            'stale': bool,
            'unsynced_count': int,
            'unsynced_files': list[str]
        }
    """
    try:
        # Load all registered file paths + updated_at from DB
        db_rows = _fetchall(conn, """
            SELECT process_id, file_path, updated_at
            FROM claude.bpmn_processes
        """)
        # Normalise to forward slashes for consistent comparison
        db_by_path = {r['file_path'].replace("\\", "/"): r for r in db_rows}

        # Find all .bpmn files on disk
        bpmn_files = []
        if BPMN_PROCESSES_DIR.exists():
            bpmn_files = list(BPMN_PROCESSES_DIR.rglob("*.bpmn"))

        unsynced_files = []
        for bpmn_file in bpmn_files:
            # Build relative path the same way server_v2.py does (relative to cwd)
            try:
                rel_path = str(bpmn_file.relative_to(
                    Path(r'C:\Projects\claude-family')
                )).replace("\\", "/")
            except ValueError:
                rel_path = str(bpmn_file).replace("\\", "/")

            db_entry = db_by_path.get(rel_path)
            if db_entry is None:
                # Not in registry at all
                unsynced_files.append(rel_path)
            else:
                # Check modification time vs updated_at
                try:
                    mtime = datetime.fromtimestamp(bpmn_file.stat().st_mtime)
                    updated_at = db_entry.get('updated_at')
                    if updated_at and isinstance(updated_at, datetime):
                        if mtime > updated_at:
                            unsynced_files.append(rel_path)
                    elif updated_at is None:
                        unsynced_files.append(rel_path)
                except (OSError, TypeError):
                    pass  # Cannot stat — skip this check

        stale = len(unsynced_files) > 0

        logger.debug(
            f"BPMN staleness: disk_files={len(bpmn_files)} "
            f"unsynced={len(unsynced_files)}"
        )
        return {
            'stale': stale,
            'unsynced_count': len(unsynced_files),
            'unsynced_files': unsynced_files[:20],
        }
    except Exception as e:
        logger.error(f"check_bpmn_staleness failed: {e}")
        return {'stale': False, 'unsynced_count': 0, 'unsynced_files': [],
                'error': str(e)}


def check_memory_staleness(conn) -> dict:
    """Count knowledge entries where tier='mid' AND embedding IS NULL.

    Fast: single COUNT query.

    Returns:
        {
            'stale': bool,
            'unembedded_count': int
        }
    """
    try:
        row = _fetchone(conn, """
            SELECT COUNT(*) AS cnt
            FROM claude.knowledge
            WHERE tier = 'mid'
            AND embedding IS NULL
        """)
        unembedded_count = row['cnt'] if row else 0
        stale = unembedded_count > 0

        logger.debug(f"Memory staleness: mid_unembedded={unembedded_count}")
        return {
            'stale': stale,
            'unembedded_count': unembedded_count,
        }
    except Exception as e:
        logger.error(f"check_memory_staleness failed: {e}")
        return {'stale': False, 'unembedded_count': 0, 'error': str(e)}


def check_column_registry_staleness(conn) -> dict:
    """Query pg_catalog for CHECK constraints with ARRAY values.

    Compares against claude.column_registry entries. A column is "missing" if
    it has a CHECK ARRAY constraint but is not in column_registry.
    Fast: pg_catalog query only — no file I/O.

    Returns:
        {
            'stale': bool,
            'missing_count': int,
            'missing_columns': list[str]
        }
    """
    try:
        # Get all constrained columns from information_schema
        constrained_rows = _fetchall(conn, """
            SELECT
                tc.table_name,
                kcu.column_name,
                cc.check_clause
            FROM information_schema.table_constraints tc
            JOIN information_schema.check_constraints cc
                ON tc.constraint_name = cc.constraint_name
                AND tc.constraint_schema = cc.constraint_schema
            JOIN information_schema.constraint_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.constraint_schema = kcu.constraint_schema
            WHERE tc.table_schema = 'claude'
            AND tc.constraint_type = 'CHECK'
            AND cc.check_clause LIKE '%%ARRAY[%%'
            ORDER BY tc.table_name, kcu.column_name
        """)

        # Build set of (table, column) pairs that have ARRAY constraints
        constrained = {
            (r['table_name'], r['column_name'])
            for r in constrained_rows
        }

        # Get all columns already in column_registry
        registry_rows = _fetchall(conn, """
            SELECT table_name, column_name FROM claude.column_registry
        """)
        registered = {(r['table_name'], r['column_name']) for r in registry_rows}

        # Find constrained columns NOT in registry
        missing = constrained - registered
        missing_columns = [f"{t}.{c}" for t, c in sorted(missing)]

        stale = len(missing_columns) > 0

        logger.debug(
            f"Column registry staleness: constrained={len(constrained)} "
            f"registered={len(registered)} missing={len(missing_columns)}"
        )
        return {
            'stale': stale,
            'missing_count': len(missing_columns),
            'missing_columns': missing_columns,
        }
    except Exception as e:
        logger.error(f"check_column_registry_staleness failed: {e}")
        return {'stale': False, 'missing_count': 0, 'missing_columns': [],
                'error': str(e)}


# ============================================================================
# AGGREGATED DETECTION
# ============================================================================

def detect_all_staleness(conn=None) -> dict:
    """Run all 5 staleness checks and return an aggregated result.

    Creates its own connection if none provided. Each check is independent —
    a failure in one does not prevent the others from running.

    Returns:
        {
            'any_stale': bool,
            'schema': {check result},
            'vault': {check result},
            'bpmn': {check result},
            'memory': {check result},
            'column_registry': {check result},
            'summary': str
        }
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    if conn is None:
        return {
            'any_stale': False,
            'schema': {'stale': False, 'error': 'No database connection'},
            'vault': {'stale': False, 'error': 'No database connection'},
            'bpmn': {'stale': False, 'error': 'No database connection'},
            'memory': {'stale': False, 'error': 'No database connection'},
            'column_registry': {'stale': False, 'error': 'No database connection'},
            'summary': 'Detection skipped — no database connection',
        }

    try:
        logger.info("Running staleness detection across all 5 subsystems...")

        schema_result = check_schema_staleness(conn)
        vault_result = check_vault_staleness(conn)
        bpmn_result = check_bpmn_staleness(conn)
        memory_result = check_memory_staleness(conn)
        column_result = check_column_registry_staleness(conn)

        any_stale = any([
            schema_result.get('stale', False),
            vault_result.get('stale', False),
            bpmn_result.get('stale', False),
            memory_result.get('stale', False),
            column_result.get('stale', False),
        ])

        # Build human-readable summary
        stale_systems = []
        if schema_result.get('stale'):
            stale_systems.append(
                f"schema({schema_result.get('new_tables', 0)} new, "
                f"{schema_result.get('changed_tables', 0)} changed)"
            )
        if vault_result.get('stale'):
            stale_systems.append(
                f"vault({vault_result.get('unembedded_count', 0)} unembedded, "
                f"{len(vault_result.get('missing_files', []))} missing)"
            )
        if bpmn_result.get('stale'):
            stale_systems.append(
                f"bpmn({bpmn_result.get('unsynced_count', 0)} unsynced)"
            )
        if memory_result.get('stale'):
            stale_systems.append(
                f"memory({memory_result.get('unembedded_count', 0)} mid unembedded)"
            )
        if column_result.get('stale'):
            stale_systems.append(
                f"column_registry({column_result.get('missing_count', 0)} missing)"
            )

        summary = (
            f"Stale: {', '.join(stale_systems)}" if stale_systems
            else "All systems current"
        )

        logger.info(f"Detection complete: {summary}")

        return {
            'any_stale': any_stale,
            'schema': schema_result,
            'vault': vault_result,
            'bpmn': bpmn_result,
            'memory': memory_result,
            'column_registry': column_result,
            'summary': summary,
        }
    finally:
        if close_conn and conn:
            try:
                conn.close()
            except Exception:
                pass


# ============================================================================
# REPAIR FUNCTIONS
# ============================================================================

def repair_schema(conn=None) -> dict:
    """Run schema_docs.py --all then embed_schema.py via subprocess.

    schema_docs.py --all: generates COMMENT ON statements, applies them,
    syncs schema_registry and column_registry.
    embed_schema.py: generates Voyage AI embeddings for changed tables.

    Returns:
        {
            'success': bool,
            'schema_docs_output': str,
            'embed_output': str
        }
    """
    schema_docs_script = str(SCRIPTS_DIR / 'schema_docs.py')
    embed_schema_script = str(SCRIPTS_DIR / 'embed_schema.py')

    logger.info("Repairing schema: running schema_docs.py --all ...")
    schema_docs_output = ""
    embed_output = ""
    schema_docs_success = False
    embed_success = False

    try:
        result = subprocess.run(
            [sys.executable, schema_docs_script, '--all'],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(SCRIPTS_DIR),
        )
        schema_docs_output = (result.stdout + result.stderr).strip()
        schema_docs_success = result.returncode == 0
        if not schema_docs_success:
            logger.error(f"schema_docs.py --all failed (rc={result.returncode})")
        else:
            logger.info("schema_docs.py --all completed")
    except subprocess.TimeoutExpired:
        schema_docs_output = "Timeout after 300s"
        logger.error("schema_docs.py --all timed out")
    except Exception as e:
        schema_docs_output = f"Error: {e}"
        logger.error(f"schema_docs.py --all error: {e}")

    logger.info("Repairing schema: running embed_schema.py ...")
    try:
        result = subprocess.run(
            [sys.executable, embed_schema_script],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(SCRIPTS_DIR),
        )
        embed_output = (result.stdout + result.stderr).strip()
        embed_success = result.returncode == 0
        if not embed_success:
            logger.error(f"embed_schema.py failed (rc={result.returncode})")
        else:
            logger.info("embed_schema.py completed")
    except subprocess.TimeoutExpired:
        embed_output = "Timeout after 300s"
        logger.error("embed_schema.py timed out")
    except Exception as e:
        embed_output = f"Error: {e}"
        logger.error(f"embed_schema.py error: {e}")

    return {
        'success': schema_docs_success and embed_success,
        'schema_docs_output': schema_docs_output,
        'embed_output': embed_output,
    }


def repair_vault(conn=None) -> dict:
    """Run embed_vault_documents.py (incremental) via subprocess.

    Incremental mode: only processes files whose hash has changed.

    Returns:
        {
            'success': bool,
            'output': str,
            'files_embedded': int
        }
    """
    embed_vault_script = str(SCRIPTS_DIR / 'embed_vault_documents.py')

    logger.info("Repairing vault: running embed_vault_documents.py ...")
    try:
        result = subprocess.run(
            [sys.executable, embed_vault_script],
            capture_output=True,
            text=True,
            timeout=900,  # 15 min — vault with many new files is slow (Voyage AI per chunk)
            cwd=str(SCRIPTS_DIR),
        )
        output = (result.stdout + result.stderr).strip()
        # Truncate output for return value (can be very large)
        output_truncated = output[-3000:] if len(output) > 3000 else output
        success = result.returncode == 0

        if not success:
            logger.error(f"embed_vault_documents.py failed (rc={result.returncode})")
        else:
            logger.info("embed_vault_documents.py completed")

        # Try to extract file count from output
        files_embedded = 0
        for line in output.splitlines():
            if 'Embedded' in line or 'new chunks' in line:
                import re
                nums = re.findall(r'\d+', line)
                if nums:
                    files_embedded = int(nums[0])
                    break

        return {
            'success': success,
            'output': output_truncated,
            'files_embedded': files_embedded,
        }
    except subprocess.TimeoutExpired:
        logger.error("embed_vault_documents.py timed out after 900s")
        return {'success': False, 'output': 'Timeout after 600s', 'files_embedded': 0}
    except Exception as e:
        logger.error(f"embed_vault_documents.py error: {e}")
        return {'success': False, 'output': f'Error: {e}', 'files_embedded': 0}


def repair_bpmn(project: str = 'claude-family') -> dict:
    """Sync BPMN processes to the registry by parsing .bpmn files directly.

    Walks the processes directory, parses each .bpmn file, and upserts into
    claude.bpmn_processes. Uses file hash for incremental sync.
    Mirrors the logic from sync_bpmn_processes in server_v2.py but runs
    inline (no MCP dependency).

    Returns:
        {
            'success': bool,
            'synced_count': int,
            'output': str
        }
    """
    logger.info(f"Repairing BPMN registry for project: {project}")
    output_lines = []
    synced_count = 0
    parse_errors = 0
    skipped_count = 0

    try:
        conn = get_db_connection()
        if conn is None:
            return {'success': False, 'synced_count': 0,
                    'output': 'No database connection'}

        bpmn_files = list(BPMN_PROCESSES_DIR.rglob("*.bpmn")) if BPMN_PROCESSES_DIR.exists() else []
        if not bpmn_files:
            msg = f"No .bpmn files found in {BPMN_PROCESSES_DIR}"
            logger.warning(msg)
            conn.close()
            return {'success': True, 'synced_count': 0, 'output': msg}

        output_lines.append(f"Found {len(bpmn_files)} .bpmn files")

        # Load existing hashes for incremental sync
        existing_rows = _fetchall(conn, """
            SELECT process_id, file_hash FROM claude.bpmn_processes
            WHERE project_name = %s
        """, (project,))
        existing_hashes = {r['process_id']: r['file_hash'] for r in existing_rows}

        project_root = Path(r'C:\Projects\claude-family')

        for bpmn_file in bpmn_files:
            # Compute file hash
            try:
                file_hash = _sha256_file(bpmn_file)
            except OSError as e:
                output_lines.append(f"Cannot read {bpmn_file.name}: {e}")
                parse_errors += 1
                continue

            # Parse BPMN metadata
            parsed = _parse_bpmn_file(str(bpmn_file))
            if parsed is None:
                output_lines.append(f"Parse error: {bpmn_file.name}")
                parse_errors += 1
                continue

            pid = parsed['process_id']

            # Skip if hash unchanged
            if existing_hashes.get(pid) == file_hash:
                skipped_count += 1
                continue

            # Build relative path for portability
            try:
                rel_path = str(bpmn_file.relative_to(project_root)).replace("\\", "/")
            except ValueError:
                rel_path = str(bpmn_file).replace("\\", "/")

            # Generate embedding for search
            embed_text = f"{parsed['process_name']} {parsed['description']}"
            embedding = _generate_embedding(embed_text)

            # Upsert into registry
            try:
                _execute(conn, """
                    INSERT INTO claude.bpmn_processes
                        (process_id, project_name, file_path, process_name, level, category,
                         description, elements, flows, file_hash, embedding, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (process_id) DO UPDATE SET
                        project_name = EXCLUDED.project_name,
                        file_path = EXCLUDED.file_path,
                        process_name = EXCLUDED.process_name,
                        level = EXCLUDED.level,
                        category = EXCLUDED.category,
                        description = EXCLUDED.description,
                        elements = EXCLUDED.elements,
                        flows = EXCLUDED.flows,
                        file_hash = EXCLUDED.file_hash,
                        embedding = EXCLUDED.embedding,
                        updated_at = NOW()
                """, (
                    pid, project, rel_path, parsed['process_name'],
                    parsed['level'], parsed['category'], parsed['description'],
                    json.dumps(parsed['elements']), json.dumps(parsed['flows']),
                    file_hash,
                    str(embedding) if embedding else None,
                ))
                action = "updated" if pid in existing_hashes else "created"
                output_lines.append(f"{action}: {pid}")
                synced_count += 1
            except Exception as e:
                output_lines.append(f"DB error for {pid}: {e}")
                conn.rollback()
                parse_errors += 1
                continue

        conn.commit()
        conn.close()

        output_lines.append(
            f"Complete: synced={synced_count} skipped={skipped_count} errors={parse_errors}"
        )
        logger.info(f"BPMN repair complete: synced={synced_count}")

        return {
            'success': parse_errors == 0,
            'synced_count': synced_count,
            'output': '\n'.join(output_lines),
        }

    except Exception as e:
        logger.error(f"repair_bpmn failed: {e}")
        return {'success': False, 'synced_count': 0, 'output': f'Error: {e}'}


def repair_memory(conn=None) -> dict:
    """Find mid-tier knowledge entries without embeddings, generate and store them.

    Uses the embedding_provider abstraction (FastEmbed local or Voyage AI).

    Returns:
        {
            'success': bool,
            'embedded_count': int
        }
    """
    logger.info("Repairing memory: embedding mid-tier knowledge entries...")

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    if conn is None:
        return {'success': False, 'embedded_count': 0, 'error': 'No database connection'}

    embedded_count = 0
    errors = 0

    try:
        # Fetch mid-tier entries with no embedding
        # knowledge table PK is knowledge_id (not id)
        # Columns: knowledge_id, title, description, knowledge_type, knowledge_category
        rows = _fetchall(conn, """
            SELECT knowledge_id, title, description, knowledge_type, knowledge_category
            FROM claude.knowledge
            WHERE tier = 'mid'
            AND embedding IS NULL
            ORDER BY created_at DESC
        """)

        if not rows:
            logger.info("No mid-tier knowledge entries need embedding")
            return {'success': True, 'embedded_count': 0}

        logger.info(f"Found {len(rows)} mid-tier entries to embed")

        for row in rows:
            try:
                # Build embeddable text
                parts = []
                if row.get('title'):
                    parts.append(f"# {row['title']}")
                if row.get('knowledge_type'):
                    parts.append(f"Type: {row['knowledge_type']}")
                if row.get('knowledge_category'):
                    parts.append(f"Category: {row['knowledge_category']}")
                if row.get('description'):
                    parts.append(row['description'])
                embed_text = '\n\n'.join(parts) if parts else str(row.get('title', 'unknown'))

                embedding = _generate_embedding(embed_text)
                if embedding is None:
                    errors += 1
                    continue

                # Store embedding
                _execute(conn, """
                    UPDATE claude.knowledge
                    SET embedding = %s::vector
                    WHERE knowledge_id = %s
                """, (str(embedding), row['knowledge_id']))
                conn.commit()
                embedded_count += 1

            except Exception as e:
                logger.error(f"Failed to embed knowledge entry {row.get('knowledge_id')}: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                errors += 1
                continue

        logger.info(f"Memory repair complete: embedded={embedded_count} errors={errors}")
        return {
            'success': errors == 0,
            'embedded_count': embedded_count,
        }

    except Exception as e:
        logger.error(f"repair_memory failed: {e}")
        return {'success': False, 'embedded_count': 0, 'error': str(e)}
    finally:
        if close_conn and conn:
            try:
                conn.close()
            except Exception:
                pass


def repair_column_registry(conn=None) -> dict:
    """Run schema_docs.py --sync-column-registry via subprocess.

    Extracts valid values from CHECK constraints and upserts into
    claude.column_registry.valid_values (JSONB).

    Returns:
        {
            'success': bool,
            'output': str
        }
    """
    schema_docs_script = str(SCRIPTS_DIR / 'schema_docs.py')

    logger.info("Repairing column registry: running schema_docs.py --sync-column-registry ...")
    try:
        result = subprocess.run(
            [sys.executable, schema_docs_script, '--sync-column-registry'],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(SCRIPTS_DIR),
        )
        output = (result.stdout + result.stderr).strip()
        success = result.returncode == 0

        if not success:
            logger.error(f"schema_docs.py --sync-column-registry failed (rc={result.returncode})")
        else:
            logger.info("Column registry sync complete")

        return {'success': success, 'output': output}

    except subprocess.TimeoutExpired:
        logger.error("schema_docs.py --sync-column-registry timed out")
        return {'success': False, 'output': 'Timeout after 120s'}
    except Exception as e:
        logger.error(f"repair_column_registry error: {e}")
        return {'success': False, 'output': f'Error: {e}'}


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def run_maintenance(scope: str = 'full', auto_repair: bool = True) -> dict:
    """Full maintenance pipeline following the BPMN model.

    Phase 1: Detect staleness across specified subsystems (always runs).
    Phase 2: If auto_repair=True and any_stale, run repairs for stale systems.
    Phase 3: Compile and return a summary report.

    Args:
        scope: Which subsystems to check/repair.
            'full'            — all 5 subsystems
            'detect_only'     — all 5 subsystems, no repair regardless of auto_repair
            'schema'          — schema registry only
            'vault'           — vault embeddings only
            'bpmn'            — BPMN registry only
            'memory'          — memory embeddings only
            'column_registry' — column registry only
        auto_repair: If True, repair stale subsystems after detection.
                     If False (or scope='detect_only'), detect only.

    Returns:
        {
            'detection': {aggregated detection results},
            'repairs': {per-subsystem repair results, or {} if detect_only},
            'summary': str,
            'any_stale': bool,
            'any_repaired': bool,
        }
    """
    started_at = datetime.now(timezone.utc).isoformat()
    detect_only = (scope == 'detect_only') or (not auto_repair)

    # Determine which subsystems are in scope
    all_scopes = {'schema', 'vault', 'bpmn', 'memory', 'column_registry'}
    if scope in ('full', 'detect_only'):
        active_scopes = all_scopes
    elif scope in all_scopes:
        active_scopes = {scope}
    else:
        logger.warning(f"Unknown scope '{scope}', defaulting to 'full'")
        active_scopes = all_scopes

    logger.info(
        f"System maintenance: scope={scope} auto_repair={auto_repair} "
        f"detect_only={detect_only} subsystems={sorted(active_scopes)}"
    )

    # -----------------------------------------------------------------------
    # Phase 1: Detection
    # -----------------------------------------------------------------------
    conn = get_db_connection()
    detection = {}

    if conn is None:
        logger.error("Cannot connect to database — aborting maintenance")
        return {
            'detection': {'any_stale': False, 'summary': 'No database connection',
                          'error': 'No database connection'},
            'repairs': {},
            'summary': 'Maintenance aborted — no database connection',
            'any_stale': False,
            'any_repaired': False,
            'started_at': started_at,
        }

    try:
        if 'schema' in active_scopes:
            detection['schema'] = check_schema_staleness(conn)
        if 'vault' in active_scopes:
            detection['vault'] = check_vault_staleness(conn)
        if 'bpmn' in active_scopes:
            detection['bpmn'] = check_bpmn_staleness(conn)
        if 'memory' in active_scopes:
            detection['memory'] = check_memory_staleness(conn)
        if 'column_registry' in active_scopes:
            detection['column_registry'] = check_column_registry_staleness(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    any_stale = any(v.get('stale', False) for v in detection.values())

    # Build detection summary
    stale_items = [k for k, v in detection.items() if v.get('stale')]
    detection['any_stale'] = any_stale
    detection['summary'] = (
        f"Stale: {', '.join(stale_items)}" if stale_items else "All checked systems current"
    )

    # -----------------------------------------------------------------------
    # Phase 2: Repair (conditional)
    # -----------------------------------------------------------------------
    repairs: dict = {}
    any_repaired = False

    if detect_only or not any_stale:
        if not any_stale:
            logger.info("Nothing stale — skipping repair phase")
        else:
            logger.info("Detect-only mode — skipping repair phase")
    else:
        logger.info("Starting repair phase for stale subsystems...")

        if 'schema' in active_scopes and detection.get('schema', {}).get('stale'):
            logger.info("Repairing: schema")
            try:
                repairs['schema'] = repair_schema()
                if repairs['schema'].get('success'):
                    any_repaired = True
            except Exception as e:
                repairs['schema'] = {'success': False, 'error': str(e)}

        if 'vault' in active_scopes and detection.get('vault', {}).get('stale'):
            logger.info("Repairing: vault")
            try:
                repairs['vault'] = repair_vault()
                if repairs['vault'].get('success'):
                    any_repaired = True
            except Exception as e:
                repairs['vault'] = {'success': False, 'error': str(e)}

        if 'bpmn' in active_scopes and detection.get('bpmn', {}).get('stale'):
            logger.info("Repairing: bpmn")
            try:
                repairs['bpmn'] = repair_bpmn()
                if repairs['bpmn'].get('success'):
                    any_repaired = True
            except Exception as e:
                repairs['bpmn'] = {'success': False, 'error': str(e)}

        if 'memory' in active_scopes and detection.get('memory', {}).get('stale'):
            logger.info("Repairing: memory")
            try:
                repairs['memory'] = repair_memory()
                if repairs['memory'].get('success'):
                    any_repaired = True
            except Exception as e:
                repairs['memory'] = {'success': False, 'error': str(e)}

        if 'column_registry' in active_scopes and detection.get('column_registry', {}).get('stale'):
            logger.info("Repairing: column_registry")
            try:
                repairs['column_registry'] = repair_column_registry()
                if repairs['column_registry'].get('success'):
                    any_repaired = True
            except Exception as e:
                repairs['column_registry'] = {'success': False, 'error': str(e)}

    # -----------------------------------------------------------------------
    # Phase 3: Summary
    # -----------------------------------------------------------------------
    repair_parts = []
    for subsystem, result in repairs.items():
        status = "repaired" if result.get('success') else "failed"
        repair_parts.append(f"{subsystem}={status}")

    if stale_items and detect_only:
        action_summary = f"Detected stale: {', '.join(stale_items)} (repair skipped)"
    elif stale_items and repair_parts:
        action_summary = f"Detected stale: {', '.join(stale_items)} | Repairs: {', '.join(repair_parts)}"
    elif stale_items:
        action_summary = f"Detected stale: {', '.join(stale_items)} | No repairs run"
    else:
        action_summary = "All systems current — no action required"

    logger.info(f"Maintenance complete: {action_summary}")

    return {
        'detection': detection,
        'repairs': repairs,
        'summary': action_summary,
        'any_stale': any_stale,
        'any_repaired': any_repaired,
        'started_at': started_at,
        'completed_at': datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='System Maintenance Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scopes:
  full              All 5 subsystems (detect + optional repair)
  detect_only       All 5 subsystems, detection only (ignores --repair)
  schema            Schema registry only
  vault             Vault embeddings only
  bpmn              BPMN process registry only
  memory            Memory (knowledge tier=mid) embeddings only
  column_registry   Column registry from CHECK constraints only

Examples:
  python system_maintenance.py
  python system_maintenance.py --scope detect_only
  python system_maintenance.py --scope full --repair
  python system_maintenance.py --scope schema --repair
  python system_maintenance.py --scope bpmn --repair
        """
    )
    parser.add_argument(
        '--scope',
        default='detect_only',
        choices=['full', 'detect_only', 'schema', 'vault', 'bpmn', 'memory', 'column_registry'],
        help='Subsystems to check (default: detect_only)',
    )
    parser.add_argument(
        '--repair',
        action='store_true',
        help='Enable auto-repair of stale subsystems',
    )
    args = parser.parse_args()

    result = run_maintenance(scope=args.scope, auto_repair=args.repair)
    print(json.dumps(result, indent=2, default=str))
