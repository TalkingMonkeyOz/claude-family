#!/usr/bin/env python3
"""
Pattern Violation Hook — PostToolUse for Write|Edit

After a file is written/edited, checks if that file has any registered
pattern instances in hal.pattern_instances. If so, compares the current
file content against what the pattern template would generate, and warns
if there's drift.

Response Format:
    - No violations: (empty or no output needed for PostToolUse)
    - Violations found: prints advisory message as additionalContext

Fail-open: Never blocks, only advises.

Author: Project HAL (F162 Pattern-Constrained Generation)
Created: 2026-03-29
"""

import sys
import io
import json

# Force UTF-8 stdout for JSON output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
sys.path.insert(0, os.path.dirname(__file__))
from config import get_database_uri
DB_CONNSTR = get_database_uri()


def check_violations(file_path: str) -> list[dict]:
    """Check if the file has pattern instances that may have drifted."""
    try:
        import psycopg2
        conn = psycopg2.connect(DB_CONNSTR)
        cur = conn.cursor()

        # Normalize path for matching
        normalized = file_path.replace('\\', '/')

        # Find pattern instances for this file
        cur.execute(
            "SELECT pi.instance_id, p.name, pi.is_customized, pi.generated_code "
            "FROM hal.pattern_instances pi "
            "JOIN hal.patterns p ON pi.pattern_id = p.pattern_id "
            "WHERE pi.file_path = %s OR pi.file_path = %s",
            (file_path, normalized)
        )
        instances = cur.fetchall()
        conn.close()

        if not instances:
            return []

        violations = []
        for instance_id, pattern_name, is_customized, generated_code in instances:
            if is_customized:
                violations.append({
                    "pattern": pattern_name,
                    "issue": "customized",
                    "message": f"Instance of '{pattern_name}' is marked as customized — manual edits may diverge further from template",
                })
            elif generated_code:
                # Read current file content to compare
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        current = f.read()
                    if generated_code.strip() not in current:
                        violations.append({
                            "pattern": pattern_name,
                            "issue": "drift",
                            "message": f"File content no longer matches pattern '{pattern_name}' template output. Run detect_violations('{file_path}') for details.",
                        })
                except (FileNotFoundError, PermissionError):
                    pass

        return violations
    except Exception:
        return []


def extract_file_path(hook_input: dict) -> str:
    """Extract the target file path from the hook input."""
    tool_input = hook_input.get("tool_input", {})
    return tool_input.get("file_path", "")


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        file_path = extract_file_path(input_data)

        if not file_path:
            return

        violations = check_violations(file_path)

        if not violations:
            return

        # Build advisory message
        messages = [v["message"] for v in violations]
        advisory = "[HAL Pattern Check] " + " | ".join(messages)

        print(json.dumps({
            "additionalContext": advisory,
        }))

    except Exception:
        pass


if __name__ == '__main__':
    main()
