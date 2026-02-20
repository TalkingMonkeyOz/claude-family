#!/usr/bin/env python3
"""
PreCompact Hook - Context Preservation Before Compaction

Runs before context compaction (manual /compact or auto-compact).
Injects critical session state that would otherwise be lost:
- Active work items (todos, features, build_tasks)
- Current focus and next steps
- CLAUDE.md refresh reminder
- Available MCP tools reminder

This ensures Claude retains situational awareness after compaction.

Hook Event: PreCompact
Output: systemMessage injected into post-compact context

Author: Claude Family
Date: 2025-12-29
Updated: 2026-02-07 (Enhanced with session state injection)
"""

import sys
import os
import io
import json
import logging
from pathlib import Path
from typing import Dict, Optional

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Setup logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('precompact')

# Try to import psycopg
DB_AVAILABLE = False
PSYCOPG_VERSION = None
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

# Load config
DEFAULT_CONN_STR = None
try:
    sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
    from config import POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
except ImportError:
    pass


def get_db_connection():
    """Get PostgreSQL connection."""
    if not DB_AVAILABLE:
        return None
    conn_str = os.environ.get('DATABASE_URL', DEFAULT_CONN_STR)
    if not conn_str:
        return None
    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(conn_str, row_factory=dict_row)
        else:
            return psycopg.connect(conn_str, cursor_factory=RealDictCursor)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


def get_session_state_for_compact(project_name: str) -> Optional[str]:
    """Query active work items and session state to preserve across compaction."""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        lines = []

        # Get project_id
        cur.execute("SELECT project_id::text FROM claude.projects WHERE project_name = %s", (project_name,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None
        project_id = row['project_id'] if isinstance(row, dict) else row[0]

        # Get active todos
        cur.execute("""
            SELECT content, status, priority
            FROM claude.todos
            WHERE project_id = %s::uuid AND is_deleted = false
              AND status IN ('pending', 'in_progress')
            ORDER BY CASE status WHEN 'in_progress' THEN 1 ELSE 2 END, priority ASC
            LIMIT 10
        """, (project_id,))
        todos = cur.fetchall()

        if todos:
            lines.append("ACTIVE TODOS (preserved from pre-compaction):")
            for t in todos:
                content = t['content'] if isinstance(t, dict) else t[0]
                status = t['status'] if isinstance(t, dict) else t[1]
                marker = "[>]" if status == 'in_progress' else "[ ]"
                lines.append(f"  {marker} {content}")

        # Get session state (focus, next_steps)
        cur.execute("""
            SELECT current_focus, next_steps
            FROM claude.session_state
            WHERE project_name = %s
        """, (project_name,))
        state = cur.fetchone()

        if state:
            focus = state['current_focus'] if isinstance(state, dict) else state[0]
            next_steps = state['next_steps'] if isinstance(state, dict) else state[1]
            if focus:
                lines.append(f"\nCURRENT FOCUS: {focus}")
            if next_steps and isinstance(next_steps, list):
                lines.append("\nNEXT STEPS:")
                for step in next_steps[:3]:
                    step_text = step.get('step', str(step)) if isinstance(step, dict) else str(step)
                    lines.append(f"  - {step_text}")

        # Get active features/build_tasks
        cur.execute("""
            SELECT f.feature_name, f.status,
                   (SELECT COUNT(*) FROM claude.build_tasks bt
                    WHERE bt.feature_id = f.feature_id AND bt.status = 'in_progress') as active_tasks
            FROM claude.features f
            WHERE f.project_id = %s::uuid AND f.status IN ('in_progress', 'planned')
            ORDER BY f.updated_at DESC LIMIT 3
        """, (project_id,))
        features = cur.fetchall()

        if features:
            lines.append("\nACTIVE FEATURES:")
            for f in features:
                name = f['feature_name'] if isinstance(f, dict) else f[0]
                status = f['status'] if isinstance(f, dict) else f[1]
                active = f['active_tasks'] if isinstance(f, dict) else f[2]
                lines.append(f"  - {name} ({status}, {active} active tasks)")

        # Get session facts (user intent, decisions, key references)
        # These preserve the narrative/context that structured data alone misses
        cur.execute("""
            SELECT fact_key, fact_value, fact_type
            FROM claude.session_facts
            WHERE session_id = (
                SELECT session_id FROM claude.sessions
                WHERE project_name = %s AND session_end IS NULL
                ORDER BY session_start DESC LIMIT 1
            )
            AND fact_type IN ('decision', 'reference', 'note')
            AND NOT is_sensitive
            ORDER BY created_at DESC LIMIT 5
        """, (project_name,))
        facts = cur.fetchall()

        if facts:
            lines.append("\nSESSION CONTEXT (decisions & intent):")
            for f in facts:
                key = f['fact_key'] if isinstance(f, dict) else f[0]
                value = f['fact_value'] if isinstance(f, dict) else f[1]
                # Truncate long values
                display = value[:200] + "..." if len(value) > 200 else value
                lines.append(f"  [{key}]: {display}")

        conn.close()
        return "\n".join(lines) if lines else None

    except Exception as e:
        logger.error(f"Failed to get session state for compact: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return None


def build_refresh_message(hook_input: Dict) -> str:
    """Build context refresh message with session state."""
    project_root = Path.cwd()
    project_name = project_root.name
    compact_type = hook_input.get('matcher', 'unknown')

    parts = [
        f"CONTEXT COMPACTION ({compact_type.upper()}) - PRESERVED STATE",
        "=" * 60,
    ]

    # Inject session state from database
    session_state = get_session_state_for_compact(project_name)
    if session_state:
        parts.append("")
        parts.append(session_state)

    # Also inject session notes if they exist
    notes_path = Path.home() / ".claude" / "session_notes.md"
    if notes_path.exists():
        try:
            notes_content = notes_path.read_text(encoding='utf-8').strip()
            if notes_content and len(notes_content) > 20:
                # Truncate to avoid bloating context
                if len(notes_content) > 500:
                    notes_content = notes_content[:500] + "\n  ... (truncated, use get_session_notes() for full)"
                parts.append("")
                parts.append("SESSION NOTES (from this session):")
                parts.append(notes_content)
        except Exception:
            pass

    parts.extend([
        "",
        "=" * 60,
        "POST-COMPACTION CHECKLIST:",
        "",
        "1. Re-read CLAUDE.md (project rules may have been lost)",
        "2. Recall user intent: recall_session_fact('user_intent')",
        "3. Check the work items above - continue where you left off",
        "4. Use MCP tools:",
        "   - project-tools: work tracking, knowledge, session facts",
        "   - orchestrator: agent spawning, messaging",
        "   - sequential-thinking: complex analysis",
        "",
        "5. Database is source of truth for config (not files)",
    ])

    return "\n".join(parts)


def main():
    """Main entry point for the hook."""
    logger.info("PreCompact hook invoked")

    try:
        try:
            hook_input = json.load(sys.stdin)
        except json.JSONDecodeError:
            hook_input = {}

        refresh_message = build_refresh_message(hook_input)

        response = {
            "systemMessage": f"<claude-context-refresh>\n{refresh_message}\n</claude-context-refresh>"
        }

        print(json.dumps(response))
        logger.info("PreCompact hook completed - session state injected")
        return 0

    except Exception as e:
        logger.error(f"PreCompact hook failed: {e}", exc_info=True)
        try:
            from failure_capture import capture_failure
            capture_failure("precompact_hook", str(e), "scripts/precompact_hook.py")
        except Exception:
            pass
        print(json.dumps({"systemMessage": "Context compaction occurred. Re-read CLAUDE.md and check work items."}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
