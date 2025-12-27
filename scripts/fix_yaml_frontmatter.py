#!/usr/bin/env python3
"""
Fix YAML frontmatter in knowledge vault files.

Adds missing 'tags' and 'projects' fields based on folder location and content.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Tuple

VAULT_PATH = Path("C:/Projects/claude-family/knowledge-vault")

# Tag inference rules based on folder
FOLDER_TAG_MAP = {
    'Claude Family': ['claude-family', 'quick-reference'],
    '10-Projects': ['project'],
    '20-Domains/APIs': ['domain-knowledge', 'api'],
    '20-Domains/Database': ['domain-knowledge', 'database'],
    '20-Domains/CSharp': ['domain-knowledge', 'csharp'],
    '20-Domains/WinForms': ['domain-knowledge', 'winforms'],
    '30-Patterns/gotchas': ['pattern', 'gotcha'],
    '30-Patterns/solutions': ['pattern', 'solution'],
    '40-Procedures': ['procedure', 'sop'],
    '_templates': ['template'],
}

# Project inference rules
PROJECT_INFERENCE_RULES = {
    'Claude Family/': ['claude-family'],
    '10-Projects/claude-family/': ['claude-family'],
    '10-Projects/ato-tax-agent/': ['ato-tax-agent'],
    '10-Projects/Claude Family Manager': ['claude-family-manager-v2'],
    '20-Domains/WinForms/': ['claude-family-manager-v2', 'mission-control-web'],
    # Default: empty array (applies to all projects)
}

def extract_frontmatter(content: str) -> Tuple[Optional[Dict], str]:
    """Extract YAML frontmatter and body from markdown content."""
    if not content.startswith('---'):
        return None, content

    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if not match:
        return None, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
        return frontmatter or {}, body
    except yaml.YAMLError:
        return None, content

def infer_tags(file_path: Path) -> List[str]:
    """Infer tags based on file location and name."""
    rel_path = str(file_path.relative_to(VAULT_PATH)).replace('\\', '/')
    tags = []

    # Check folder-based tags
    for folder_pattern, folder_tags in FOLDER_TAG_MAP.items():
        if folder_pattern in rel_path:
            tags.extend(folder_tags)

    # Filename-based tags
    filename_lower = file_path.stem.lower()

    if 'mcp' in filename_lower:
        tags.append('mcp')
    if 'session' in filename_lower:
        tags.append('session')
    if 'hook' in filename_lower:
        tags.append('hooks')
    if 'orchestrator' in filename_lower:
        tags.append('orchestration')
    if 'database' in filename_lower or 'postgres' in filename_lower:
        tags.append('database')
    if 'identity' in filename_lower:
        tags.append('identity')

    # Remove duplicates
    return list(set(tags))

def infer_projects(file_path: Path) -> List[str]:
    """Infer projects based on file location."""
    rel_path = str(file_path.relative_to(VAULT_PATH)).replace('\\', '/')

    # Check specific rules
    for pattern, projects in PROJECT_INFERENCE_RULES.items():
        if pattern in rel_path:
            return projects

    # Default: applies to all projects (empty array)
    return []

def fix_frontmatter(file_path: Path, dry_run: bool = False) -> bool:
    """Fix YAML frontmatter in a file. Returns True if modified."""
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract frontmatter
        frontmatter, body = extract_frontmatter(content)

        # If no frontmatter exists, create it
        if frontmatter is None:
            frontmatter = {}
            print(f"  [WARN] No frontmatter found, creating new")

        modified = False

        # Add missing 'tags' field
        if 'tags' not in frontmatter or not frontmatter['tags']:
            inferred_tags = infer_tags(file_path)
            frontmatter['tags'] = inferred_tags
            print(f"  + tags: {inferred_tags}")
            modified = True

        # Add missing 'projects' field
        if 'projects' not in frontmatter:
            inferred_projects = infer_projects(file_path)
            frontmatter['projects'] = inferred_projects if inferred_projects else []
            print(f"  + projects: {inferred_projects or '(all)'}")
            modified = True

        # If nothing was modified, skip
        if not modified:
            return False

        if dry_run:
            print(f"  Would update frontmatter")
            return True

        # Reconstruct file content
        frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        new_content = f"---\n{frontmatter_yaml}---\n{body}"

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"  [OK] Updated frontmatter")
        return True

    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        return False

def find_markdown_files() -> List[Path]:
    """Find all markdown files in vault."""
    files = []
    for md_file in VAULT_PATH.rglob('*.md'):
        files.append(md_file)
    return sorted(files)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Fix YAML frontmatter in vault files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--file', type=str, help='Process single file')
    args = parser.parse_args()

    print(f"{'DRY RUN - ' if args.dry_run else ''}Fixing YAML frontmatter in vault files\n")

    # Get files
    if args.file:
        files = [Path(args.file)]
    else:
        files = find_markdown_files()

    print(f"Found {len(files)} markdown files\n")

    # Process each file
    modified_count = 0
    skipped_count = 0

    for file_path in files:
        rel_path = file_path.relative_to(VAULT_PATH)
        print(f"Processing: {rel_path}")

        if fix_frontmatter(file_path, dry_run=args.dry_run):
            modified_count += 1
        else:
            print(f"  [SKIP] Skipped (already has tags and projects)")
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
