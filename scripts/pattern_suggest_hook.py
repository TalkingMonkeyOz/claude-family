#!/usr/bin/env python3
"""
Pattern Suggestion Hook — PreToolUse for Write|Edit

Checks if the target file path matches any registered pattern's scope_glob
in hal.patterns. If so, suggests using apply_pattern() instead of manual writing.

Response Format:
    - No pattern match: {"decision": "allow"}
    - Pattern match: {"decision": "allow", "additionalContext": "suggestion..."}

Fail-open: Always allows the write, just adds context when patterns exist.

Author: Project HAL (F162 Pattern-Constrained Generation)
Created: 2026-03-29
"""

import sys
import io
import json
import fnmatch

# Force UTF-8 stdout for JSON output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
sys.path.insert(0, os.path.dirname(__file__))
from config import get_database_uri
DB_CONNSTR = get_database_uri()


def get_matching_patterns(file_path: str) -> list[dict]:
    """Query hal.patterns for active patterns whose scope_glob matches file_path."""
    try:
        import psycopg2
        conn = psycopg2.connect(DB_CONNSTR)
        cur = conn.cursor()
        cur.execute(
            "SELECT name, scope_glob, language, framework "
            "FROM hal.patterns WHERE is_active = true"
        )
        rows = cur.fetchall()
        conn.close()

        matches = []
        # Normalize path separators for matching
        normalized = file_path.replace('\\', '/')
        for name, scope_glob, language, framework in rows:
            if scope_glob and fnmatch.fnmatch(normalized, scope_glob):
                matches.append({
                    "name": name,
                    "scope_glob": scope_glob,
                    "language": language or "",
                    "framework": framework or "",
                })
        return matches
    except Exception:
        return []


def extract_file_path(hook_input: dict) -> str:
    """Extract the target file path from the hook input."""
    tool_input = hook_input.get("tool_input", {})
    # Write tool uses "file_path", Edit tool uses "file_path"
    return tool_input.get("file_path", "")


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        file_path = extract_file_path(input_data)

        if not file_path:
            print(json.dumps({"decision": "allow"}))
            return

        matches = get_matching_patterns(file_path)

        if not matches:
            print(json.dumps({"decision": "allow"}))
            return

        # Build suggestion message
        pattern_names = [m["name"] for m in matches]
        names_str = ", ".join(f'"{n}"' for n in pattern_names)
        suggestion = (
            f"[HAL Pattern] This file matches registered pattern(s): {names_str}. "
            f"Consider using apply_pattern({pattern_names[0]!r}, parameters) "
            f"for 100% conformance instead of writing manually. "
            f"Use search_patterns() for details."
        )

        print(json.dumps({
            "decision": "allow",
            "additionalContext": suggestion,
        }))

    except Exception:
        print(json.dumps({"decision": "allow"}))


if __name__ == '__main__':
    main()
