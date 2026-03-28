#!/usr/bin/env python3
"""
Pre-tool validation for database writes.

Validates data against claude.column_registry before INSERT/UPDATE operations.
Blocks operations with invalid values and provides valid options.

Usage:
    python validate_db_write.py <tool_name> <sql_or_params>

Exit codes:
    0 = Valid (allow)
    1 = Warning (non-blocking)
    2 = Error (blocking)

Output:
    JSON with decision, reason, and suggestions
"""

import json
import sys
import re
import os

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

# Tables with constrained columns
CONSTRAINED_TABLES = {
    'feedback': ['feedback_type', 'status', 'priority'],
    'features': ['status', 'priority'],
    'build_tasks': ['status', 'priority'],
    'projects': ['status', 'phase', 'priority'],
    'work_tasks': ['status', 'priority'],
    'documents': ['status', 'doc_type'],
}


def get_db_connection():
    """Get PostgreSQL connection from environment."""
    conn_str = os.environ.get('DATABASE_URL')
    if not conn_str:
        return None

    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(conn_str, row_factory=dict_row)
        else:
            return psycopg.connect(conn_str, cursor_factory=RealDictCursor)
    except Exception:
        return None


def get_valid_values(table_name: str, column_name: str) -> list:
    """Get valid values from column_registry."""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT valid_values FROM claude.column_registry
            WHERE table_name = %s AND column_name = %s
        """, (table_name, column_name))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            values = result['valid_values'] if isinstance(result, dict) else result[0]
            return values if values else []
        return []
    except Exception:
        return []


def extract_table_from_sql(sql: str) -> str:
    """Extract table name from INSERT or UPDATE SQL."""
    sql_lower = sql.lower().strip()

    # INSERT INTO table_name
    insert_match = re.search(r'insert\s+into\s+(?:claude\.)?(\w+)', sql_lower)
    if insert_match:
        return insert_match.group(1)

    # UPDATE table_name
    update_match = re.search(r'update\s+(?:claude\.)?(\w+)', sql_lower)
    if update_match:
        return update_match.group(1)

    return None


def extract_column_values(sql: str, table_name: str) -> dict:
    """Extract column-value pairs from SQL."""
    sql_lower = sql.lower()
    values_found = {}

    # For INSERT: look for column names and values
    if 'insert' in sql_lower:
        # Try to match INSERT INTO table (col1, col2) VALUES (val1, val2)
        cols_match = re.search(r'\(([^)]+)\)\s*values\s*\(([^)]+)\)', sql_lower)
        if cols_match:
            cols = [c.strip() for c in cols_match.group(1).split(',')]
            vals = [v.strip().strip("'\"") for v in cols_match.group(2).split(',')]
            for col, val in zip(cols, vals):
                if col in CONSTRAINED_TABLES.get(table_name, []):
                    values_found[col] = val

    # For UPDATE: look for SET column = value
    elif 'update' in sql_lower:
        set_matches = re.findall(r"(\w+)\s*=\s*'([^']*)'", sql)
        for col, val in set_matches:
            col_lower = col.lower()
            if col_lower in CONSTRAINED_TABLES.get(table_name, []):
                values_found[col_lower] = val

    return values_found


def validate_sql(sql: str) -> dict:
    """Validate SQL against column_registry constraints."""
    result = {
        "decision": "allow",
        "reason": "",
        "warnings": [],
        "errors": [],
        "suggestions": {}
    }

    if not DB_AVAILABLE:
        result["warnings"].append("Database not available for validation")
        return result

    # Extract table name
    table_name = extract_table_from_sql(sql)
    if not table_name:
        return result  # Not an INSERT/UPDATE, allow

    if table_name not in CONSTRAINED_TABLES:
        return result  # Table not constrained, allow

    # Extract column values
    col_values = extract_column_values(sql, table_name)
    if not col_values:
        return result  # No constrained columns found, allow

    # Validate each constrained column
    for col, val in col_values.items():
        valid_values = get_valid_values(table_name, col)
        if valid_values and val not in valid_values:
            result["errors"].append(
                f"Invalid value '{val}' for {table_name}.{col}"
            )
            result["suggestions"][f"{table_name}.{col}"] = valid_values

    # Set final decision
    if result["errors"]:
        result["decision"] = "block"
        result["reason"] = "; ".join(result["errors"])
        result["reason"] += f"\n\nValid values: {json.dumps(result['suggestions'], indent=2)}"

    return result


def main():
    # Get input
    if len(sys.argv) < 2:
        print(json.dumps({
            "decision": "allow",
            "reason": "No input provided"
        }))
        return 0

    tool_name = sys.argv[1]

    # Only validate postgres execute_sql calls
    if 'postgres' not in tool_name.lower() and 'execute' not in tool_name.lower():
        print(json.dumps({
            "decision": "allow",
            "reason": f"Not a database operation: {tool_name}"
        }))
        return 0

    # Get SQL from remaining args or stdin
    sql = ""
    if len(sys.argv) > 2:
        sql = " ".join(sys.argv[2:])
    else:
        # Try reading from stdin
        if not sys.stdin.isatty():
            sql = sys.stdin.read()

    if not sql:
        print(json.dumps({
            "decision": "allow",
            "reason": "No SQL provided"
        }))
        return 0

    # Only validate INSERT/UPDATE
    sql_lower = sql.lower()
    if 'insert' not in sql_lower and 'update' not in sql_lower:
        print(json.dumps({
            "decision": "allow",
            "reason": "Not an INSERT/UPDATE operation"
        }))
        return 0

    # Validate
    result = validate_sql(sql)
    print(json.dumps(result, indent=2))

    if result["decision"] == "block":
        return 2
    elif result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
