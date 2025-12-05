#!/usr/bin/env python3
"""
Session-end check for documentation updates.

Checks if CLAUDE.md was updated during the session when significant
changes were made. Returns warnings (non-blocking) if docs are stale.

Usage:
    python check_doc_updates.py [--project <project_name>]

Exit codes:
    0 = No issues
    1 = Warnings (non-blocking)

Output:
    JSON with decision, warnings, and suggestions
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Database imports
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

CONN_STR = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation'

# Core docs to check
CORE_DOCS = ['CLAUDE.md', 'ARCHITECTURE.md', 'PROBLEM_STATEMENT.md']

# Staleness thresholds
CLAUDE_MD_STALE_DAYS = 7
ARCHITECTURE_STALE_DAYS = 30


def get_db_connection():
    """Get PostgreSQL connection."""
    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(CONN_STR, row_factory=dict_row)
        else:
            return psycopg.connect(CONN_STR, cursor_factory=RealDictCursor)
    except Exception:
        return None


def detect_project_from_cwd() -> str:
    """Detect project name from current working directory."""
    cwd = Path.cwd()

    # Check if we're in C:\Projects\<project>
    if 'Projects' in cwd.parts:
        idx = cwd.parts.index('Projects')
        if len(cwd.parts) > idx + 1:
            return cwd.parts[idx + 1]

    return None


def get_session_activity(project_name: str) -> dict:
    """Get activity from current session."""
    if not DB_AVAILABLE:
        return {}

    conn = get_db_connection()
    if not conn:
        return {}

    try:
        cur = conn.cursor()

        # Check for recent build_tasks, features, or feedback created
        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM claude.build_tasks
                 WHERE created_at > NOW() - INTERVAL '4 hours') as recent_tasks,
                (SELECT COUNT(*) FROM claude.features
                 WHERE created_at > NOW() - INTERVAL '4 hours') as recent_features,
                (SELECT COUNT(*) FROM claude.feedback
                 WHERE created_at > NOW() - INTERVAL '4 hours') as recent_feedback
        """)

        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            if isinstance(result, dict):
                return result
            return {
                'recent_tasks': result[0],
                'recent_features': result[1],
                'recent_feedback': result[2]
            }
        return {}
    except Exception:
        return {}


def check_doc_freshness(project_path: Path) -> dict:
    """Check if core docs have been updated recently."""
    warnings = []
    now = datetime.now()

    for doc in CORE_DOCS:
        doc_path = project_path / doc
        if not doc_path.exists():
            warnings.append(f"Missing: {doc}")
            continue

        # Get modification time
        mtime = datetime.fromtimestamp(doc_path.stat().st_mtime)
        age_days = (now - mtime).days

        if doc == 'CLAUDE.md' and age_days > CLAUDE_MD_STALE_DAYS:
            warnings.append(
                f"CLAUDE.md last updated {age_days} days ago (threshold: {CLAUDE_MD_STALE_DAYS} days)"
            )
        elif doc == 'ARCHITECTURE.md' and age_days > ARCHITECTURE_STALE_DAYS:
            warnings.append(
                f"ARCHITECTURE.md last updated {age_days} days ago (threshold: {ARCHITECTURE_STALE_DAYS} days)"
            )

    return warnings


def check_session_docs(project_name: str) -> dict:
    """Check if docs should be updated based on session activity."""
    result = {
        "decision": "allow",
        "warnings": [],
        "suggestions": []
    }

    # Detect project path
    project_path = Path(f"C:/Projects/{project_name}")
    if not project_path.exists():
        return result

    # Check doc freshness
    freshness_warnings = check_doc_freshness(project_path)
    result["warnings"].extend(freshness_warnings)

    # Check session activity
    activity = get_session_activity(project_name)
    if activity:
        significant_changes = (
            activity.get('recent_tasks', 0) > 0 or
            activity.get('recent_features', 0) > 0
        )

        if significant_changes:
            # Check if CLAUDE.md was modified today
            claude_md = project_path / 'CLAUDE.md'
            if claude_md.exists():
                mtime = datetime.fromtimestamp(claude_md.stat().st_mtime)
                if mtime.date() < datetime.now().date():
                    result["warnings"].append(
                        "Significant work done this session but CLAUDE.md not updated today"
                    )
                    result["suggestions"].append(
                        "Update the 'Recent Changes' section in CLAUDE.md"
                    )

    return result


def main():
    # Get project name
    project_name = None

    if '--project' in sys.argv:
        idx = sys.argv.index('--project') + 1
        if idx < len(sys.argv):
            project_name = sys.argv[idx]

    if not project_name:
        project_name = detect_project_from_cwd()

    if not project_name:
        print(json.dumps({
            "decision": "allow",
            "reason": "Could not detect project"
        }))
        return 0

    result = check_session_docs(project_name)

    if result["warnings"]:
        result["decision"] = "warn"
        print(json.dumps(result, indent=2))
        return 1

    result["reason"] = f"Documentation for {project_name} is up to date"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
