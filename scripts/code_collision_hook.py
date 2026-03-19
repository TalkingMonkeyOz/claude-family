#!/usr/bin/env python3
"""
Code Collision Hook - PreToolUse Hook for Symbol Collision Detection

Checks Write/Edit operations against the Code Knowledge Graph to warn
about potential symbol name collisions. Advisory only — never blocks.

Response Format:
    - allow: {"decision": "allow"}
    - allow with warning: {"decision": "allow", "additionalContext": "warning..."}

Author: Claude Family
Created: 2026-03-19
"""

import sys
import os
import io
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

# Force UTF-8 stdout for JSON output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('code_collision_hook')

# Regex patterns for detecting symbol definitions across languages
SYMBOL_PATTERNS = [
    # Python: def name( or class Name(
    (re.compile(r'^\s*(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE), 'function'),
    (re.compile(r'^\s*class\s+(\w+)\s*[\(:]', re.MULTILINE), 'class'),
    # TypeScript/JavaScript: function name(, class Name, const name =
    (re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*[\(<]', re.MULTILINE), 'function'),
    (re.compile(r'^\s*(?:export\s+)?class\s+(\w+)\s*[\{<]', re.MULTILINE), 'class'),
    (re.compile(r'^\s*(?:export\s+)?interface\s+(\w+)\s*[\{<]', re.MULTILINE), 'interface'),
    # C#: public void Name(, class Name
    (re.compile(r'^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?(?:async\s+)?(?:[\w<>\[\]]+\s+)+(\w+)\s*\(', re.MULTILINE), 'method'),
    # Rust: fn name(, struct Name, enum Name
    (re.compile(r'^\s*(?:pub\s+)?fn\s+(\w+)\s*[\(<]', re.MULTILINE), 'function'),
    (re.compile(r'^\s*(?:pub\s+)?struct\s+(\w+)\s*[\{<]', re.MULTILINE), 'class'),
    (re.compile(r'^\s*(?:pub\s+)?enum\s+(\w+)\s*[\{<]', re.MULTILINE), 'enum'),
]

# Skip common names that aren't worth warning about
SKIP_NAMES = {
    'main', 'init', 'new', 'run', 'test', 'setup', 'teardown',
    'get', 'set', 'update', 'delete', 'create', 'list',
    '__init__', '__str__', '__repr__', '__eq__', '__hash__',
    'toString', 'equals', 'hashCode', 'clone',
}


def get_db_connection():
    """Get database connection using config module."""
    try:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from config import get_db_connection as _get_conn
        return _get_conn(strict=False)
    except Exception:
        return None


def extract_new_symbols(content: str, old_content: str = "") -> list[str]:
    """Extract symbol names from new content that don't exist in old content."""
    new_names = set()
    old_names = set()

    for pattern, _ in SYMBOL_PATTERNS:
        for match in pattern.finditer(content):
            name = match.group(1)
            if name not in SKIP_NAMES and len(name) > 2:
                new_names.add(name)
        if old_content:
            for match in pattern.finditer(old_content):
                old_names.add(match.group(1))

    # Only return truly new symbols (not in old content)
    return list(new_names - old_names)


def check_collisions(conn, project_name: str, names: list[str], file_path: str) -> list[dict]:
    """Check if any of the given names collide with existing symbols."""
    if not names:
        return []

    try:
        cur = conn.cursor()
        # Get project_id
        cur.execute(
            "SELECT project_id FROM claude.projects WHERE project_name = %s",
            (project_name,)
        )
        row = cur.fetchone()
        if not row:
            return []
        project_id = row['project_id'] if isinstance(row, dict) else row[0]

        # Check for collisions (exclude the file being edited, exclude private symbols)
        placeholders = ','.join(['%s'] * len(names))
        cur.execute(f"""
            SELECT name, kind, file_path, line_number, visibility
            FROM claude.code_symbols
            WHERE project_id = %s
              AND name IN ({placeholders})
              AND file_path != %s
              AND visibility != 'private'
            ORDER BY name, file_path
        """, [project_id] + names + [file_path])

        results = cur.fetchall()
        if isinstance(results, list) and results and isinstance(results[0], dict):
            return results
        elif results:
            return [{'name': r[0], 'kind': r[1], 'file_path': r[2], 'line_number': r[3], 'visibility': r[4]} for r in results]
        return []
    except Exception as e:
        logger.warning(f"Collision check failed: {e}")
        return []


def main():
    """Main entry point for PreToolUse hook."""
    start_time = time.perf_counter()
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # Only check Write and Edit tools
        if tool_name not in ('Write', 'Edit'):
            print(json.dumps({"decision": "allow"}))
            return

        # Extract file path and content
        file_path = tool_input.get('file_path', '')
        if not file_path:
            print(json.dumps({"decision": "allow"}))
            return

        # Get the content being written/edited
        if tool_name == 'Write':
            content = tool_input.get('content', '')
            old_content = ''
        else:  # Edit
            content = tool_input.get('new_string', '')
            old_content = tool_input.get('old_string', '')

        if not content:
            print(json.dumps({"decision": "allow"}))
            return

        # Extract new symbol names
        new_symbols = extract_new_symbols(content, old_content)
        if not new_symbols:
            total_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Code collision hook: no new symbols in {tool_name} [{total_ms:.1f}ms]")
            print(json.dumps({"decision": "allow"}))
            return

        # Check database for collisions
        conn = get_db_connection()
        if not conn:
            print(json.dumps({"decision": "allow"}))
            return

        try:
            # Determine project from CWD
            project_name = os.path.basename(os.getcwd())

            # Normalize file path for comparison
            norm_path = file_path.replace('\\', '/').replace('C:/Projects/' + project_name + '/', '')

            collisions = check_collisions(conn, project_name, new_symbols, norm_path)
            total_ms = (time.perf_counter() - start_time) * 1000

            if not collisions:
                logger.info(f"Code collision hook: {len(new_symbols)} symbols checked, no collisions [{total_ms:.1f}ms]")
                print(json.dumps({"decision": "allow"}))
                return

            # Format warning
            warnings = []
            for c in collisions[:5]:  # Max 5 warnings
                name = c['name'] if isinstance(c, dict) else c[0]
                kind = c['kind'] if isinstance(c, dict) else c[1]
                fpath = c['file_path'] if isinstance(c, dict) else c[2]
                line = c['line_number'] if isinstance(c, dict) else c[3]
                warnings.append(f"  - {kind} '{name}' already exists in {fpath}:{line}")

            warning_text = "Code Knowledge Graph — Symbol collision warning:\n" + "\n".join(warnings)
            if len(collisions) > 5:
                warning_text += f"\n  ... and {len(collisions) - 5} more"

            logger.info(f"Code collision hook: {len(collisions)} collisions found [{total_ms:.1f}ms]")
            print(json.dumps({
                "decision": "allow",
                "additionalContext": warning_text
            }))

        finally:
            conn.close()

    except Exception as e:
        # Fail open — never block on errors
        logger.error(f"Code collision hook error: {e}")
        print(json.dumps({"decision": "allow"}))


if __name__ == '__main__':
    main()
