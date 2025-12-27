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


def get_pending_messages(project_name):
    """Check for pending messages."""
    if not DB_AVAILABLE:
        return 0

    conn = get_db_connection()
    if not conn:
        return 0

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as count
            FROM claude.messages
            WHERE status = 'pending'
              AND (to_project = %s OR to_project IS NULL)
        """, (project_name,))

        row = cur.fetchone()
        conn.close()

        if row:
            return row['count'] if isinstance(row, dict) else row[0]
        return 0
    except:
        return 0


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

        # AUTO-LOG SESSION: Create session record for new sessions (not resumes)
        session_id = None
        if not is_resume:
            session_id = create_session(project_name)
            # Export session_id as environment variable for MCP usage logging
            if session_id:
                result["environment"]["CLAUDE_SESSION_ID"] = session_id
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

        # Show pending todos
        if state.get('todo_list'):
            todo_list = state['todo_list']
            if isinstance(todo_list, str):
                try:
                    todo_list = json.loads(todo_list)
                except:
                    pass
            if isinstance(todo_list, list):
                pending = [t for t in todo_list if t.get('status') != 'completed']
                if pending:
                    context_lines.append(f"PENDING TODOS ({len(pending)} items):")
                    for item in pending[:5]:
                        status = item.get('status', 'pending')
                        icon = '→' if status == 'in_progress' else '○'
                        context_lines.append(f"   {icon} {item.get('content', 'Unknown')}")
                    if len(pending) > 5:
                        context_lines.append(f"   ... and {len(pending) - 5} more")
                    context_lines.append("")

        context_lines.append("=" * 50)
        context_lines.append("")

    # Check for pending messages
    msg_count = get_pending_messages(project_name)
    if msg_count > 0:
        context_lines.append(f"📬 {msg_count} pending message(s) - use /inbox-check to view")
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

        if state.get('todo_list'):
            todo_list = state['todo_list']
            if isinstance(todo_list, str):
                try:
                    todo_list = json.loads(todo_list)
                except:
                    pass
            if isinstance(todo_list, list):
                pending = [t for t in todo_list if t.get('status') != 'completed']
                if pending:
                    system_parts.append(f"{len(pending)} pending todos.")

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
