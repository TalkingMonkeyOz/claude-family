#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update Line Counts in Documentation Manifest

Scans all markdown files and updates current_lines in .docs-manifest.json

Usage:
    python scripts/update_manifest_lines.py
    python scripts/update_manifest_lines.py --check-only  # report only
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

CHECK = '[OK]'
WARN = '[!!]'
INFO = '[>>]'

def count_lines(filepath):
    """Count lines in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except Exception as e:
        return -1

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

def update_section_lines(project_root, section_name, files_dict):
    """Update line counts for a section"""
    updated = []
    for filename, info in files_dict.items():
        # Handle different path formats
        if filename.startswith('.claude/'):
            filepath = project_root / filename
        elif filename.startswith('docs/'):
            filepath = project_root / filename
        else:
            filepath = project_root / filename

        if filepath.exists() and filename.endswith('.md'):
            actual_lines = count_lines(filepath)
            expected_lines = info.get('current_lines', info.get('lines', 0))

            if actual_lines != expected_lines:
                info['current_lines'] = actual_lines
                if 'lines' in info and 'current_lines' not in info:
                    info['lines'] = actual_lines
                updated.append((filename, expected_lines, actual_lines))

    return updated

def main():
    parser = argparse.ArgumentParser(description='Update manifest line counts')
    parser.add_argument('--check-only', action='store_true',
                        help='Report differences without updating manifest')
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent

    print(f"\n{'='*70}")
    print(f"Manifest Line Count Update Tool")
    print(f"{'='*70}\n")

    if args.check_only:
        print(f"{INFO} CHECK-ONLY MODE - Manifest will not be updated\n")

    # Load manifest
    try:
        manifest = load_manifest(project_root)
    except Exception as e:
        print(f"{WARN} Failed to load manifest: {e}")
        return 1

    all_updated = []

    # Check each section
    sections = [
        ('active', manifest.get('active', {})),
        ('deprecated', manifest.get('deprecated', {})),
        ('slash_commands', manifest.get('slash_commands', {})),
        ('archive_candidates', manifest.get('archive_candidates', {})),
        ('docs_subdirectory', manifest.get('docs_subdirectory', {})),
        ('recent_additions', manifest.get('recent_additions', {}))
    ]

    for section_name, files_dict in sections:
        if files_dict:
            updated = update_section_lines(project_root, section_name, files_dict)
            if updated:
                print(f"\n{section_name}:")
                for filename, expected, actual in updated:
                    print(f"  {WARN} {filename}: {expected} -> {actual} lines")
                all_updated.extend(updated)

    if not all_updated:
        print(f"{CHECK} All line counts are up to date\n")
        return 0

    print(f"\n{'='*70}")
    print(f"Summary: {len(all_updated)} files need line count updates")
    print(f"{'='*70}\n")

    if args.check_only:
        print(f"{INFO} Run without --check-only to update manifest\n")
    else:
        # Save updated manifest
        manifest['stats']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        save_manifest(project_root, manifest)
        print(f"{CHECK} Manifest updated successfully\n")

    return 0

if __name__ == '__main__':
    exit(main())
