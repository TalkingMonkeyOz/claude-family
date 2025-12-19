#!/usr/bin/env python3
"""
Sync Obsidian Vault to PostgreSQL Database

Syncs markdown files from an Obsidian vault to the claude.knowledge table.
- Parses YAML frontmatter for metadata
- Extracts markdown content
- Upserts to database (update if exists, insert if new)
- Tracks sync status via 'synced' frontmatter flag

Usage:
    python sync_obsidian_to_db.py [--vault PATH] [--dry-run] [--force]
"""

import argparse
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("Error: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)


# Default vault location
DEFAULT_VAULT = Path(r"C:\Projects\claude-family\knowledge-vault")

# Database connection settings
DB_CONFIG = {
    "host": os.environ.get("CLAUDE_DB_HOST", "localhost"),
    "database": os.environ.get("CLAUDE_DB_NAME", "ai_company_foundation"),
    "user": os.environ.get("CLAUDE_DB_USER", "postgres"),
    "password": os.environ.get("CLAUDE_DB_PASSWORD", "05OX79HNFCjQwhotDjVx"),
}

# Folders to skip
SKIP_FOLDERS = {".obsidian", "_templates", ".git"}

# File patterns to skip
SKIP_PATTERNS = {"_", "."}


def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def parse_markdown_file(file_path: Path) -> Tuple[Optional[Dict], str]:
    """
    Parse a markdown file, extracting YAML frontmatter and content.

    Returns:
        Tuple of (frontmatter dict or None, content string)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        return None, ""

    # Check for YAML frontmatter (starts with ---)
    if not content.startswith("---"):
        # No frontmatter, return content as-is
        return {}, content.strip()

    # Find the closing ---
    parts = content.split("---", 2)
    if len(parts) < 3:
        # Malformed frontmatter
        return {}, content.strip()

    yaml_content = parts[1].strip()
    markdown_content = parts[2].strip()

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(yaml_content)
        if frontmatter is None:
            frontmatter = {}
    except yaml.YAMLError as e:
        print(f"  YAML parse error in {file_path}: {e}")
        frontmatter = {}

    return frontmatter, markdown_content


def extract_summary(content: str, max_length: int = 500) -> str:
    """Extract a summary from markdown content."""
    # Remove headers
    content = re.sub(r"^#+\s+.*$", "", content, flags=re.MULTILINE)
    # Remove code blocks
    content = re.sub(r"```[\s\S]*?```", "", content)
    # Remove inline code
    content = re.sub(r"`[^`]+`", "", content)
    # Remove links but keep text
    content = re.sub(r"\[\[([^\]]+)\]\]", r"\1", content)
    content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
    # Remove images
    content = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", content)
    # Clean up whitespace
    content = re.sub(r"\n\s*\n", "\n", content)
    content = content.strip()

    # Truncate
    if len(content) > max_length:
        content = content[:max_length] + "..."

    return content


def map_type_to_knowledge_type(type_value: str) -> str:
    """Map Obsidian type to database knowledge_type."""
    type_map = {
        "pattern": "pattern",
        "gotcha": "gotcha",
        "api-reference": "api-reference",
        "solution": "solution",
        "learning": "session-learning",
        "template": "template",
        "bug-fix": "bug-fix",
        "best-practice": "best-practice",
    }
    return type_map.get(type_value, "pattern")


def upsert_knowledge(conn, entry: Dict) -> bool:
    """
    Insert or update a knowledge entry.

    Returns True if successful, False otherwise.
    """
    try:
        cur = conn.cursor()

        # Check if entry exists by source or title
        cur.execute(
            "SELECT knowledge_id FROM claude.knowledge WHERE source = %s OR title = %s",
            (entry["source"], entry["title"])
        )
        existing = cur.fetchone()

        if existing:
            # Update existing
            cur.execute("""
                UPDATE claude.knowledge SET
                    title = %s,
                    description = %s,
                    knowledge_category = %s,
                    knowledge_type = %s,
                    confidence_level = %s,
                    applies_to_projects = %s,
                    source = %s,
                    updated_at = NOW()
                WHERE knowledge_id = %s
            """, (
                entry["title"],
                entry["description"],
                entry.get("knowledge_category"),
                entry.get("knowledge_type", "pattern"),
                entry.get("confidence_level", 80),
                entry.get("applies_to_projects", []),
                entry["source"],
                existing[0],
            ))
            action = "Updated"
        else:
            # Insert new
            cur.execute("""
                INSERT INTO claude.knowledge (
                    knowledge_id, title, description, knowledge_category,
                    knowledge_type, confidence_level, applies_to_projects, source, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                str(uuid.uuid4()),
                entry["title"],
                entry["description"],
                entry.get("knowledge_category"),
                entry.get("knowledge_type", "pattern"),
                entry.get("confidence_level", 80),
                entry.get("applies_to_projects", []),
                entry["source"],
            ))
            action = "Inserted"

        conn.commit()
        print(f"  {action}: {entry['title']}")
        return True

    except Exception as e:
        conn.rollback()
        print(f"  Database error: {e}")
        return False


def mark_as_synced(file_path: Path, frontmatter: Dict, content: str):
    """Update the file to mark it as synced."""
    frontmatter["synced"] = True
    frontmatter["synced_at"] = datetime.now().isoformat()

    # Rebuild the file
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    new_content = f"---\n{yaml_str}---\n\n{content}"

    try:
        file_path.write_text(new_content, encoding="utf-8")
    except Exception as e:
        print(f"  Warning: Could not mark as synced: {e}")


def should_skip_file(file_path: Path, vault_path: Path) -> bool:
    """Check if file should be skipped."""
    # Skip files in special folders
    rel_path = file_path.relative_to(vault_path)
    parts = rel_path.parts

    for part in parts:
        if part in SKIP_FOLDERS:
            return True
        for pattern in SKIP_PATTERNS:
            if part.startswith(pattern):
                return True

    return False


def sync_vault(vault_path: Path, dry_run: bool = False, force: bool = False) -> Dict:
    """
    Sync all markdown files in the vault to the database.

    Args:
        vault_path: Path to the Obsidian vault
        dry_run: If True, don't actually sync, just report
        force: If True, sync even if already synced

    Returns:
        Dict with sync statistics
    """
    stats = {
        "total_files": 0,
        "skipped": 0,
        "synced": 0,
        "errors": 0,
        "already_synced": 0,
    }

    if not vault_path.exists():
        print(f"Error: Vault path does not exist: {vault_path}")
        return stats

    # Get database connection
    conn = None
    if not dry_run:
        conn = get_db_connection()
        if not conn:
            print("Error: Could not connect to database")
            return stats

    print(f"Scanning vault: {vault_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("-" * 50)

    # Find all markdown files
    md_files = list(vault_path.rglob("*.md"))
    stats["total_files"] = len(md_files)

    for md_file in md_files:
        # Skip special files/folders
        if should_skip_file(md_file, vault_path):
            stats["skipped"] += 1
            continue

        print(f"\nProcessing: {md_file.relative_to(vault_path)}")

        # Parse the file
        frontmatter, content = parse_markdown_file(md_file)

        if frontmatter is None:
            stats["errors"] += 1
            continue

        # Check if already synced
        if frontmatter.get("synced") and not force:
            print("  Already synced (use --force to resync)")
            stats["already_synced"] += 1
            continue

        # Build knowledge entry
        rel_path = md_file.relative_to(vault_path)
        entry = {
            "title": frontmatter.get("title", md_file.stem),
            "description": content,
            "knowledge_category": frontmatter.get("category"),
            "knowledge_type": map_type_to_knowledge_type(
                frontmatter.get("type", "pattern")
            ),
            "confidence_level": frontmatter.get("confidence", 80),
            "applies_to_projects": frontmatter.get("projects", []),
            "source": f"obsidian:{rel_path}",
        }

        if dry_run:
            print(f"  Would sync: {entry['title']}")
            print(f"    Category: {entry['knowledge_category']}")
            print(f"    Type: {entry['knowledge_type']}")
            stats["synced"] += 1
        else:
            # Upsert to database
            if upsert_knowledge(conn, entry):
                # Mark file as synced
                mark_as_synced(md_file, frontmatter, content)
                stats["synced"] += 1
            else:
                stats["errors"] += 1

    # Close connection
    if conn:
        conn.close()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Sync Obsidian vault to PostgreSQL database"
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=DEFAULT_VAULT,
        help=f"Path to Obsidian vault (default: {DEFAULT_VAULT})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without making changes"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Resync files even if already marked as synced"
    )

    args = parser.parse_args()

    # Run sync
    stats = sync_vault(args.vault, dry_run=args.dry_run, force=args.force)

    # Print summary
    print("\n" + "=" * 50)
    print("SYNC SUMMARY")
    print("=" * 50)
    print(f"Total files found:  {stats['total_files']}")
    print(f"Skipped (special):  {stats['skipped']}")
    print(f"Already synced:     {stats['already_synced']}")
    print(f"Synced this run:    {stats['synced']}")
    print(f"Errors:             {stats['errors']}")

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
