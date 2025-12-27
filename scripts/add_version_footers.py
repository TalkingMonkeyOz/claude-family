#!/usr/bin/env python3
"""
Add version footers to knowledge vault markdown files.

Adds footer template with version, dates, and location to files missing footers.
Uses git history to determine creation/update dates.
"""

import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

VAULT_PATH = Path("C:/Projects/claude-family/knowledge-vault")

FOOTER_TEMPLATE = """---

**Version**: 1.0
**Created**: {created}
**Updated**: {updated}
**Location**: {location}
"""

def has_footer(content: str) -> bool:
    """Check if file already has version footer."""
    return bool(re.search(r'\*\*Version\*\*:', content))

def get_git_dates(file_path: Path) -> Tuple[str, str]:
    """Get creation and last modified dates from git history."""
    try:
        # Get creation date (first commit that added this file)
        result = subprocess.run(
            ['git', 'log', '--diff-filter=A', '--follow', '--format=%aI', '--', str(file_path)],
            capture_output=True,
            text=True,
            cwd=file_path.parent
        )

        created_raw = result.stdout.strip().split('\n')[-1] if result.stdout.strip() else None
        created = created_raw[:10] if created_raw else None

        # Get last modified date
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%aI', '--', str(file_path)],
            capture_output=True,
            text=True,
            cwd=file_path.parent
        )

        updated_raw = result.stdout.strip()
        updated = updated_raw[:10] if updated_raw else None

        # Fallback to file system dates if git fails
        if not created or not updated:
            stat = file_path.stat()
            fallback_date = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
            created = created or fallback_date
            updated = updated or fallback_date

        return created, updated

    except Exception as e:
        # Fallback to current date if git fails
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"  Warning: Git failed for {file_path.name}, using current date: {e}")
        return today, today

def get_relative_location(file_path: Path) -> str:
    """Get file location relative to vault root."""
    try:
        return str(file_path.relative_to(VAULT_PATH)).replace('\\', '/')
    except ValueError:
        return str(file_path)

def add_footer_to_file(file_path: Path, dry_run: bool = False) -> bool:
    """Add version footer to a single file. Returns True if modified."""
    try:
        # Read current content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if footer already exists
        if has_footer(content):
            return False

        # Get dates from git
        created, updated = get_git_dates(file_path)

        # Get relative location
        location = get_relative_location(file_path)

        # Generate footer
        footer = FOOTER_TEMPLATE.format(
            created=created,
            updated=updated,
            location=location
        )

        # Append footer to content
        new_content = content.rstrip() + '\n' + footer

        if dry_run:
            print(f"  Would add footer: created={created}, updated={updated}")
            return True
        else:
            # Write updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  [OK] Added footer: created={created}, updated={updated}")
            return True

    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        return False

def find_markdown_files() -> list[Path]:
    """Find all markdown files in vault (excluding templates)."""
    files = []
    for md_file in VAULT_PATH.rglob('*.md'):
        # Skip templates
        if '_templates' in str(md_file):
            continue
        files.append(md_file)
    return sorted(files)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Add version footers to vault markdown files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--file', type=str, help='Process single file instead of all files')
    args = parser.parse_args()

    print(f"{'DRY RUN - ' if args.dry_run else ''}Adding version footers to knowledge vault files\n")

    # Get files to process
    if args.file:
        files = [Path(args.file)]
    else:
        files = find_markdown_files()

    print(f"Found {len(files)} markdown files\n")

    # Process each file
    modified_count = 0
    skipped_count = 0

    for file_path in files:
        rel_path = get_relative_location(file_path)
        print(f"Processing: {rel_path}")

        if add_footer_to_file(file_path, dry_run=args.dry_run):
            modified_count += 1
        else:
            print(f"  [SKIP] Skipped (already has footer)")
            skipped_count += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Summary:")
    print(f"  Modified: {modified_count}")
    print(f"  Skipped:  {skipped_count}")
    print(f"  Total:    {len(files)}")

    if args.dry_run:
        print(f"\n[INFO] This was a dry run. Run without --dry-run to apply changes.")

if __name__ == '__main__':
    main()
