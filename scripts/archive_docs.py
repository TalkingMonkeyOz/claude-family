#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archive Documentation Files

Moves archive-candidate files from manifest to docs/archive/YYYY-MM/

Usage:
    python scripts/archive_docs.py --month 2025-10
    python scripts/archive_docs.py --dry-run  # preview only
"""

import json
import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

CHECK = '[OK]'
WARN = '[!!]'
INFO = '[>>]'

def load_manifest(project_root):
    """Load .docs-manifest.json"""
    manifest_path = project_root / '.docs-manifest.json'
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_manifest(project_root, manifest):
    """Save updated manifest"""
    manifest_path = project_root / '.docs-manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
        f.write('\n')

def archive_file(project_root, filename, archive_month, dry_run=False):
    """Archive a single file"""
    source = project_root / filename
    archive_dir = project_root / 'docs' / 'archive' / archive_month
    dest = archive_dir / Path(filename).name

    if not source.exists():
        print(f"   {WARN} Source not found: {filename}")
        return False

    if dry_run:
        print(f"   {INFO} Would move: {filename} -> docs/archive/{archive_month}/")
        return True

    # Create archive directory
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Move file
    shutil.move(str(source), str(dest))
    print(f"   {CHECK} Archived: {filename}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Archive documentation files')
    parser.add_argument('--month', default=datetime.now().strftime('%Y-%m'),
                        help='Archive month (YYYY-MM)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without moving files')
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent

    print(f"\n{'='*70}")
    print(f"Documentation Archival Tool")
    print(f"{'='*70}\n")

    if args.dry_run:
        print(f"{INFO} DRY RUN MODE - No files will be moved\n")

    # Load manifest
    try:
        manifest = load_manifest(project_root)
    except Exception as e:
        print(f"{WARN} Failed to load manifest: {e}")
        return 1

    # Get archive candidates
    candidates = manifest.get('archive_candidates', {})

    if not candidates:
        print(f"{INFO} No archive candidates found\n")
        return 0

    print(f"Found {len(candidates)} files marked for archival:\n")

    archived = []
    failed = []

    for filename, info in candidates.items():
        reason = info.get('reason', 'No reason given')
        print(f"{INFO} {filename}")
        print(f"    Reason: {reason}")

        if archive_file(project_root, filename, args.month, args.dry_run):
            archived.append(filename)
        else:
            failed.append(filename)

    # Update manifest (remove archived files)
    if not args.dry_run and archived:
        print(f"\n{INFO} Updating manifest...")
        for filename in archived:
            del manifest['archive_candidates'][filename]

        # Update stats
        manifest['stats']['archive_candidates'] = len(manifest['archive_candidates'])
        manifest['stats']['last_updated'] = datetime.now().strftime('%Y-%m-%d')

        save_manifest(project_root, manifest)
        print(f"{CHECK} Manifest updated\n")

    # Summary
    print(f"{'='*70}")
    print(f"Summary")
    print(f"{'='*70}\n")
    print(f"Archived: {len(archived)} files")
    if failed:
        print(f"Failed: {len(failed)} files")
    print(f"Archive location: docs/archive/{args.month}/\n")

    if args.dry_run:
        print(f"{INFO} Run without --dry-run to actually move files\n")

    return 0 if not failed else 1

if __name__ == '__main__':
    exit(main())
