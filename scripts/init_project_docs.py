#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialize Documentation System for a Project

Sets up the documentation management system for any project:
1. Creates .docs-manifest.json
2. Installs git pre-commit hook
3. Scans existing markdown files
4. Categorizes docs automatically

Usage:
    python scripts/init_project_docs.py /path/to/project
    python scripts/init_project_docs.py C:\Projects\nimbus-user-loader
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

def count_lines(filepath):
    """Count lines in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except Exception as e:
        return -1

def scan_markdown_files(project_root):
    """Find all markdown files in project"""
    md_files = []

    # Root level
    for file in project_root.glob('*.md'):
        if file.is_file():
            md_files.append(file.relative_to(project_root))

    # docs/ subdirectory
    docs_dir = project_root / 'docs'
    if docs_dir.exists():
        for file in docs_dir.rglob('*.md'):
            if file.is_file():
                md_files.append(file.relative_to(project_root))

    return sorted(md_files)

def categorize_file(filename, lines):
    """Auto-categorize a markdown file"""
    filename_str = str(filename).lower()

    # Active core files
    if filename_str == 'claude.md':
        return 'active', {
            'purpose': 'Project context for Claude Code CLI (auto-loaded)',
            'max_lines': 250,
            'current_lines': lines,
            'status': 'active'
        }

    if filename_str == 'readme.md':
        return 'active', {
            'purpose': 'Human-readable project overview',
            'status': 'active',
            'current_lines': lines
        }

    # Session notes
    if 'session' in filename_str or 'completion' in filename_str or 'summary' in filename_str:
        return 'docs_subdirectory', {
            'purpose': 'Session notes or completion report',
            'status': 'session-note',
            'lines': lines,
            'action': 'Consider archiving when project phase completes'
        }

    # Reference docs
    if 'reference' in filename_str or 'guide' in filename_str or 'api' in filename_str:
        return 'docs_subdirectory', {
            'purpose': 'Reference documentation',
            'status': 'reference',
            'lines': lines,
            'action': 'Keep as reference'
        }

    # Large files (>400 lines)
    if lines > 400:
        return 'archive_candidates', {
            'reason': f'Large file ({lines} lines) - consider breaking up or archiving',
            'lines': lines,
            'action': 'Review and possibly archive or split'
        }

    # Default: docs subdirectory
    return 'docs_subdirectory', {
        'purpose': 'Project documentation',
        'status': 'active',
        'lines': lines
    }

def create_manifest(project_root, project_name):
    """Create .docs-manifest.json for project"""
    manifest = {
        'project': project_name,
        'last_updated': datetime.now().strftime('%Y-%m-%d'),
        'documentation_home': str(project_root),
        'active': {},
        'deprecated': {},
        'archive_candidates': {},
        'docs_subdirectory': {},
        'audit_schedule': {
            'last_audit': datetime.now().strftime('%Y-%m-%d'),
            'next_audit': (datetime.now().replace(day=1).replace(month=datetime.now().month % 12 + 1)).strftime('%Y-%m-%d'),
            'frequency': 'monthly',
            'run_command': 'python C:\\Projects\\claude-family\\scripts\\audit_docs.py'
        },
        'rules': {
            'max_lines_CLAUDE_md': 250,
            'deprecated_retention_days': 90,
            'session_notes_archive_days': 30,
            'enforce_via': 'git pre-commit hook + monthly audit'
        },
        'stats': {}
    }

    # Scan and categorize files
    md_files = scan_markdown_files(project_root)

    for md_file in md_files:
        filepath = project_root / md_file
        lines = count_lines(filepath)
        category, info = categorize_file(md_file, lines)

        manifest[category][str(md_file).replace('\\', '/')] = info

    # Calculate stats
    manifest['stats'] = {
        'total_md_files': len(md_files),
        'active_docs': len(manifest['active']),
        'deprecated_docs': len(manifest['deprecated']),
        'archive_candidates': len(manifest['archive_candidates']),
        'docs_subdirectory': len(manifest['docs_subdirectory']),
        'tracked_in_manifest': sum([
            len(manifest['active']),
            len(manifest['deprecated']),
            len(manifest['archive_candidates']),
            len(manifest['docs_subdirectory'])
        ]),
        'last_updated': datetime.now().strftime('%Y-%m-%d')
    }

    return manifest

def install_git_hook(project_root, claude_family_root):
    """Install pre-commit hook from claude-family"""
    hook_source = claude_family_root / 'scripts' / 'pre-commit-hook.sh'
    hook_dest = project_root / '.git' / 'hooks' / 'pre-commit'

    if not hook_source.exists():
        print(f"  {WARN} Hook source not found: {hook_source}")
        return False

    git_dir = project_root / '.git'
    if not git_dir.exists():
        print(f"  {WARN} Not a git repository: {project_root}")
        return False

    # Copy hook
    shutil.copy2(hook_source, hook_dest)

    # Make executable (Git Bash will use it)
    try:
        import stat
        os.chmod(hook_dest, os.stat(hook_dest).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except:
        pass

    print(f"  {CHECK} Installed git pre-commit hook")
    return True

def main():
    parser = argparse.ArgumentParser(description='Initialize documentation system for a project')
    parser.add_argument('project_path', help='Path to project directory')
    args = parser.parse_args()

    project_root = Path(args.project_path).resolve()
    project_name = project_root.name
    claude_family_root = Path(__file__).parent.parent

    print(f"\n{'='*70}")
    print(f"Documentation System Initialization")
    print(f"{'='*70}\n")
    print(f"Project: {project_name}")
    print(f"Path: {project_root}\n")

    if not project_root.exists():
        print(f"{WARN} Project directory does not exist: {project_root}")
        return 1

    # Check if already initialized
    manifest_path = project_root / '.docs-manifest.json'
    if manifest_path.exists():
        print(f"{WARN} Project already has .docs-manifest.json")
        response = input("Overwrite? (y/n): ")
        if response.lower() != 'y':
            print(f"{INFO} Cancelled\n")
            return 0

    # Create manifest
    print(f"{INFO} Scanning markdown files...")
    manifest = create_manifest(project_root, project_name)

    print(f"{CHECK} Found {manifest['stats']['total_md_files']} markdown files")
    print(f"  - Active: {manifest['stats']['active_docs']}")
    print(f"  - Docs: {manifest['stats']['docs_subdirectory']}")
    print(f"  - Archive candidates: {manifest['stats']['archive_candidates']}\n")

    # Save manifest
    print(f"{INFO} Creating .docs-manifest.json...")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
        f.write('\n')
    print(f"{CHECK} Created: {manifest_path}\n")

    # Install git hook
    print(f"{INFO} Installing git pre-commit hook...")
    install_git_hook(project_root, claude_family_root)
    print()

    # Summary
    print(f"{'='*70}")
    print(f"Initialization Complete!")
    print(f"{'='*70}\n")
    print(f"Next steps:")
    print(f"  1. Review .docs-manifest.json and adjust categories")
    print(f"  2. Run audit: python C:\\Projects\\claude-family\\scripts\\audit_docs.py")
    print(f"  3. CLAUDE.md will be enforced at ≤250 lines by git hook")
    print(f"  4. Run monthly audits to keep docs healthy\n")

    return 0

if __name__ == '__main__':
    exit(main())
