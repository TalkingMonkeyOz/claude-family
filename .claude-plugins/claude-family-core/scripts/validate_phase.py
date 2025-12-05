#!/usr/bin/env python3
"""
Pre-tool validation for build_task creation.

Checks that the project is in 'planning' or 'implementation' phase
before allowing build_task creation.

Usage:
    python validate_phase.py <sql>

Exit codes:
    0 = Valid (allow)
    2 = Error (blocking)

Output:
    JSON with decision and reason
"""

import json
import sys
import re

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

ALLOWED_PHASES = ['planning', 'implementation']


def get_db_connection():
    """Get PostgreSQL connection."""
    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(CONN_STR, row_factory=dict_row)
        else:
            return psycopg.connect(CONN_STR, cursor_factory=RealDictCursor)
    except Exception:
        return None


def get_project_phase(feature_id: str) -> tuple:
    """Get project name and phase from feature_id."""
    conn = get_db_connection()
    if not conn:
        return None, None

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.project_name, p.phase
            FROM claude.projects p
            JOIN claude.features f ON p.project_id = f.project_id
            WHERE f.feature_id = %s::uuid
        """, (feature_id,))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            if isinstance(result, dict):
                return result['project_name'], result['phase']
            return result[0], result[1]
        return None, None
    except Exception:
        return None, None


def extract_feature_id(sql: str) -> str:
    """Extract feature_id from INSERT INTO build_tasks SQL."""
    # Look for UUID pattern after feature_id
    uuid_pattern = r"'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'"

    # First check if this is a build_tasks insert
    if 'build_tasks' not in sql.lower():
        return None

    if 'insert' not in sql.lower():
        return None

    # Find all UUIDs in the SQL
    uuids = re.findall(uuid_pattern, sql, re.IGNORECASE)

    # The feature_id is typically the second UUID (after task_id)
    # Or we can look for it explicitly
    feature_match = re.search(r"feature_id[^']*'([^']+)'", sql, re.IGNORECASE)
    if feature_match:
        return feature_match.group(1)

    # If explicit match fails, try second UUID
    if len(uuids) >= 2:
        return uuids[1]

    return None


def validate_phase(sql: str) -> dict:
    """Validate that project is in correct phase for build_task creation."""
    result = {
        "decision": "allow",
        "reason": ""
    }

    # Check if this is a build_tasks INSERT
    sql_lower = sql.lower()
    if 'insert' not in sql_lower or 'build_tasks' not in sql_lower:
        return result  # Not a build_tasks insert, allow

    if not DB_AVAILABLE:
        result["reason"] = "Database not available - allowing operation"
        return result

    # Extract feature_id
    feature_id = extract_feature_id(sql)
    if not feature_id:
        result["reason"] = "Could not extract feature_id - allowing operation"
        return result

    # Get project phase
    project_name, phase = get_project_phase(feature_id)
    if not project_name:
        result["reason"] = "Could not find project for feature - allowing operation"
        return result

    # Validate phase
    if phase not in ALLOWED_PHASES:
        result["decision"] = "block"
        result["reason"] = (
            f"Cannot create build_task: Project '{project_name}' is in '{phase}' phase.\n"
            f"Build tasks can only be created when project is in: {', '.join(ALLOWED_PHASES)}.\n"
            f"Use /phase-advance to move the project to the correct phase first."
        )
    else:
        result["reason"] = f"Project '{project_name}' is in '{phase}' phase - OK"

    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "decision": "allow",
            "reason": "No SQL provided"
        }))
        return 0

    sql = " ".join(sys.argv[1:])

    result = validate_phase(sql)
    print(json.dumps(result, indent=2))

    return 2 if result["decision"] == "block" else 0


if __name__ == "__main__":
    sys.exit(main())
