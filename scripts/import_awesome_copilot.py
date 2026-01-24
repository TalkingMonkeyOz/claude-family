#!/usr/bin/env python3
"""
Import awesome-copilot-reference content into claude.skill_content table.

Usage:
    python import_awesome_copilot.py [--dry-run]

Author: Claude Family
Created: 2026-01-17
"""

import os
import sys
import hashlib
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Try to import database libraries
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        PSYCOPG_VERSION = 2
    except ImportError:
        print("ERROR: psycopg or psycopg2 required")
        sys.exit(1)

# Try to load database config
DEFAULT_CONN_STR = None
try:
    sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
    from config import POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
except ImportError:
    pass

# Paths
AWESOME_COPILOT_DIR = Path(r"C:\Projects\claude-family\knowledge-vault\20-Domains\awesome-copilot-reference")

# Priority content to import (high-value files)
PRIORITY_IMPORTS = [
    # Agents - comprehensive expert personas
    ("agents/CSharpExpert.agent.md", "agent", ["csharp", "dotnet", "testing", "async"], ["**/*.cs"]),
    ("agents/arch.agent.md", "agent", ["architecture", "design", "diagram", "nfr", "system"], None),
    ("agents/postgresql-dba.agent.md", "agent", ["postgresql", "database", "sql", "dba"], ["**/*.sql"]),
    ("agents/playwright-tester.agent.md", "agent", ["testing", "playwright", "e2e", "automation"], ["**/*.spec.ts", "**/tests/**"]),
    ("agents/accessibility.agent.md", "agent", ["accessibility", "a11y", "wcag", "aria"], None),
    ("agents/debug.agent.md", "agent", ["debug", "debugging", "troubleshoot", "error"], None),
    ("agents/plan.agent.md", "agent", ["plan", "planning", "task", "breakdown"], None),
    ("agents/implementation-plan.agent.md", "agent", ["implementation", "plan", "steps", "feature"], None),
    ("agents/expert-nextjs-developer.agent.md", "agent", ["nextjs", "react", "frontend", "ssr"], ["**/*.tsx", "**/*.ts"]),
    ("agents/expert-react-frontend-engineer.agent.md", "agent", ["react", "frontend", "component", "hooks"], ["**/*.tsx", "**/*.jsx"]),

    # Instructions - coding standards
    ("instructions/dotnet-wpf.instructions.md", "instruction", ["wpf", "xaml", "mvvm", "gui", "desktop"], ["**/*.xaml", "**/*.cs"]),
    ("instructions/code-review-generic.instructions.md", "instruction", ["review", "code-review", "quality"], None),
    ("instructions/a11y.instructions.md", "instruction", ["accessibility", "a11y", "aria"], None),
    ("instructions/devops-core-principles.instructions.md", "instruction", ["devops", "ci", "cd", "deployment"], None),
    ("instructions/github-actions-ci-cd-best-practices.instructions.md", "instruction", ["github", "actions", "ci", "cd", "workflow"], ["**/.github/**"]),
    ("instructions/containerization-docker-best-practices.instructions.md", "instruction", ["docker", "container", "dockerfile"], ["**/Dockerfile", "**/docker-compose*"]),

    # Prompts - task-specific workflows
    ("prompts/sql-optimization.prompt.md", "prompt", ["sql", "optimization", "performance", "query"], ["**/*.sql"]),
    ("prompts/sql-code-review.prompt.md", "prompt", ["sql", "review", "code-review"], ["**/*.sql"]),
    ("prompts/review-and-refactor.prompt.md", "prompt", ["refactor", "review", "cleanup", "improve"], None),
    ("prompts/conventional-commit.prompt.md", "prompt", ["commit", "git", "conventional"], None),

    # Collections - themed groupings
    ("collections/csharp-dotnet-development.md", "collection", ["csharp", "dotnet", "development"], ["**/*.cs", "**/*.csproj"]),
    ("collections/database-data-management.md", "collection", ["database", "data", "sql", "management"], ["**/*.sql"]),
    ("collections/frontend-web-dev.md", "collection", ["frontend", "web", "react", "typescript"], ["**/*.tsx", "**/*.ts", "**/*.css"]),
    ("collections/testing-automation.md", "collection", ["testing", "automation", "e2e", "unit"], ["**/*test*", "**/*.spec.*"]),
    ("collections/security-best-practices.md", "collection", ["security", "auth", "vulnerability", "owasp"], None),
]


def get_connection():
    """Get database connection."""
    conn_str = os.environ.get('DATABASE_URL', DEFAULT_CONN_STR)
    if not conn_str:
        raise RuntimeError("No database connection string available")

    if PSYCOPG_VERSION == 3:
        return psycopg.connect(conn_str, row_factory=dict_row)
    else:
        return psycopg.connect(conn_str, cursor_factory=RealDictCursor)


def compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def extract_metadata(content: str) -> Tuple[Optional[str], Optional[str], str]:
    """Extract name and description from YAML frontmatter."""
    name = None
    description = None
    body = content

    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2].strip()

            for line in frontmatter.split('\n'):
                if line.startswith('name:'):
                    name = line.split(':', 1)[1].strip().strip('"\'')
                elif line.startswith('description:'):
                    description = line.split(':', 1)[1].strip().strip('"\'')

    return name, description, body


def import_file(
    conn,
    rel_path: str,
    category: str,
    keywords: List[str],
    applies_to: Optional[List[str]],
    dry_run: bool = False
) -> bool:
    """Import a single file to the database."""
    file_path = AWESOME_COPILOT_DIR / rel_path

    if not file_path.exists():
        print(f"  SKIP: {rel_path} (not found)")
        return False

    content = file_path.read_text(encoding='utf-8')
    yaml_name, description, body = extract_metadata(content)

    # Use filename as name if not in YAML
    name = yaml_name or file_path.stem.replace('.agent', '').replace('.instructions', '').replace('.prompt', '')
    content_hash = compute_hash(content)

    if dry_run:
        print(f"  WOULD IMPORT: {name} ({category}) - {len(content)} chars")
        return True

    cur = conn.cursor()

    # Check if already exists
    cur.execute(
        "SELECT content_id, content_hash FROM claude.skill_content WHERE name = %s AND source = %s",
        (name, 'awesome-copilot')
    )
    existing = cur.fetchone()

    if existing:
        if existing['content_hash'] == content_hash:
            print(f"  SKIP: {name} (unchanged)")
            return False
        else:
            # Update existing
            cur.execute("""
                UPDATE claude.skill_content
                SET content = %s, content_hash = %s, description = %s,
                    task_keywords = %s, applies_to = %s, updated_at = NOW()
                WHERE content_id = %s
            """, (content, content_hash, description, keywords, applies_to, existing['content_id']))
            print(f"  UPDATE: {name}")
    else:
        # Insert new
        cur.execute("""
            INSERT INTO claude.skill_content
            (name, description, category, source, task_keywords, applies_to, content, content_hash, priority)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, description, category, 'awesome-copilot', keywords, applies_to, content, content_hash, 70))
        print(f"  INSERT: {name}")

    cur.close()
    return True


def main():
    parser = argparse.ArgumentParser(description='Import awesome-copilot content to database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without doing it')
    args = parser.parse_args()

    print(f"Importing from: {AWESOME_COPILOT_DIR}")
    print(f"Priority imports: {len(PRIORITY_IMPORTS)} files")
    print()

    if args.dry_run:
        print("=== DRY RUN MODE ===\n")

    conn = get_connection()

    imported = 0
    skipped = 0

    try:
        for rel_path, category, keywords, applies_to in PRIORITY_IMPORTS:
            if import_file(conn, rel_path, category, keywords, applies_to, args.dry_run):
                imported += 1
            else:
                skipped += 1

        if not args.dry_run:
            conn.commit()

        print()
        print(f"Done: {imported} imported/updated, {skipped} skipped")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
