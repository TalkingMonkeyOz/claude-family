#!/usr/bin/env python3
"""
Standards Validator - PreToolUse Block-and-Correct Hook

Validates file operations (Write/Edit) against coding standards from database
BEFORE execution. Blocks violations with helpful error messages.

Architecture:
    Database (claude.coding_standards)
        ↓
    PreToolUse hook receives tool_input
        ↓
    Validate proposed content
        ↓
    Exit 0 (allow) OR Exit 2 (block with reason)

Block-and-Correct Pattern:
    - Exit code 0: Operation allowed (passes validation)
    - Exit code 2: Operation BLOCKED (Claude sees error, adjusts, retries)
    - stderr: Helpful error message explaining violation

Replaces: instruction_matcher.py (which tried additionalContext injection - didn't work)

Author: Claude Family
Date: 2026-01-02
"""

import sys
import os
import io
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import fnmatch
import re

# Setup file-based logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('standards_validator')

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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

# Default connection string
DEFAULT_CONN_STR = None

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


def get_matching_standards(file_path: str, conn) -> List[Dict]:
    """Get all coding standards that apply to this file path."""
    try:
        cur = conn.cursor()

        # Get all active standards
        cur.execute("""
            SELECT
                standard_id,
                category,
                name,
                applies_to_patterns,
                validation_rules,
                description
            FROM claude.coding_standards
            WHERE active = true
            ORDER BY priority, name
        """)

        all_standards = cur.fetchall()
        standards_list = [dict(s) if PSYCOPG_VERSION == 3 else dict(s) for s in all_standards]

        # Filter to those matching file path
        matches = []
        for standard in standards_list:
            patterns = standard.get('applies_to_patterns', [])
            if matches_any_pattern(file_path, patterns):
                matches.append(standard)

        return matches

    except Exception as e:
        logger.error(f"Failed to get standards: {e}")
        return []


def matches_any_pattern(file_path: str, patterns: List[str]) -> bool:
    """Check if file path matches any of the glob patterns."""
    # Normalize paths
    file_path = file_path.replace('\\', '/')

    for pattern in patterns:
        pattern = pattern.replace('\\', '/')

        # Handle ** patterns (glob-style)
        if '**' in pattern:
            # Convert glob pattern to regex
            regex_pattern = pattern.replace('.', r'\.')
            regex_pattern = regex_pattern.replace('**/', '(.*/)?')
            regex_pattern = regex_pattern.replace('**', '.*')
            regex_pattern = regex_pattern.replace('*', '[^/]*')
            regex_pattern = f'^(.*/)?{regex_pattern}$'

            if re.match(regex_pattern, file_path, re.IGNORECASE):
                return True
        else:
            # Simple filename match
            if fnmatch.fnmatch(os.path.basename(file_path), pattern):
                return True

    return False


def get_file_type(file_path: str) -> str:
    """Determine file type based on path for context-specific validation."""
    base_name = os.path.basename(file_path)

    # Check specific filenames first
    if base_name == 'CLAUDE.md':
        return 'claude-md'
    if base_name == 'PROBLEM_STATEMENT.md':
        return 'problem-statement'
    if base_name == 'ARCHITECTURE.md':
        return 'architecture'
    if base_name == 'README.md':
        return 'readme'

    # Check patterns
    if 'docs/' in file_path or 'TODO' in base_name or 'PLAN' in base_name:
        return 'working'

    if any(folder in file_path.lower() for folder in ['40-procedures', 'procedures', 'sop']):
        return 'procedure'

    if any(folder in file_path.lower() for folder in ['30-patterns', 'patterns']):
        return 'pattern'

    if any(folder in file_path.lower() for folder in ['10-projects', '20-domains', 'knowledge-vault']):
        return 'detailed'

    # Default
    return 'detailed'


def validate_file_size(content: str, file_path: str, validation_rules: Dict) -> Optional[str]:
    """Validate file size against limits. Returns error message if violation."""
    # Count lines
    line_count = content.count('\n') + 1

    # Get limits from validation rules
    max_lines_by_type = validation_rules.get('max_lines_by_type', {})
    default_max = validation_rules.get('default_max_lines', 300)

    # Determine file type and get limit
    file_type = get_file_type(file_path)
    base_name = os.path.basename(file_path)

    # Check type-specific limits
    max_lines = None
    if base_name in max_lines_by_type:
        max_lines = max_lines_by_type[base_name]
    elif file_type in max_lines_by_type:
        max_lines = max_lines_by_type[file_type]
    else:
        max_lines = default_max

    # Check violation
    if line_count > max_lines:
        file_type_display = base_name if base_name in max_lines_by_type else file_type
        return f"""VIOLATION: File exceeds maximum line limit

File: {os.path.basename(file_path)}
Type: {file_type_display}
Current lines: {line_count}
Maximum allowed: {max_lines}

Recommendation:
- Split into smaller files (overview + details)
- Use chunked approach (Part 1, Part 2)
- Link to related docs instead of duplicating content
- For detailed docs: Max 300 lines
- For working files (TODO, plans): Max 100 lines

See: ~/.claude/standards/core/markdown-documentation.md"""

    return None


def validate_content(file_path: str, content: str, standards: List[Dict]) -> Optional[str]:
    """
    Validate content against all matching standards.

    Returns:
        Error message if validation fails, None if passes
    """
    for standard in standards:
        validation_rules = standard.get('validation_rules', {})

        if not validation_rules:
            continue

        # File size validation (most important)
        if 'max_lines_by_type' in validation_rules or 'default_max_lines' in validation_rules:
            error = validate_file_size(content, file_path, validation_rules)
            if error:
                logger.warning(f"File size violation: {file_path} ({content.count(chr(10)) + 1} lines)")
                return error

        # TODO: Add more validation types as needed
        # - forbidden_patterns (check for .unwrap() in Rust, .Result in C#, etc.)
        # - required_patterns (XML comments on public C# APIs, etc.)
        # - naming_checks (interfaces start with I in C#, etc.)

    return None


def block_with_reason(reason: str, exit_code: int = 2):
    """Block the operation with a helpful error message."""
    # Write error to stderr (Claude will see this)
    print(reason, file=sys.stderr)

    # Return permissionDecision block
    response = {
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": reason
        }
    }

    print(json.dumps(response))
    sys.exit(exit_code)


def allow_operation():
    """Allow the operation to proceed."""
    response = {
        "hookSpecificOutput": {
            "permissionDecision": "allow"
        }
    }

    print(json.dumps(response))
    sys.exit(0)


def main():
    """Main entry point for the hook."""
    try:
        logger.info("Standards validator invoked")

        # Read hook input from stdin
        try:
            stdin_data = sys.stdin.read()
            if not stdin_data:
                logger.info("No stdin data, allowing operation")
                allow_operation()

            hook_input = json.loads(stdin_data)
            logger.info(f"Hook input keys: {list(hook_input.keys())}")

        except Exception as e:
            logger.error(f"Failed to parse stdin: {e}", exc_info=True)
            # On parse error, allow operation (don't break workflow)
            allow_operation()

        # Extract tool information
        tool_name = hook_input.get('tool_name') or hook_input.get('toolName')
        tool_input = hook_input.get('tool_input') or hook_input.get('toolInput', {})

        # Only validate Write and Edit operations
        if tool_name not in ['Write', 'Edit']:
            logger.info(f"Skipping validation for tool: {tool_name}")
            allow_operation()

        # Get file path and content
        file_path = (
            tool_input.get('file_path') or
            tool_input.get('filePath') or
            tool_input.get('path')
        )

        if not file_path:
            logger.warning("No file path in tool_input")
            allow_operation()

        # Get proposed content
        content = None
        if tool_name == 'Write':
            content = tool_input.get('content')
        elif tool_name == 'Edit':
            # For Edit, we need to construct full content (simplified - just check new_string)
            content = tool_input.get('new_string')

        if content is None:
            logger.warning(f"No content to validate for {tool_name}")
            allow_operation()

        logger.info(f"Validating {tool_name} operation on {file_path} ({len(content)} chars, {content.count(chr(10)) + 1} lines)")

        # Connect to database
        if not DB_AVAILABLE:
            logger.warning("Database not available, skipping validation")
            allow_operation()

        conn = get_db_connection()
        if not conn:
            logger.warning("Could not connect to database, skipping validation")
            allow_operation()

        try:
            # Get matching standards
            standards = get_matching_standards(file_path, conn)
            logger.info(f"Found {len(standards)} matching standards")

            if not standards:
                # No standards apply, allow operation
                logger.info("No matching standards, allowing operation")
                allow_operation()

            # Validate content
            error = validate_content(file_path, content, standards)

            if error:
                # Validation failed - BLOCK
                logger.warning(f"BLOCKED: {file_path} - {error[:100]}")
                block_with_reason(error)
            else:
                # Validation passed - ALLOW
                standard_names = [s['name'] for s in standards]
                logger.info(f"PASSED: {file_path} validated against {', '.join(standard_names)}")
                allow_operation()

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Validator failed: {e}", exc_info=True)
        # On unexpected error, allow operation (don't break workflow)
        allow_operation()


if __name__ == "__main__":
    main()
