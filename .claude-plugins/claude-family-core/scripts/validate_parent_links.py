#!/usr/bin/env python3
"""
Pre-tool validation for parent link requirements.

Prevents orphan creation by requiring:
- build_tasks must have a feature_id
- features must have a project_id
- documents should be linked to a project (warning only)

Usage:
    python validate_parent_links.py <sql>

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

# Parent link requirements
# Format: table_name -> (required_column, error_message, blocking)
PARENT_REQUIREMENTS = {
    'build_tasks': {
        'column': 'feature_id',
        'message': 'build_tasks must have a feature_id to prevent orphans',
        'blocking': True,
        'help': 'First create/find a feature, then link the task to it'
    },
    'features': {
        'column': 'project_id',
        'message': 'features must have a project_id to prevent orphans',
        'blocking': True,
        'help': 'Find the project_id from claude.projects first'
    },
    'documents': {
        'column': 'project_id',
        'message': 'documents should be linked to a project',
        'blocking': False,  # Warning only - some docs may be global
        'help': 'Consider linking to a project or use document_projects table'
    },
    'work_tasks': {
        'column': 'project_id',
        'message': 'work_tasks should have a project_id',
        'blocking': False,
        'help': 'Link task to a project for better organization'
    }
}


def extract_table_from_sql(sql: str) -> str:
    """Extract table name from INSERT SQL."""
    sql_lower = sql.lower().strip()

    # INSERT INTO table_name
    insert_match = re.search(r'insert\s+into\s+(?:claude\.)?(\w+)', sql_lower)
    if insert_match:
        return insert_match.group(1)

    return None


def extract_columns_from_insert(sql: str) -> list:
    """Extract column names from INSERT statement."""
    sql_lower = sql.lower()

    # Match INSERT INTO table (col1, col2, ...) VALUES
    cols_match = re.search(r'insert\s+into\s+\S+\s*\(([^)]+)\)', sql_lower)
    if cols_match:
        cols = [c.strip() for c in cols_match.group(1).split(',')]
        return cols

    return []


def check_column_has_value(sql: str, columns: list, column_name: str) -> bool:
    """Check if a column has a non-null value in the INSERT."""
    sql_lower = sql.lower()

    # Find position of column in column list
    col_lower = column_name.lower()
    if col_lower not in [c.lower() for c in columns]:
        return False

    # Get position
    col_index = None
    for i, c in enumerate(columns):
        if c.lower() == col_lower:
            col_index = i
            break

    if col_index is None:
        return False

    # Extract values
    values_match = re.search(r'values\s*\(([^)]+)\)', sql_lower)
    if not values_match:
        return False

    values = [v.strip() for v in values_match.group(1).split(',')]

    if col_index >= len(values):
        return False

    value = values[col_index]

    # Check if value is NULL or empty
    if value in ('null', "''", '""', ''):
        return False

    return True


def validate_parent_links(sql: str) -> dict:
    """Validate that INSERT has required parent links."""
    result = {
        "decision": "allow",
        "reason": "",
        "warnings": [],
        "errors": [],
        "suggestions": {}
    }

    # Only validate INSERT statements
    sql_lower = sql.lower().strip()
    if not sql_lower.startswith('insert'):
        return result

    # Extract table name
    table_name = extract_table_from_sql(sql)
    if not table_name:
        return result

    # Check if table has parent requirements
    if table_name not in PARENT_REQUIREMENTS:
        return result

    req = PARENT_REQUIREMENTS[table_name]
    columns = extract_columns_from_insert(sql)

    if not columns:
        # Can't parse columns, allow with warning
        result["warnings"].append(
            f"Could not parse INSERT columns for {table_name}"
        )
        return result

    # Check if required column has a value
    has_parent = check_column_has_value(sql, columns, req['column'])

    if not has_parent:
        if req['blocking']:
            result["decision"] = "block"
            result["errors"].append(req['message'])
            result["reason"] = req['message']
            result["suggestions"]["fix"] = req['help']
        else:
            result["warnings"].append(req['message'])
            result["suggestions"]["recommendation"] = req['help']

    return result


def main():
    # Get SQL from args or stdin
    sql = ""
    if len(sys.argv) > 1:
        sql = " ".join(sys.argv[1:])
    else:
        if not sys.stdin.isatty():
            sql = sys.stdin.read()

    if not sql:
        print(json.dumps({
            "decision": "allow",
            "reason": "No SQL provided"
        }))
        return 0

    # Only validate INSERT
    if 'insert' not in sql.lower():
        print(json.dumps({
            "decision": "allow",
            "reason": "Not an INSERT operation"
        }))
        return 0

    # Validate
    result = validate_parent_links(sql)
    print(json.dumps(result, indent=2))

    if result["decision"] == "block":
        return 2
    elif result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
