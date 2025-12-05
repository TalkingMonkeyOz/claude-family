#!/usr/bin/env python3
"""
Document Scanner - Indexes project documentation to PostgreSQL

Scans project directories for documentation files and indexes them
in the claude.documents table for the MCW documents view.

Features:
- Automatic document type detection from filename patterns
- Project linking via document_projects junction table
- Core document detection (CLAUDE.md, shared docs, session commands)
- Change detection via SHA256 hash

Usage:
    python scan_documents.py                    # Scan all projects
    python scan_documents.py --project mcw      # Scan specific project
    python scan_documents.py --dry-run          # Preview without writing
    python scan_documents.py --link-only        # Just update project links
"""

import os
import sys
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

# Database imports
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        PSYCOPG_VERSION = 2
    except ImportError:
        print("ERROR: psycopg not installed")
        sys.exit(1)


# Configuration
PROJECT_ROOT = Path("C:/Projects")
SHARED_DOCS = Path("C:/claude/shared/docs")
COMMANDS_PATH = Path("C:/Projects/claude-family/.claude/commands")

# Core document patterns (these appear in ALL projects)
CORE_DOC_PATTERNS = [
    ('claude.md', 'Claude configuration - applies to all sessions'),
    ('/shared/docs/', 'Shared documentation for all projects'),
    ('/commands/session-', 'Session commands used by all instances'),
    ('/.claude/commands/', 'Claude slash commands'),
]

# Document type detection patterns (order matters - first match wins)
DOC_TYPE_PATTERNS = {
    'ADR': ['adr-', 'adr_', '/adr/'],
    'ARCHITECTURE': ['architecture', 'arch_', 'system_design', 'design_spec', 'layer', 'structure', 'service', 'module', 'controller'],
    'CLAUDE_CONFIG': ['claude.md'],
    'README': ['readme', 'welcome', 'intro'],
    'SOP': ['sop', 'procedure', 'workflow', 'protocol', 'enforcement', 'guardian', 'coordinat', 'parallel', 'methodology'],
    'GUIDE': ['guide', 'how-to', 'howto', 'tutorial', 'quick_start', 'quickstart', 'getting_started', 'checklist', 'start_here', 'start here', 'integration', 'setup', 'install', 'deploy', 'build'],
    'API': ['api', 'swagger', 'openapi', 'endpoint'],
    'SPEC': ['spec', 'requirement', 'prd', 'plan', 'strategy', 'phase', 'priorit', 'analysis', 'project', 'feature', 'business', 'compliance'],
    'SESSION_NOTE': ['session_note', 'session-note', 'startup_context', 'daily_note', 'daily-note', 'context', 'session', 'commit', 'log', 'change'],
    'MIGRATION': ['migration', 'upgrade'],
    'TROUBLESHOOTING': ['troubleshoot', 'debug', 'fix', '_fix_', 'investigation', 'audit', 'security', 'solved', 'reality_check', 'reality check'],
    'COMPLETION_REPORT': ['completion', 'complete', 'summary', 'report', 'status', 'delivery', 'cleanup', 'implementation'],
    'REFERENCE': ['reference', 'cheat_sheet', 'cheatsheet', 'index', 'overview', 'manifest', 'register', 'config', 'mcp', 'command', 'agent', 'nimbus', 'tax', 'database', 'db', 'document', 'comparison', 'update', 'identity', 'supporting', 'usage', 'example'],
    'TEST_DOC': ['test'],
    'ARCHIVE': ['deprecated', '_archive', '/archive/', 'egg-info', '/obj/', '/bin/debug'],
}

# Category mappings
DOC_CATEGORIES = {
    'ARCHITECTURE': 'architecture',
    'CLAUDE_CONFIG': 'claude_config',
    'README': 'readme',
    'SOP': 'sop',
    'GUIDE': 'guide',
    'API': 'api',
    'SPEC': 'spec',
    'SESSION_NOTE': 'session_note',
    'ADR': 'adr',
    'MIGRATION': 'migration',
    'TROUBLESHOOTING': 'troubleshooting',
    'COMPLETION_REPORT': 'completion_report',
    'REFERENCE': 'reference',
    'TEST_DOC': 'test',
    'ARCHIVE': 'archive',
}


def get_db_connection():
    """Get PostgreSQL connection."""
    conn_str = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation'
    if PSYCOPG_VERSION == 3:
        return psycopg.connect(conn_str, row_factory=dict_row)
    else:
        return psycopg.connect(conn_str, cursor_factory=RealDictCursor)


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file contents."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def detect_doc_type(filename: str) -> str:
    """Detect document type from filename."""
    filename_lower = filename.lower()

    for doc_type, patterns in DOC_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in filename_lower:
                return doc_type

    return 'OTHER'


def extract_title(file_path: Path) -> str:
    """Extract title from markdown file (first # heading or filename)."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('# '):
                    # Strip emojis and other non-ASCII for Windows console safety
                    title = line[2:].strip()
                    return ''.join(c for c in title if ord(c) < 128 or c.isalnum())
                # Skip frontmatter
                if line == '---':
                    continue
    except:
        pass

    # Fallback to filename
    return file_path.stem.replace('_', ' ').replace('-', ' ').title()


def get_project_id(conn, project_name: str):
    """Get project_id from projects table."""
    cur = conn.cursor()
    cur.execute("""
        SELECT project_id FROM claude.projects
        WHERE project_name = %s OR project_name ILIKE %s
        LIMIT 1
    """, (project_name, f'%{project_name}%'))
    row = cur.fetchone()
    cur.close()
    return row['project_id'] if row else None


def detect_core_document(file_path: str) -> tuple:
    """Check if document is a core document that applies to all projects."""
    file_path_lower = file_path.lower().replace('\\', '/')

    for pattern, reason in CORE_DOC_PATTERNS:
        if pattern in file_path_lower:
            return True, reason

    return False, None


def detect_project_from_path(file_path: str) -> str:
    """Extract project name from file path."""
    # Normalize path
    path_parts = Path(file_path).parts

    # Look for Projects folder and get next part
    for i, part in enumerate(path_parts):
        if part.lower() == 'projects' and i + 1 < len(path_parts):
            return path_parts[i + 1]

    # Check for shared docs
    if 'shared' in file_path.lower() and 'docs' in file_path.lower():
        return 'shared'

    return 'unknown'


def link_document_to_project(conn, doc_id, project_id, is_primary: bool = True, linked_by: str = 'scanner'):
    """Create link between document and project in junction table."""
    if not project_id:
        return False

    cur = conn.cursor()

    # Check if link already exists
    cur.execute("""
        SELECT document_project_id FROM claude.document_projects
        WHERE doc_id = %s AND project_id = %s
    """, (doc_id, project_id))

    if not cur.fetchone():
        cur.execute("""
            INSERT INTO claude.document_projects (doc_id, project_id, is_primary, linked_by)
            VALUES (%s, %s, %s, %s)
        """, (doc_id, project_id, is_primary, linked_by))
        cur.close()
        return True

    cur.close()
    return False


def scan_directory(directory: Path, project_name: str = None) -> list:
    """Scan directory for documentation files."""
    docs = []

    # Patterns to scan
    patterns = ['*.md', '*.txt', '*.rst']

    for pattern in patterns:
        for file_path in directory.rglob(pattern):
            # Skip node_modules, .git, etc.
            if any(skip in str(file_path) for skip in ['node_modules', '.git', '__pycache__', 'venv', '.next']):
                continue

            # Skip very small files (likely empty or stubs)
            if file_path.stat().st_size < 50:
                continue

            doc_type = detect_doc_type(file_path.name)
            title = extract_title(file_path)
            file_hash = calculate_file_hash(file_path)

            # Detect if this is a core document
            is_core, core_reason = detect_core_document(str(file_path))

            # Auto-detect project from path if not provided
            detected_project = project_name or detect_project_from_path(str(file_path))

            docs.append({
                'file_path': str(file_path),
                'doc_title': title,
                'doc_type': doc_type,
                'category': DOC_CATEGORIES.get(doc_type, 'other'),
                'file_hash': file_hash,
                'project_name': detected_project,
                'is_core': is_core,
                'core_reason': core_reason,
            })

    return docs


def safe_print(msg: str):
    """Print with ASCII fallback for Windows console."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def detect_document_status(file_path: str, doc_type: str) -> str:
    """Detect appropriate status based on file path and type."""
    file_path_lower = file_path.lower()

    # Deprecated files
    if 'deprecated' in file_path_lower:
        return 'DEPRECATED'

    # Archived files
    if '/archive/' in file_path_lower or '\\archive\\' in file_path_lower:
        return 'ARCHIVED'

    # Archive type docs (from DOC_TYPE_PATTERNS)
    if doc_type == 'ARCHIVE':
        return 'ARCHIVED'

    return 'ACTIVE'


def upsert_document(conn, doc: dict, project_id = None, dry_run: bool = False):
    """Insert or update document in database."""
    is_core = doc.get('is_core', False)
    core_reason = doc.get('core_reason')
    core_label = " [CORE]" if is_core else ""

    # Detect status from file path/type
    doc_status = detect_document_status(doc['file_path'], doc['doc_type'])

    if dry_run:
        safe_print(f"  [DRY-RUN] Would upsert: {doc['doc_title']} ({doc['doc_type']}){core_label}")
        return None

    cur = conn.cursor()

    # Check if exists by file_path
    cur.execute("""
        SELECT doc_id, file_hash FROM claude.documents
        WHERE file_path = %s
    """, (doc['file_path'],))
    existing = cur.fetchone()

    doc_id = None

    if existing:
        doc_id = existing['doc_id']
        # Update if hash changed or core status changed
        if existing['file_hash'] != doc['file_hash']:
            cur.execute("""
                UPDATE claude.documents SET
                    doc_title = %s,
                    doc_type = %s,
                    category = %s,
                    file_hash = %s,
                    status = %s,
                    is_core = %s,
                    core_reason = %s,
                    updated_at = NOW()
                WHERE doc_id = %s
            """, (doc['doc_title'], doc['doc_type'], doc['category'],
                  doc['file_hash'], doc_status, is_core, core_reason, doc_id))
            safe_print(f"  [UPDATED] {doc['doc_title']} ({doc_status}){core_label}")
        else:
            # Still update core status if needed
            cur.execute("""
                UPDATE claude.documents SET
                    is_core = %s,
                    core_reason = %s
                WHERE doc_id = %s AND (is_core IS DISTINCT FROM %s OR core_reason IS DISTINCT FROM %s)
            """, (is_core, core_reason, doc_id, is_core, core_reason))
            safe_print(f"  [UNCHANGED] {doc['doc_title']}{core_label}")
    else:
        # Insert new with detected status
        cur.execute("""
            INSERT INTO claude.documents
            (doc_title, doc_type, file_path, file_hash, category, project_id, status, version, is_core, core_reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s, '1.0', %s, %s)
            RETURNING doc_id
        """, (doc['doc_title'], doc['doc_type'], doc['file_path'],
              doc['file_hash'], doc['category'], project_id, doc_status, is_core, core_reason))
        result = cur.fetchone()
        doc_id = result['doc_id'] if isinstance(result, dict) else result[0]
        safe_print(f"  [NEW] {doc['doc_title']}{core_label}")

    cur.close()
    return doc_id


def main():
    parser = argparse.ArgumentParser(description='Scan and index documentation files')
    parser.add_argument('--project', '-p', help='Specific project to scan')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Preview without writing')
    parser.add_argument('--link-only', '-l', action='store_true', help='Only update project links')
    args = parser.parse_args()

    print("=" * 60)
    print("Document Scanner - Indexing project documentation")
    if args.link_only:
        print("(Link-only mode)")
    print("=" * 60)

    conn = get_db_connection()

    # Determine what to scan
    if args.project:
        project_dir = PROJECT_ROOT / args.project
        if not project_dir.exists():
            print(f"ERROR: Project directory not found: {project_dir}")
            sys.exit(1)
        projects = [(args.project, project_dir)]
    else:
        # Scan all projects
        projects = []
        for d in PROJECT_ROOT.iterdir():
            if d.is_dir() and not d.name.startswith('.'):
                projects.append((d.name, d))

        # Also scan shared docs
        if SHARED_DOCS.exists():
            projects.append(('shared', SHARED_DOCS))

    total_docs = 0
    total_links = 0

    for project_name, project_dir in projects:
        print(f"\nScanning: {project_name}")
        print("-" * 40)

        project_id = get_project_id(conn, project_name)
        docs = scan_directory(project_dir, project_name)

        print(f"Found {len(docs)} documents")

        for doc in docs:
            doc_id = upsert_document(conn, doc, project_id, args.dry_run)

            # Link document to project
            if doc_id and project_id and not args.dry_run:
                if link_document_to_project(conn, doc_id, project_id, is_primary=True, linked_by='scanner'):
                    total_links += 1

        total_docs += len(docs)

    if not args.dry_run:
        conn.commit()

    conn.close()

    print("\n" + "=" * 60)
    print(f"Total documents indexed: {total_docs}")
    print(f"Total project links created: {total_links}")
    print("=" * 60)


if __name__ == "__main__":
    main()
