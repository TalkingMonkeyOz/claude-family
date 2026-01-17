#!/usr/bin/env python3
"""
Context Injector Hook - PreToolUse Hook for Database-Driven Context Injection

Uses Claude Code 2.1.9 additionalContext feature to inject relevant standards
and context BEFORE tool execution, so Claude is aware of rules before writing.

Architecture:
    PreToolUse event (tool_name, tool_input)
        ↓
    Query context_rules matching:
        - tool_patterns (e.g., 'Write', 'mcp__postgres__execute_sql')
        - file_patterns (e.g., '**/*.md', '**/*.cs')
        ↓
    Compose additionalContext from:
        - inject_static_context (immediate, ~0ms)
        - inject_standards files (read from disk, ~20ms)
        - inject_vault_query (optional RAG, ~500ms) - TODO
        ↓
    Return: {"decision": "allow", "additionalContext": "..."}

Response Format:
    - allow: {"decision": "allow", "additionalContext": "context to inject"}
    - deny: {"decision": "deny", "reason": "why blocked"}

Called BEFORE standards_validator.py in the hook chain.

Author: Claude Family
Created: 2026-01-17
"""

import sys
import os
import io
import json
import logging
import fnmatch
import time
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple

# Setup file-based logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('context_injector')

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
    sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
    from config import POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
except ImportError:
    pass

# Standards file locations
GLOBAL_STANDARDS_DIR = Path.home() / ".claude" / "standards"
INSTRUCTIONS_DIR = Path.home() / ".claude" / "instructions"
SKILLS_DIR = Path.home() / ".claude" / "skills"


def get_db_connection():
    """Get PostgreSQL connection."""
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


def extract_file_path(tool_name: str, tool_input: Dict[str, Any]) -> Optional[str]:
    """Extract file path from tool input based on tool type."""
    if tool_name in ('Write', 'Edit', 'Read'):
        return tool_input.get('file_path')
    elif tool_name == 'Bash':
        # Try to extract file path from command (best effort)
        cmd = tool_input.get('command', '')
        # Look for common patterns like 'cat file.txt', 'python script.py'
        return None  # Too complex for now, rely on tool_patterns
    elif tool_name.startswith('mcp__postgres__'):
        # SQL tools - check for file patterns in SQL content
        sql = tool_input.get('sql', '')
        return None  # Rely on tool_patterns for SQL tools
    return None


def match_file_pattern(file_path: str, patterns: List[str]) -> bool:
    """Check if file path matches any of the glob patterns."""
    if not file_path or not patterns:
        return False

    file_path = file_path.replace('\\', '/')  # Normalize to forward slashes

    for pattern in patterns:
        pattern = pattern.replace('\\', '/')
        # Handle ** glob patterns
        if '**' in pattern:
            # Convert ** to regex-style matching
            import re
            regex_pattern = pattern.replace('.', r'\.').replace('**', '.*').replace('*', '[^/]*')
            if re.search(regex_pattern, file_path):
                return True
        elif fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(Path(file_path).name, pattern):
            return True

    return False


def get_matching_rules(conn, tool_name: str, file_path: Optional[str]) -> List[Dict]:
    """Query context_rules matching tool and file pattern.

    Matching logic:
    1. If rule has tool_patterns: tool must match
    2. If rule has file_patterns: file must match
    3. Rules with neither tool_patterns nor file_patterns are skipped
    """
    cur = conn.cursor()

    # Query rules that have tool_patterns containing this tool
    # Include skill_content_ids for database-stored comprehensive skills
    cur.execute("""
        SELECT name, tool_patterns, file_patterns, inject_standards,
               inject_static_context, inject_vault_query, priority,
               skill_content_ids
        FROM claude.context_rules
        WHERE active = true
          AND tool_patterns IS NOT NULL
          AND %s = ANY(tool_patterns)
        ORDER BY priority DESC
    """, (tool_name,))

    rules = list(cur.fetchall())
    cur.close()

    # Filter by file pattern if we have a file path
    if file_path:
        filtered = []
        for rule in rules:
            file_patterns = rule.get('file_patterns') or []
            # If rule has file_patterns, file must match; otherwise include it
            if not file_patterns or match_file_pattern(file_path, file_patterns):
                filtered.append(rule)
        return filtered

    return rules


def load_skill_content(conn, content_ids: List[str]) -> List[Tuple[str, str]]:
    """Load skill content from database by IDs.

    Returns list of (name, content) tuples.
    """
    if not content_ids:
        return []

    cur = conn.cursor()
    # Query skill_content by IDs
    cur.execute("""
        SELECT name, content
        FROM claude.skill_content
        WHERE content_id = ANY(%s)
          AND active = true
        ORDER BY priority DESC
    """, (content_ids,))

    results = [(row['name'], row['content']) for row in cur.fetchall()]
    cur.close()
    return results


def load_standard_file(standard_name: str) -> Optional[str]:
    """Load a standard/instruction/skill file by name.

    Search order:
    1. Global standards directory (core/, framework/, language/, pattern/)
    2. Instructions directory (*.instructions.md)
    3. Skills directory (skill-name/00-skill.md or skill-name/*.md)
    """
    # Try global standards directory first
    for subdir in ['core', 'framework', 'language', 'pattern']:
        path = GLOBAL_STANDARDS_DIR / subdir / f"{standard_name}.md"
        if path.exists():
            try:
                return path.read_text(encoding='utf-8')
            except Exception as e:
                logger.warning(f"Failed to read standard {path}: {e}")

    # Try instructions directory
    instructions_path = INSTRUCTIONS_DIR / f"{standard_name}.instructions.md"
    if instructions_path.exists():
        try:
            return instructions_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to read instruction {instructions_path}: {e}")

    # Try skills directory (skill-name/00-skill.md convention)
    skill_dir = SKILLS_DIR / standard_name
    if skill_dir.is_dir():
        # First try the main skill file
        main_skill = skill_dir / "00-skill.md"
        if main_skill.exists():
            try:
                return main_skill.read_text(encoding='utf-8')
            except Exception as e:
                logger.warning(f"Failed to read skill {main_skill}: {e}")

        # Fall back to any .md file in the skill directory
        for md_file in skill_dir.glob("*.md"):
            try:
                return md_file.read_text(encoding='utf-8')
            except Exception as e:
                logger.warning(f"Failed to read skill file {md_file}: {e}")

    return None


def compose_context(rules: List[Dict], conn=None) -> str:
    """Compose additionalContext from matched rules.

    Loads context from:
    1. inject_static_context (immediate text)
    2. inject_standards (files from disk)
    3. skill_content_ids (comprehensive skills from database)
    4. inject_vault_query (RAG - TODO)
    """
    context_parts = []
    loaded_standards = set()
    loaded_skills = set()

    # Maximum content per skill (to avoid context overflow)
    MAX_SKILL_CONTENT = 4000

    for rule in rules:
        rule_name = rule.get('name', 'unknown')

        # 1. Static context (immediate)
        static = rule.get('inject_static_context')
        if static:
            context_parts.append(f"[{rule_name}]\n{static}")

        # 2. Standards files (from disk)
        standards = rule.get('inject_standards') or []
        for std_name in standards:
            if std_name not in loaded_standards:
                content = load_standard_file(std_name)
                if content:
                    # Truncate very long standards
                    if len(content) > 1500:
                        content = content[:1500] + "\n... (truncated)"
                    context_parts.append(f"[Standard: {std_name}]\n{content}")
                    loaded_standards.add(std_name)

        # 3. Database skill content (comprehensive guidelines)
        skill_ids = rule.get('skill_content_ids') or []
        if skill_ids and conn:
            skills = load_skill_content(conn, skill_ids)
            for skill_name, skill_content in skills:
                if skill_name not in loaded_skills:
                    # Truncate to reasonable size
                    if len(skill_content) > MAX_SKILL_CONTENT:
                        skill_content = skill_content[:MAX_SKILL_CONTENT] + "\n\n... (truncated for context limit)"
                    context_parts.append(f"[Skill: {skill_name}]\n{skill_content}")
                    loaded_skills.add(skill_name)
                    logger.info(f"Loaded skill: {skill_name} ({len(skill_content)} chars)")

        # 4. Vault query (TODO: implement RAG call)
        vault_query = rule.get('inject_vault_query')
        if vault_query:
            # TODO: Call vault-rag MCP to get relevant context
            logger.info(f"Would query vault for: {vault_query}")

    if not context_parts:
        return ""

    return "\n\n---\n\n".join(context_parts)


def main():
    """Main entry point for PreToolUse hook."""
    start_time = time.perf_counter()
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        logger.info(f"Context injector called for tool: {tool_name}")

        # Extract file path if available
        file_path = extract_file_path(tool_name, tool_input)

        # Get database connection
        db_start = time.perf_counter()
        conn = get_db_connection()
        db_connect_ms = (time.perf_counter() - db_start) * 1000

        if not conn:
            # No database - allow without injection
            logger.warning("No database connection, skipping context injection")
            print(json.dumps({"decision": "allow"}))
            return

        try:
            # Get matching rules
            query_start = time.perf_counter()
            rules = get_matching_rules(conn, tool_name, file_path)
            query_ms = (time.perf_counter() - query_start) * 1000

            if not rules:
                # No matching rules - allow without injection
                total_ms = (time.perf_counter() - start_time) * 1000
                logger.info(f"No matching rules for {tool_name} / {file_path} [total={total_ms:.1f}ms]")
                print(json.dumps({"decision": "allow"}))
                return

            logger.info(f"Found {len(rules)} matching rules: {[r.get('name') for r in rules]}")

            # Compose context from rules (pass conn for database skill loading)
            compose_start = time.perf_counter()
            context = compose_context(rules, conn)
            compose_ms = (time.perf_counter() - compose_start) * 1000

            total_ms = (time.perf_counter() - start_time) * 1000

            if context:
                logger.info(f"Injecting {len(context)} chars [db={db_connect_ms:.1f}ms, query={query_ms:.1f}ms, compose={compose_ms:.1f}ms, total={total_ms:.1f}ms]")
                print(json.dumps({
                    "decision": "allow",
                    "additionalContext": context
                }))
            else:
                print(json.dumps({"decision": "allow"}))

        finally:
            conn.close()

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        print(json.dumps({"decision": "allow"}))  # Fail open
    except Exception as e:
        logger.error(f"Context injector error: {e}", exc_info=True)
        print(json.dumps({"decision": "allow"}))  # Fail open


if __name__ == "__main__":
    main()
