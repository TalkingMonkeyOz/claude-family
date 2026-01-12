#!/usr/bin/env python3
"""
Session Startup Hook Script for claude-family-core plugin.

This is called automatically via SessionStart hook.
- Syncs configuration from database (generates .claude/settings.local.json)
- Creates a new session record in claude.sessions (auto-logging)
- Checks for saved session state (todo list, focus)
- Checks for pending messages
- Outputs JSON for Claude Code to consume
"""

import json
import os
import sys
import uuid
import logging
import time
from datetime import datetime
from pathlib import Path

# Import config generator for database-driven settings
# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from generate_project_settings import sync_project_config
    CONFIG_SYNC_AVAILABLE = True
except ImportError:
    CONFIG_SYNC_AVAILABLE = False

try:
    from log_rotation import rotate_logs
    LOG_ROTATION_AVAILABLE = True
except ImportError:
    LOG_ROTATION_AVAILABLE = False

try:
    from deploy_components import deploy_for_project, check_sync_status, get_target_path
    DEPLOY_AVAILABLE = True
except ImportError:
    DEPLOY_AVAILABLE = False

# Setup file-based logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

# ROTATE LOGS BEFORE SETTING UP LOGGING (prevents 48GB bloat issue)
if LOG_ROTATION_AVAILABLE:
    try:
        rotation_result = rotate_logs()
        # Can't log yet - logging not configured - write to stderr if rotated
        if rotation_result.get("rotated"):
            import sys
            print(f"Log rotated: {rotation_result.get('previous_size_mb', 0):.1f}MB", file=sys.stderr)
    except Exception:
        pass  # Silent fail - don't break startup

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('session_startup')

# Try to import psycopg for database access
DB_AVAILABLE = False
try:
    import psycopg
    from psycopg.rows import dict_row
    DB_AVAILABLE = True
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        DB_AVAILABLE = True
        PSYCOPG_VERSION = 2
    except ImportError:
        DB_AVAILABLE = False

# Default identity for claude-code-unified
DEFAULT_IDENTITY_ID = 'ff32276f-9d05-4a18-b092-31b54c82fff9'

# Default connection string - DO NOT hardcode credentials!
# Use environment variable DATABASE_URL or ai-workspace config
DEFAULT_CONN_STR = None  # Must be set via DATABASE_URL env var

# Try to load from ai-workspace secure config
try:
    import sys as _sys
    _sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
    from config import POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
except ImportError:
    pass


def get_db_connection():
    """Get PostgreSQL connection from environment or default."""
    conn_str = os.environ.get('DATABASE_URL', DEFAULT_CONN_STR)

    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(conn_str, row_factory=dict_row)
        else:
            return psycopg.connect(conn_str, cursor_factory=RealDictCursor)
    except Exception:
        return None


def resolve_identity_for_project(project_name):
    """Resolve the identity for a project from projects.default_identity_id.

    Falls back to environment variable or DEFAULT_IDENTITY_ID if:
    - Project doesn't exist in projects table
    - Project has no default_identity_id set
    - Database connection fails

    Returns the identity_id (UUID string) to use for the session.
    """
    if not DB_AVAILABLE:
        return os.environ.get('CLAUDE_IDENTITY_ID', DEFAULT_IDENTITY_ID)

    conn = get_db_connection()
    if not conn:
        return os.environ.get('CLAUDE_IDENTITY_ID', DEFAULT_IDENTITY_ID)

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT default_identity_id
            FROM claude.projects
            WHERE project_name = %s
              AND (is_archived = false OR is_archived IS NULL)
        """, (project_name,))

        row = cur.fetchone()
        conn.close()

        if row:
            default_identity = row['default_identity_id'] if isinstance(row, dict) else row[0]
            if default_identity:
                return str(default_identity)

        # Fall back to environment or default
        return os.environ.get('CLAUDE_IDENTITY_ID', DEFAULT_IDENTITY_ID)
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return os.environ.get('CLAUDE_IDENTITY_ID', DEFAULT_IDENTITY_ID)


def create_session(project_name, identity_id=None, claude_session_id=None):
    """Create a new session record in claude.sessions.

    Args:
        project_name: Name of the project
        identity_id: Optional identity UUID
        claude_session_id: Session ID from Claude Code (use this instead of generating new)

    Returns the session_id if successful, None otherwise.
    """
    if not DB_AVAILABLE:
        logger.warning("Database not available - cannot create session")
        return None

    conn = get_db_connection()
    if not conn:
        logger.error("Failed to connect to database")
        return None

    try:
        # Use Claude Code's session_id if provided, otherwise generate new
        session_id = claude_session_id if claude_session_id else str(uuid.uuid4())

        # Resolve identity: explicit parameter > project default > env var > hardcoded default
        if identity_id:
            identity = identity_id
        else:
            identity = resolve_identity_for_project(project_name)

        logger.info(f"Creating session for project '{project_name}' with identity '{identity}'")

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.sessions (session_id, identity_id, project_name, session_start, created_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            RETURNING session_id
        """, (session_id, identity, project_name))

        conn.commit()
        result = cur.fetchone()
        conn.close()

        if result:
            final_id = str(result['session_id']) if PSYCOPG_VERSION == 3 else str(result[0])
            logger.info(f"SUCCESS: Session created - ID: {final_id}")
            return final_id
        logger.info(f"Session created with ID: {session_id}")
        return session_id
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        try:
            conn.close()
        except Exception:
            pass
        return None


def get_session_state(project_name):
    """Get saved session state for project."""
    if not DB_AVAILABLE:
        return None

    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT todo_list, current_focus, next_steps, files_modified, pending_actions, updated_at
            FROM claude.session_state
            WHERE project_name = %s
        """, (project_name,))

        row = cur.fetchone()
        conn.close()

        if row:
            return dict(row) if PSYCOPG_VERSION == 3 else row
        return None
    except Exception as e:
        return None


def get_todos_from_database(project_id, session_id):
    """
    Load todos from claude.todos table and auto-complete obvious ones.

    Smart auto-completion rules:
    - "RESTART" in content + new session = mark completed
    - "Verify RAG" + RAG working = mark completed
    - "Fix SessionStart" + SessionStart succeeded = mark completed
    """
    if not DB_AVAILABLE:
        return []

    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()

        # Load pending/in_progress todos
        cur.execute("""
            SELECT
                todo_id::text,
                content,
                active_form,
                status,
                priority,
                display_order
            FROM claude.todos
            WHERE project_id = %s::uuid
              AND status IN ('pending', 'in_progress')
              AND is_deleted = false
            ORDER BY priority ASC, display_order ASC, created_at ASC
        """, (project_id,))

        todos = cur.fetchall()

        # Smart auto-completion logic
        auto_completed = []

        for todo in todos:
            content_lower = todo['content'].lower()
            should_complete = False

            # Rule 1: "restart" in content = auto-complete (we're in a new session!)
            if 'restart' in content_lower and 'claude' in content_lower:
                should_complete = True
                logger.info(f"Auto-completing todo (restart detected): {todo['content'][:50]}...")

            # Rule 2: "verify rag" + check if RAG is working
            elif 'verify' in content_lower and 'rag' in content_lower:
                # Check hooks.log for recent RAG success
                try:
                    log_file = Path.home() / ".claude" / "hooks.log"
                    if log_file.exists():
                        with open(log_file, 'r') as f:
                            recent_logs = f.readlines()[-100:]  # Last 100 lines
                            for line in recent_logs:
                                if 'rag_query' in line and 'RAG query success' in line:
                                    should_complete = True
                                    logger.info(f"Auto-completing todo (RAG verified): {todo['content'][:50]}...")
                                    break
                except Exception:
                    pass

            # Rule 3: "fix sessionstart" + this session started successfully
            elif 'fix' in content_lower and 'sessionstart' in content_lower:
                # If we got here, SessionStart succeeded!
                should_complete = True
                logger.info(f"Auto-completing todo (SessionStart working): {todo['content'][:50]}...")

            if should_complete:
                # Mark as completed in database
                cur.execute("""
                    UPDATE claude.todos
                    SET status = 'completed',
                        completed_at = NOW(),
                        completed_session_id = %s::uuid,
                        updated_at = NOW()
                    WHERE todo_id = %s::uuid
                """, (session_id, todo['todo_id']))
                auto_completed.append(todo['content'])

        if auto_completed:
            conn.commit()
            logger.info(f"Auto-completed {len(auto_completed)} obvious todos")

        # Reload todos after auto-completion
        cur.execute("""
            SELECT
                todo_id::text,
                content,
                active_form,
                status,
                priority,
                display_order
            FROM claude.todos
            WHERE project_id = %s::uuid
              AND status IN ('pending', 'in_progress')
              AND is_deleted = false
            ORDER BY priority ASC, display_order ASC, created_at ASC
        """, (project_id,))

        final_todos = cur.fetchall()
        conn.close()

        return final_todos if final_todos else []

    except Exception as e:
        logger.error(f"Failed to load todos from database: {e}")
        if conn:
            conn.close()
        return []


def get_pending_messages(project_name):
    """Check for pending messages and return detailed message data."""
    if not DB_AVAILABLE:
        return []

    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                message_id::text,
                from_session_id::text,
                to_project,
                to_session_id::text,
                message_type,
                subject,
                body,
                priority,
                created_at
            FROM claude.messages
            WHERE status = 'pending'
              AND (to_project = %s OR message_type = 'broadcast')
            ORDER BY
                CASE priority
                    WHEN 'urgent' THEN 1
                    WHEN 'normal' THEN 2
                    WHEN 'low' THEN 3
                END,
                created_at ASC
            LIMIT 10
        """, (project_name,))

        rows = cur.fetchall()
        conn.close()

        # Convert rows to list of dicts if needed
        if rows and not isinstance(rows[0], dict):
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
        return rows if rows else []
    except Exception as e:
        logger.warning(f"Failed to get pending messages: {e}")
        return []


def get_active_work_items(project_id):
    """Load active features, feedback, and build_tasks for context injection."""
    if not DB_AVAILABLE:
        return {'features': [], 'feedback': [], 'build_tasks': []}

    conn = get_db_connection()
    if not conn:
        return {'features': [], 'feedback': [], 'build_tasks': []}

    try:
        cur = conn.cursor()

        # Active features
        cur.execute("""
            SELECT 'F' || short_code as code, feature_name, status
            FROM claude.features
            WHERE project_id = %s::uuid
              AND status IN ('draft', 'planned', 'in_progress', 'blocked')
            ORDER BY short_code
            LIMIT 10
        """, (project_id,))
        features = cur.fetchall()

        # Open feedback
        cur.execute("""
            SELECT 'FB' || short_code as code, description, feedback_type, status
            FROM claude.feedback
            WHERE project_id = %s::uuid
              AND status IN ('new', 'triaged', 'in_progress')
            ORDER BY short_code
            LIMIT 10
        """, (project_id,))
        feedback = cur.fetchall()

        # Active build_tasks
        cur.execute("""
            SELECT 'BT' || bt.short_code as code, bt.task_name, bt.status,
                   'F' || f.short_code as feature_code
            FROM claude.build_tasks bt
            LEFT JOIN claude.features f ON bt.feature_id = f.feature_id
            WHERE bt.project_id = %s::uuid
              AND bt.status IN ('pending', 'in_progress', 'blocked')
            ORDER BY bt.short_code
            LIMIT 10
        """, (project_id,))
        build_tasks = cur.fetchall()

        conn.close()

        return {
            'features': features if features else [],
            'feedback': feedback if feedback else [],
            'build_tasks': build_tasks if build_tasks else []
        }
    except Exception as e:
        logger.warning(f"Failed to load work items: {e}")
        if conn:
            conn.close()
        return {'features': [], 'feedback': [], 'build_tasks': []}


def get_governance_compliance(project_name):
    """Check project governance compliance."""
    if not DB_AVAILABLE:
        return None

    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                has_claude_md,
                has_problem_statement,
                has_architecture,
                compliance_pct,
                phase
            FROM claude.v_project_governance
            WHERE project_name = %s
        """, (project_name,))

        row = cur.fetchone()
        conn.close()

        if row:
            return dict(row) if PSYCOPG_VERSION == 3 else dict(row)
        return None
    except Exception:
        return None


def generate_embedding_for_rag(text):
    """Generate embedding using Voyage AI REST API."""
    try:
        import requests
        api_key = os.environ.get('VOYAGE_API_KEY')
        if not api_key:
            return None

        response = requests.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "input": [text],
                "model": "voyage-3",
                "input_type": "document"
            },
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        return result["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"Failed to generate embedding for RAG: {e}")
        return None


def preload_relevant_docs(conn, project_name, session_id, top_k=3, min_similarity=0.5):
    """Pre-load relevant vault documents based on project type/phase.

    Uses semantic search to find the most relevant docs for this project.
    Returns formatted text to inject into context and logs usage.
    """
    try:
        start_time = time.time()

        # Get project type for query
        cur = conn.cursor()
        cur.execute("""
            SELECT project_type, phase
            FROM claude.workspaces w
            LEFT JOIN claude.projects p ON w.project_name = p.project_name
            WHERE w.project_name = %s
        """, (project_name,))
        row = cur.fetchone()

        if not row:
            return None

        project_type = row['project_type'] if isinstance(row, dict) else row[0]
        phase = row['phase'] if isinstance(row, dict) else (row[1] if len(row) > 1 else 'unknown')

        # Build query based on project type and phase
        query_parts = []
        if project_type:
            query_parts.append(f"{project_type} project")
        if phase:
            query_parts.append(f"{phase} phase")
        query_parts.append("procedures and standards")

        query = " ".join(query_parts)
        logger.info(f"RAG pre-load query: '{query}'")

        # Generate embedding for query
        query_embedding = generate_embedding_for_rag(query)
        if not query_embedding:
            logger.warning("Could not generate embedding - skipping RAG pre-load")
            return None

        # Search for similar documents (prefer vault docs, include project docs)
        cur.execute("""
            SELECT
                doc_path,
                doc_title,
                chunk_text,
                doc_source,
                1 - (embedding <=> %s::vector) as similarity_score
            FROM claude.vault_embeddings
            WHERE 1 - (embedding <=> %s::vector) >= %s
              AND (doc_source = 'vault' OR (doc_source = 'project' AND project_name = %s))
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity, project_name, query_embedding, top_k))

        results = cur.fetchall()

        # Log usage
        latency_ms = int((time.time() - start_time) * 1000)
        docs_returned = [r['doc_path'] if isinstance(r, dict) else r[0] for r in results]
        top_similarity = results[0]['similarity_score'] if results and isinstance(results[0], dict) else (results[0][4] if results else None)

        cur.execute("""
            INSERT INTO claude.rag_usage_log
            (session_id, project_name, query_type, query_text, results_count,
             top_similarity, docs_returned, latency_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            session_id,
            project_name,
            "session_preload",
            query,
            len(results),
            top_similarity,
            docs_returned,
            latency_ms
        ))
        conn.commit()

        if not results:
            logger.info("No relevant docs found for RAG pre-load")
            return None

        # Format results
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 60)
        context_lines.append(f"PRE-LOADED KNOWLEDGE ({len(results)} docs, {latency_ms}ms)")
        context_lines.append("=" * 60)
        context_lines.append("")

        for r in results:
            if isinstance(r, dict):
                doc_path = r['doc_path']
                doc_title = r['doc_title']
                chunk_text = r['chunk_text']
                similarity = round(r['similarity_score'], 3)
            else:
                doc_path = r[0]
                doc_title = r[1]
                chunk_text = r[2]
                similarity = round(r[4], 3)

            context_lines.append(f"📄 {doc_title} ({similarity} similarity)")
            context_lines.append(f"   Path: {doc_path}")
            context_lines.append("")
            # Truncate long chunks
            preview = chunk_text[:500] + "..." if len(chunk_text) > 500 else chunk_text
            context_lines.append(preview)
            context_lines.append("")
            context_lines.append("-" * 60)
            context_lines.append("")

        logger.info(f"RAG pre-load: {len(results)} docs, top similarity={top_similarity}, latency={latency_ms}ms")
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"RAG pre-load failed: {e}", exc_info=True)
        return None


def sync_workspaces_json():
    """Sync workspaces.json from database if project is missing.

    Regenerates workspaces.json if the current project isn't in it.
    This ensures new projects get proper config deployment.
    """
    if not DB_AVAILABLE:
        return False

    workspaces_file = Path(__file__).parent.parent.parent.parent.parent / "workspaces.json"
    cwd = os.getcwd()
    project_name = os.path.basename(cwd)

    # Check if current project is in workspaces.json
    try:
        if workspaces_file.exists():
            with open(workspaces_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if project_name in data.get('workspaces', {}):
                    return True  # Already in file, no sync needed

        # Project not in file - regenerate from database
        logger.info(f"Project '{project_name}' not in workspaces.json - regenerating...")

        conn = get_db_connection()
        if not conn:
            return False

        cur = conn.cursor()
        cur.execute("""
            SELECT project_name, project_path, project_type, description
            FROM claude.workspaces
            WHERE is_active = true
            ORDER BY project_name
        """)
        rows = cur.fetchall()
        conn.close()

        # Build new workspaces.json
        workspaces = {}
        for row in rows:
            if PSYCOPG_VERSION == 2:
                name, path, ptype, desc = row[0], row[1], row[2], row[3]
            else:
                name, path, ptype, desc = row['project_name'], row['project_path'], row['project_type'], row['description']

            workspaces[name] = {
                "path": path,
                "type": ptype or "infrastructure",
                "description": desc or ""
            }

        new_data = {
            "_metadata": {
                "generated_at": datetime.now().isoformat(),
                "source": "PostgreSQL (claude.workspaces)",
                "description": "Auto-generated workspace mappings. Do not edit manually."
            },
            "workspaces": workspaces
        }

        with open(workspaces_file, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2)

        logger.info(f"Regenerated workspaces.json with {len(workspaces)} projects")
        return True

    except Exception as e:
        logger.warning(f"Could not sync workspaces.json: {e}")
        return False


def fix_windows_npx_commands(project_path):
    """Fix .mcp.json files to use cmd /c wrapper for npx on Windows.

    On Windows, npx commands need to be wrapped with 'cmd /c' otherwise
    Claude Code shows a warning: "Windows requires 'cmd /c' wrapper to execute npx"

    This function automatically fixes any .mcp.json files in the project.
    """
    if sys.platform != 'win32':
        return 0  # Only applies to Windows

    mcp_json_path = Path(project_path) / '.mcp.json'
    if not mcp_json_path.exists():
        return 0

    fixes_made = 0
    try:
        with open(mcp_json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        modified = False
        servers = config.get('mcpServers', {})

        for server_name, server_config in servers.items():
            # Check if command is "npx" without cmd wrapper
            if server_config.get('command') == 'npx':
                # Need to wrap with cmd /c
                old_args = server_config.get('args', [])
                server_config['command'] = 'cmd'
                server_config['args'] = ['/c', 'npx'] + old_args
                modified = True
                fixes_made += 1
                logger.info(f"Fixed Windows npx wrapper for MCP server: {server_name}")

        if modified:
            with open(mcp_json_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Updated .mcp.json with {fixes_made} npx wrapper fix(es)")

    except Exception as e:
        logger.warning(f"Could not fix Windows npx commands: {e}")

    return fixes_made


def main():
    """Run startup checks and output JSON context."""
    try:
        is_resume = '--resume' in sys.argv
        logger.info(f"SessionStart hook invoked (resume={is_resume})")

        # Read hook input from stdin (Claude Code passes session_id and other context)
        hook_input = {}
        try:
            raw_input = sys.stdin.read()
            if raw_input.strip():
                hook_input = json.loads(raw_input)
                logger.info(f"Hook input received: session_id={hook_input.get('session_id')}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse hook input: {e}")

        # Extract session_id from Claude Code's hook input
        claude_session_id = hook_input.get('session_id')

        # Claude Code expects additionalContext at top level (not nested in hookSpecificOutput)
        result = {
            "additionalContext": "",
            "systemMessage": "",
            "environment": {}  # Environment variables to export for this session
        }

        context_lines = []

        # Get current directory to determine project (prefer hook input)
        cwd = hook_input.get('cwd') or os.getcwd()
        project_name = os.path.basename(cwd)
        logger.info(f"Project: {project_name}")

        # SYNC CONFIGURATION: Generate settings.local.json from database
        # This is the self-healing step - manual file edits get overwritten
        if CONFIG_SYNC_AVAILABLE:
            logger.info("Syncing configuration from database...")
            sync_success = sync_project_config(project_name, cwd)
            if sync_success:
                logger.info("Configuration sync completed successfully")
            else:
                logger.warning("Configuration sync failed - using existing settings")
        else:
            logger.warning("Config sync not available - generate_project_settings.py not found")

        # DEPLOY COMPONENTS: Deploy CLAUDE.md, skills, rules, etc. from database
        # This ensures files match database (ADR-006: database is source of truth)
        deploy_conflicts = []
        if DEPLOY_AVAILABLE:
            logger.info("Deploying components from database...")
            try:
                deploy_result = deploy_for_project(project_name, dry_run=False, force=False)

                # Track conflicts for user notification
                if deploy_result.get('conflicts'):
                    deploy_conflicts = deploy_result['conflicts']
                    logger.warning(f"Component deployment found {len(deploy_conflicts)} conflicts")

                deployed_count = len(deploy_result.get('deployed', []))
                skipped_count = len(deploy_result.get('skipped', []))
                error_count = len(deploy_result.get('errors', []))

                if deployed_count > 0:
                    logger.info(f"Deployed {deployed_count} components")
                if error_count > 0:
                    logger.warning(f"Failed to deploy {error_count} components")
                    for err in deploy_result.get('errors', []):
                        if isinstance(err, dict):
                            logger.warning(f"  - {err.get('type')}/{err.get('name')}: {err.get('error')}")
            except Exception as e:
                logger.error(f"Component deployment failed: {e}")
        else:
            logger.warning("Component deployment not available - deploy_components.py not found")

        # SYNC WORKSPACES.JSON: Ensure new projects are in workspaces.json
        sync_workspaces_json()

        # FIX WINDOWS NPX COMMANDS: Automatically add cmd /c wrapper
        npx_fixes = fix_windows_npx_commands(cwd)
        if npx_fixes > 0:
            context_lines.append(f"[AUTO-FIX] Fixed {npx_fixes} MCP server(s) with Windows npx wrapper")

        # WARN ABOUT CONFLICTS: If local files were modified, notify user
        if deploy_conflicts:
            context_lines.append("")
            context_lines.append("=" * 60)
            context_lines.append(f"!! LOCAL FILE CHANGES DETECTED ({len(deploy_conflicts)} files)")
            context_lines.append("=" * 60)
            context_lines.append("")
            context_lines.append("The following files have been modified locally and differ from database:")
            context_lines.append("")
            for conflict in deploy_conflicts:
                context_lines.append(f"   - {conflict['type']}: {conflict['name']}")
                context_lines.append(f"     Path: {conflict['path']}")
            context_lines.append("")
            context_lines.append("OPTIONS:")
            context_lines.append("   1. Accept local changes: Run 'python scripts/deploy_components.py --import'")
            context_lines.append("   2. Discard local changes: Run 'python scripts/deploy_components.py --force'")
            context_lines.append("   3. Continue as-is (files will remain out of sync)")
            context_lines.append("")
            context_lines.append("NOTE: Database is source of truth (ADR-006). To persist local edits,")
            context_lines.append("      import them to database first, then they will deploy to all projects.")
            context_lines.append("=" * 60)
            context_lines.append("")

        # Get project_id from database (needed for todos and other queries)
        project_id = None
        if DB_AVAILABLE:
            try:
                conn = get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute("SELECT project_id::text FROM claude.projects WHERE project_name = %s", (project_name,))
                    row = cur.fetchone()
                    if row:
                        project_id = row[0] if PSYCOPG_VERSION == 2 else row['project_id']
                    conn.close()
            except Exception:
                pass

        # AUTO-LOG SESSION: Create session record for new sessions (not resumes)
        session_id = None
        if not is_resume:
            # Pass Claude Code's session_id so we use the same ID throughout
            session_id = create_session(project_name, claude_session_id=claude_session_id)
            # Export session_id as environment variable for MCP usage logging and todo tracking
            if session_id:
                result["environment"]["CLAUDE_SESSION_ID"] = session_id
                result["environment"]["SESSION_ID"] = session_id  # Also set SESSION_ID for hooks
                result["environment"]["PROJECT_ID"] = project_id if project_id else ""  # For todo_sync_hook
                result["environment"]["CLAUDE_PROJECT_NAME"] = project_name
                logger.info(f"Environment variables set for session")
            else:
                logger.warning("Session creation failed - no environment variables set")

        context_lines.append(f"=== Claude Family Session {'Resumed' if is_resume else 'Started'} ===")
        context_lines.append(f"Project: {project_name}")
        context_lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        if session_id:
            context_lines.append(f"Session ID: {session_id} (auto-logged)")
            context_lines.append(f"MCP logging: enabled (session tracking active)")
        context_lines.append("")

        # Check for saved session state
        state = get_session_state(project_name)
        if state:
            context_lines.append("=" * 50)
            context_lines.append("HERE'S WHERE WE LEFT OFF:")
            context_lines.append("=" * 50)
            context_lines.append("")

            if state.get('current_focus'):
                context_lines.append(f"Focus: {state['current_focus']}")
                context_lines.append("")

            # Show next_steps prominently - this is the key handoff info
            next_steps = state.get('next_steps', [])
            if isinstance(next_steps, str):
                try:
                    next_steps = json.loads(next_steps)
                except Exception:
                    next_steps = []
            if next_steps:
                context_lines.append("NEXT STEPS (from last session):")
                for i, step in enumerate(next_steps, 1):
                    if isinstance(step, dict):
                        step = step.get('content', str(step))
                    context_lines.append(f"   {i}. {step}")
                context_lines.append("")

            context_lines.append("=" * 50)
            context_lines.append("")

        # Load todos from database (with smart auto-completion)
        if project_id and session_id:
            db_todos = get_todos_from_database(project_id, session_id)
            if db_todos:
                context_lines.append("=" * 50)
                context_lines.append(f"ACTIVE TODOS ({len(db_todos)} items):")
                context_lines.append("=" * 50)
                for idx, todo in enumerate(db_todos, 1):
                    priority = todo.get('priority', 3)
                    priority_icon = "🔴" if priority == 1 else "🟡" if priority == 2 else "🔵"
                    status = todo.get('status', 'pending')
                    status_icon = '→' if status == 'in_progress' else '○'
                    content = todo.get('content', 'Unknown')
                    context_lines.append(f"   {idx}. {priority_icon} {status_icon} {content}")
                context_lines.append("")
                context_lines.append("Note: Obvious completed todos (like 'restart') auto-completed on session start")
                context_lines.append("=" * 50)
                context_lines.append("")
                context_lines.append("IMPORTANT: Call TodoWrite immediately to populate the tool with the above todos:")
                context_lines.append("")
                context_lines.append("TodoWrite([")
                for idx, todo in enumerate(db_todos):
                    status = todo.get('status', 'pending')
                    content = todo.get('content', 'Unknown')
                    active_form = todo.get('active_form', content)
                    # Escape quotes in content
                    content_escaped = content.replace('"', '\\"')
                    active_form_escaped = active_form.replace('"', '\\"')
                    comma = "," if idx < len(db_todos) - 1 else ""
                    context_lines.append(f'  {{"content": "{content_escaped}", "activeForm": "{active_form_escaped}", "status": "{status}"}}{comma}')
                context_lines.append("])")
                context_lines.append("")
                context_lines.append("=" * 50)
                context_lines.append("")

        # Load active work items (features, feedback, build_tasks)
        work_items = get_active_work_items(project_id)
        has_work_items = any([work_items['features'], work_items['feedback'], work_items['build_tasks']])

        if has_work_items:
            context_lines.append("=" * 50)
            context_lines.append("📋 ACTIVE WORK ITEMS")
            context_lines.append("=" * 50)

            if work_items['features']:
                context_lines.append("")
                context_lines.append("FEATURES:")
                for f in work_items['features']:
                    code = f['code'] if isinstance(f, dict) else f[0]
                    name = f['feature_name'] if isinstance(f, dict) else f[1]
                    status = f['status'] if isinstance(f, dict) else f[2]
                    context_lines.append(f"   {code}: {name} [{status}]")

            if work_items['feedback']:
                context_lines.append("")
                context_lines.append("OPEN FEEDBACK:")
                for fb in work_items['feedback']:
                    code = fb['code'] if isinstance(fb, dict) else fb[0]
                    desc = fb['description'] if isinstance(fb, dict) else fb[1]
                    ftype = fb['feedback_type'] if isinstance(fb, dict) else fb[2]
                    desc_short = (desc[:40] + "...") if desc and len(desc) > 40 else desc
                    context_lines.append(f"   {code}: {desc_short} [{ftype}]")

            if work_items['build_tasks']:
                context_lines.append("")
                context_lines.append("BUILD TASKS:")
                for bt in work_items['build_tasks']:
                    code = bt['code'] if isinstance(bt, dict) else bt[0]
                    name = bt['task_name'] if isinstance(bt, dict) else bt[1]
                    status = bt['status'] if isinstance(bt, dict) else bt[2]
                    feat = bt.get('feature_code', '') if isinstance(bt, dict) else (bt[3] if len(bt) > 3 else '')
                    feat_str = f" → {feat}" if feat else ""
                    context_lines.append(f"   {code}: {name} [{status}]{feat_str}")

            context_lines.append("")
            context_lines.append("TIP: Link commits to work items using branch naming: feature/F1-desc, fix/FB1-desc")
            context_lines.append("=" * 50)
            context_lines.append("")
        else:
            # No active work items - gentle reminder
            context_lines.append("")
            context_lines.append("💡 No active features for this project. Consider creating one for significant work.")
            context_lines.append("")

        # Check for pending messages
        pending_messages = get_pending_messages(project_name)
        msg_count = len(pending_messages) if pending_messages else 0
        if pending_messages:
            context_lines.append("=" * 50)
            context_lines.append(f"📬 INBOX: {len(pending_messages)} PENDING MESSAGE(S)")
            context_lines.append("=" * 50)
            for idx, msg in enumerate(pending_messages[:5], 1):  # Show max 5
                priority_icon = "🔴" if msg['priority'] == 'urgent' else "🟡" if msg['priority'] == 'normal' else "🔵"
                msg_type = msg['message_type'].upper()
                context_lines.append(f"\n{priority_icon} Message {idx}: [{msg_type}] {msg['subject']}")
                from_id = msg.get('from_session_id') or 'System'
                context_lines.append(f"   From: {from_id[:8]}...")
                context_lines.append(f"   To: {msg.get('to_project', 'Direct')} | Created: {msg['created_at']}")

                # Show preview of body (first 200 chars)
                body = msg.get('body', '').strip()
                if body:
                    body_preview = body[:200] + "..." if len(body) > 200 else body
                    context_lines.append(f"   Preview: {body_preview}")

                # Add ID for acknowledgment
                context_lines.append(f"   ID: {msg['message_id']}")

            if len(pending_messages) > 5:
                context_lines.append(f"\n   ... and {len(pending_messages) - 5} more messages")

            context_lines.append("\nACTIONS:")
            context_lines.append("   - Use mcp__orchestrator__acknowledge(message_id, action='read') to mark as read")
            context_lines.append("   - Use mcp__orchestrator__acknowledge(message_id, action='actioned', project_id=UUID) to create todo")
            context_lines.append("   - Use mcp__orchestrator__acknowledge(message_id, action='deferred', defer_reason='...') to skip")
            context_lines.append("=" * 50)
            context_lines.append("")

        # Check governance compliance
        compliance = get_governance_compliance(project_name)
        if compliance:
            pct = compliance.get('compliance_pct', 0)
            if pct < 100:
                context_lines.append(f"⚠️  GOVERNANCE COMPLIANCE: {pct}%")
                missing = []
                if not compliance.get('has_claude_md'):
                    missing.append('CLAUDE.md')
                if not compliance.get('has_problem_statement'):
                    missing.append('PROBLEM_STATEMENT.md')
                if not compliance.get('has_architecture'):
                    missing.append('ARCHITECTURE.md')
                if missing:
                    context_lines.append(f"   Missing: {', '.join(missing)}")
                    context_lines.append("   Run /retrofit-project to add missing documents")
                context_lines.append("")
            else:
                context_lines.append(f"✓ Governance: 100% compliant (Phase: {compliance.get('phase', 'unknown')})")
                context_lines.append("")

        # Reminder about commands
        context_lines.append("Available commands: /session-start, /session-end, /inbox-check, /feedback-check, /team-status, /broadcast")

        # PRE-LOAD RELEVANT KNOWLEDGE: Use RAG to inject relevant vault docs
        if session_id and DB_AVAILABLE:
            conn = get_db_connection()
            if conn:
                try:
                    rag_context = preload_relevant_docs(conn, project_name, session_id)
                    if rag_context:
                        context_lines.append(rag_context)
                    conn.close()
                except Exception as e:
                    logger.warning(f"RAG pre-load failed: {e}")
                    try:
                        conn.close()
                    except Exception:
                        pass

        result["additionalContext"] = "\n".join(context_lines)

        # Build system message - show key info to user
        system_parts = [f"Claude Family session {'resumed' if is_resume else 'started'} for {project_name}."]

        # Show session logging status
        if session_id:
            system_parts.append(f"Session logged ({session_id[:8]}...).")
        elif not is_resume:
            system_parts.append("Session NOT logged (database unavailable).")

        if state:
            # Show next steps count first - most important for continuity
            next_steps = state.get('next_steps', [])
            if isinstance(next_steps, str):
                try:
                    next_steps = json.loads(next_steps)
                except Exception:
                    next_steps = []
            if next_steps:
                system_parts.append(f"{len(next_steps)} next steps from last session.")

            if state.get('current_focus'):
                system_parts.append(f"Focus: {state['current_focus'][:60]}...")

            # Use database todos instead of session_state
            if 'db_todos' in locals() and db_todos:
                system_parts.append(f"{len(db_todos)} active todos.")

            if msg_count > 0:
                system_parts.append(f"{msg_count} pending message(s).")

            result["systemMessage"] = " ".join(system_parts)

            logger.info(f"SUCCESS: SessionStart hook completed for {project_name}")
            print(json.dumps(result))
            return 0

    except Exception as e:
        logger.error(f"SessionStart hook failed: {e}", exc_info=True)
        # Return minimal valid output on error
        print(json.dumps({"additionalContext": "", "systemMessage": "Session start hook failed", "environment": {}}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
