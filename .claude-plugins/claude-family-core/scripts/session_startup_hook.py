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

# Setup file-based logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

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
    except:
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
        except:
            pass
        return os.environ.get('CLAUDE_IDENTITY_ID', DEFAULT_IDENTITY_ID)


def create_session(project_name, identity_id=None):
    """Create a new session record in claude.sessions.

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
        session_id = str(uuid.uuid4())

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
        except:
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
                except:
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


def get_due_reminders(project_name):
    """Check for due reminders."""
    if not DB_AVAILABLE:
        return []

    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT reminder_id, title, description, check_after, reminder_count, max_reminders
            FROM claude.reminders
            WHERE status = 'pending'
              AND check_after <= NOW()
              AND (project_name = %s OR project_name IS NULL)
            ORDER BY check_after ASC
            LIMIT 5
        """, (project_name,))

        rows = cur.fetchall()
        conn.close()

        return [dict(r) if PSYCOPG_VERSION == 3 else dict(r) for r in rows]
    except:
        return []


def get_due_jobs(project_name):
    """Check for scheduled jobs that should run."""
    if not DB_AVAILABLE:
        return []

    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT job_id, job_name, job_description,
                   EXTRACT(DAY FROM NOW() - COALESCE(last_run, created_at)) as days_since_run
            FROM claude.scheduled_jobs
            WHERE is_active = true
              AND (
                  -- Check if enough days have passed (default 7 if no trigger_condition)
                  EXTRACT(DAY FROM NOW() - COALESCE(last_run, created_at)) >= 7
              )
            ORDER BY last_run ASC NULLS FIRST
            LIMIT 3
        """)

        rows = cur.fetchall()
        conn.close()

        return [dict(r) if PSYCOPG_VERSION == 3 else dict(r) for r in rows]
    except:
        return []


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
    except:
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


def main():
    """Run startup checks and output JSON context."""
    try:
        is_resume = '--resume' in sys.argv
        logger.info(f"SessionStart hook invoked (resume={is_resume})")

        # Claude Code expects additionalContext at top level (not nested in hookSpecificOutput)
        result = {
            "additionalContext": "",
            "systemMessage": "",
            "environment": {}  # Environment variables to export for this session
        }

        context_lines = []

        # Get current directory to determine project
        cwd = os.getcwd()
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
            except:
                pass

        # AUTO-LOG SESSION: Create session record for new sessions (not resumes)
        session_id = None
        if not is_resume:
            session_id = create_session(project_name)
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
                except:
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
                context_lines.append(f"   From: {msg.get('from_session_id', 'Unknown')[:8]}...")
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

        # Check for due reminders
        reminders = get_due_reminders(project_name)
        if reminders:
            context_lines.append("⏰ DUE REMINDERS:")
            for r in reminders:
                context_lines.append(f"   - {r['title']}")
                if r.get('description'):
                    context_lines.append(f"     {r['description'][:100]}...")
            context_lines.append("")

        # Check for due scheduled jobs
        due_jobs = get_due_jobs(project_name)
        if due_jobs:
            context_lines.append("📅 JOBS DUE TO RUN:")
            for job in due_jobs:
                days = int(job.get('days_since_run', 0))
                context_lines.append(f"   - {job['job_name']} (last run: {days} days ago)")
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
                    except:
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
                except:
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

            if reminders:
                system_parts.append(f"{len(reminders)} reminder(s) due!")

            if due_jobs:
                system_parts.append(f"{len(due_jobs)} job(s) ready to run.")

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
