#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Documentation Audit Script

Checks:
1. CLAUDE.md line count (must be ≤250 lines)
2. Files in manifest vs actual files
3. Deprecated docs >90 days old (ready to archive)
4. Archive candidates that should be moved

Run: python scripts/audit_docs.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Simple checkmarks that work on Windows
CHECK = '[OK]'
WARN = '[!!]'
ERROR = '[XX]'
INFO = '[--]'

# Colors for terminal output (optional)
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
END = '\033[0m'

def load_manifest() -> Dict:
    """Load .docs-manifest.json"""
    manifest_path = Path(__file__).parent.parent / '.docs-manifest.json'
    with open(manifest_path, 'r') as f:
        return json.load(f)

def count_lines(filepath: Path) -> int:
    """Count lines in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except Exception as e:
        return -1

def check_claude_md_limit(project_root: Path, max_lines: int = 250) -> Tuple[bool, int]:
    """Check if CLAUDE.md is within line limit"""
    claude_md = project_root / 'CLAUDE.md'
    if not claude_md.exists():
        return False, 0

    lines = count_lines(claude_md)
    return lines <= max_lines, lines

def find_all_md_files(project_root: Path) -> List[Path]:
    """Find all markdown files"""
    md_files = []
    for pattern in ['*.md', 'docs/**/*.md']:
        md_files.extend(project_root.glob(pattern))
    return [f for f in md_files if f.is_file()]

def check_deprecated_age(manifest: Dict) -> List[Dict]:
    """Check which deprecated docs are >90 days old"""
    ready_to_archive = []
    today = datetime.now()

    for name, info in manifest.get('deprecated', {}).items():
        deprecated_date = datetime.strptime(info['deprecated_date'], '%Y-%m-%d')
        days_old = (today - deprecated_date).days

        if days_old > 90:
            ready_to_archive.append({
                'name': name,
                'days_old': days_old,
                'location': info.get('current_location', 'root'),
                'reason': info.get('reason', 'Unknown')
            })

    return ready_to_archive

def main():
    # Use current working directory as project root
    import os
    project_root = Path(os.getcwd())

    print(f"\n{BLUE}{'='*80}{END}")
    print(f"{BLUE}Documentation Audit - {datetime.now().strftime('%Y-%m-%d %H:%M')}{END}")
    print(f"{BLUE}Project: {project_root.name}{END}")
    print(f"{BLUE}{'='*80}{END}\n")

    # Load manifest from current directory
    manifest_path = project_root / '.docs-manifest.json'
    if not manifest_path.exists():
        print(f"{RED}{ERROR}{END} No .docs-manifest.json found in current directory")
        print(f"    Run: python C:\\Projects\\claude-family\\scripts\\init_project_docs.py {project_root}")
        return 1

    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        print(f"{GREEN}{CHECK}{END} Loaded .docs-manifest.json")
    except Exception as e:
        print(f"{RED}{ERROR}{END} Failed to load manifest: {e}")
        return 1
    issues_found = []

    # Check 1: CLAUDE.md line limit
    print(f"\n{BLUE}1. Checking CLAUDE.md line limit...{END}")
    max_lines = manifest['rules']['max_lines_CLAUDE_md']
    within_limit, actual_lines = check_claude_md_limit(project_root, max_lines)

    if within_limit:
        print(f"   {GREEN}{CHECK}{END} CLAUDE.md: {actual_lines}/{max_lines} lines")
    else:
        print(f"   {RED}{ERROR}{END} CLAUDE.md: {actual_lines}/{max_lines} lines (OVER LIMIT!)")
        issues_found.append(f"CLAUDE.md exceeds {max_lines} line limit")

    # Check 2: Manifest accuracy
    print(f"\n{BLUE}2. Checking manifest accuracy...{END}")
    all_md_files = find_all_md_files(project_root)
    total_files = len(all_md_files)

    print(f"   Found {total_files} markdown files")

    # Count files in manifest
    manifest_count = (
        len(manifest.get('active', {})) +
        len(manifest.get('deprecated', {})) +
        len(manifest.get('archive_candidates', {})) +
        len(manifest.get('docs_subdirectory', {})) +
        len(manifest.get('recent_additions', {}))
    )

    if manifest_count == total_files:
        print(f"   {GREEN}{CHECK}{END} Manifest accounts for all {total_files} files")
    else:
        print(f"   {YELLOW}{WARN}{END} Manifest has {manifest_count} files, but found {total_files}")
        print(f"       (Some files may not be in manifest)")

    # Check 3: Deprecated docs ready to archive
    print(f"\n{BLUE}3. Checking deprecated docs age...{END}")
    ready_to_archive = check_deprecated_age(manifest)

    if ready_to_archive:
        print(f"   {YELLOW}{WARN}{END} {len(ready_to_archive)} deprecated docs ready to archive:")
        for doc in ready_to_archive:
            print(f"       - {doc['name']} ({doc['days_old']} days old)")
            print(f"         Reason: {doc['reason']}")
    else:
        print(f"   {GREEN}{CHECK}{END} No deprecated docs >90 days old")

    # Check 4: Archive candidates
    print(f"\n{BLUE}4. Archive candidates...{END}")
    archive_candidates = manifest.get('archive_candidates', {})

    if archive_candidates:
        print(f"   {YELLOW}{WARN}{END} {len(archive_candidates)} files marked for archival:")
        for name, info in list(archive_candidates.items())[:5]:  # Show first 5
            lines = info.get('lines', '?')
            action = info.get('action', 'Review')
            print(f"       - {name} ({lines} lines) - {action}")

        if len(archive_candidates) > 5:
            print(f"       ... and {len(archive_candidates) - 5} more (see manifest)")
    else:
        print(f"   {GREEN}{CHECK}{END} No archive candidates")

    # Check 5: Active docs line counts
    print(f"\n{BLUE}5. Checking active docs line counts...{END}")
    active_docs = manifest.get('active', {})
    large_docs = []

    for name, info in active_docs.items():
        if name.endswith('.md'):
            filepath = project_root / name
            if filepath.exists():
                actual = count_lines(filepath)
                expected = info.get('current_lines', 0)

                if actual != expected:
                    print(f"   {YELLOW}{WARN}{END} {name}: Expected {expected} lines, found {actual} lines")
                    if actual > 300:
                        large_docs.append((name, actual))

    if large_docs:
        print(f"\n   {YELLOW}{WARN}{END} Large active docs (>300 lines):")
        for name, lines in large_docs:
            print(f"       - {name}: {lines} lines")
    else:
        print(f"   {GREEN}{CHECK}{END} All active docs are reasonably sized")

    # Summary
    print(f"\n{BLUE}{'='*80}{END}")
    print(f"{BLUE}Summary{END}")
    print(f"{BLUE}{'='*80}{END}\n")

    print(f"Total markdown files: {total_files}")
    print(f"Active docs: {len(active_docs)}")
    print(f"Deprecated docs: {len(manifest.get('deprecated', {}))}")
    print(f"Archive candidates: {len(archive_candidates)}")
    print(f"Ready to archive (>90 days): {len(ready_to_archive)}")

    if issues_found:
        print(f"\n{RED}Issues Found:{END}")
        for issue in issues_found:
            print(f"  - {issue}")
        return 1
    else:
        print(f"\n{GREEN}{CHECK} No critical issues found{END}")

        if archive_candidates or ready_to_archive:
            print(f"\n{YELLOW}Recommended Actions:{END}")
            if archive_candidates:
                print(f"  - Review and archive {len(archive_candidates)} candidate files")
            if ready_to_archive:
                print(f"  - Archive {len(ready_to_archive)} deprecated docs (>90 days old)")

        return 0

if __name__ == '__main__':
    exit(main())
