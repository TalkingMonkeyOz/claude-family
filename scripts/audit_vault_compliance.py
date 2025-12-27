#!/usr/bin/env python3
"""
Audit knowledge vault files for compliance with documentation standards.

Checks:
1. File size limits (150 lines for Claude Family/, 300 for others)
2. Version footer presence
3. YAML frontmatter completeness (tags, projects)
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

VAULT_PATH = Path("C:/Projects/claude-family/knowledge-vault")

# File size limits by folder
SIZE_LIMITS = {
    'Claude Family': 150,
    'default': 300
}

def get_line_limit(file_path: Path) -> int:
    """Get line limit for file based on folder."""
    rel_path = str(file_path.relative_to(VAULT_PATH))
    if 'Claude Family' in rel_path:
        return SIZE_LIMITS['Claude Family']
    return SIZE_LIMITS['default']

def check_file_size(file_path: Path) -> Tuple[bool, int, int]:
    """Check if file is within size limit. Returns (compliant, actual, limit)."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = len(f.readlines())

    limit = get_line_limit(file_path)
    return lines <= limit, lines, limit

def has_version_footer(content: str) -> bool:
    """Check if file has version footer."""
    return bool(re.search(r'\*\*Version\*\*:', content))

def extract_frontmatter(content: str) -> Dict:
    """Extract YAML frontmatter from content."""
    if not content.startswith('---'):
        return None

    match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not match:
        return None

    # Simple YAML parsing - just check for field presence
    fm_text = match.group(1)
    return {
        'has_tags': 'tags:' in fm_text,
        'has_projects': 'projects:' in fm_text
    }

def audit_file(file_path: Path) -> Dict:
    """Audit a single file for compliance."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    size_ok, actual_lines, limit_lines = check_file_size(file_path)
    has_footer = has_version_footer(content)
    frontmatter = extract_frontmatter(content)

    issues = []
    if not size_ok:
        issues.append(f"Oversized: {actual_lines}/{limit_lines} lines")
    if not has_footer:
        issues.append("Missing footer")
    if frontmatter is None:
        issues.append("Missing YAML frontmatter")
    elif not frontmatter['has_tags']:
        issues.append("Missing 'tags' field")
    elif not frontmatter['has_projects']:
        issues.append("Missing 'projects' field")

    return {
        'path': file_path.relative_to(VAULT_PATH),
        'compliant': len(issues) == 0,
        'issues': issues,
        'lines': actual_lines,
        'limit': limit_lines
    }

def find_markdown_files() -> List[Path]:
    """Find all markdown files in vault (excluding templates)."""
    files = []
    for md_file in VAULT_PATH.rglob('*.md'):
        if '_templates' in str(md_file):
            continue
        files.append(md_file)
    return sorted(files)

def main():
    print("Knowledge Vault Compliance Audit\n")
    print("=" * 80)

    files = find_markdown_files()
    results = []

    for file_path in files:
        result = audit_file(file_path)
        results.append(result)

    # Separate compliant and non-compliant
    compliant = [r for r in results if r['compliant']]
    non_compliant = [r for r in results if not r['compliant']]

    # Print non-compliant files
    if non_compliant:
        print(f"\nNon-Compliant Files ({len(non_compliant)}):\n")
        for r in non_compliant:
            print(f"  {r['path']}")
            for issue in r['issues']:
                print(f"    - {issue}")
            print()

    # Print summary
    print("\n" + "=" * 80)
    print("Summary:\n")
    print(f"  Total files:       {len(results)}")
    print(f"  Compliant:         {len(compliant)} ({len(compliant)/len(results)*100:.1f}%)")
    print(f"  Non-compliant:     {len(non_compliant)} ({len(non_compliant)/len(results)*100:.1f}%)")

    # Breakdown by issue type
    oversized = [r for r in non_compliant if any('Oversized' in i for i in r['issues'])]
    missing_footer = [r for r in non_compliant if 'Missing footer' in r['issues']]
    missing_yaml = [r for r in non_compliant if 'Missing YAML frontmatter' in r['issues']]
    missing_tags = [r for r in non_compliant if "Missing 'tags' field" in r['issues']]
    missing_projects = [r for r in non_compliant if "Missing 'projects' field" in r['issues']]

    print(f"\nIssue Breakdown:")
    print(f"  Oversized files:   {len(oversized)}")
    print(f"  Missing footer:    {len(missing_footer)}")
    print(f"  Missing YAML:      {len(missing_yaml)}")
    print(f"  Missing tags:      {len(missing_tags)}")
    print(f"  Missing projects:  {len(missing_projects)}")

    # Success criteria
    print(f"\nSuccess Criteria:")
    compliance_rate = len(compliant) / len(results) * 100
    print(f"  Compliance rate: {compliance_rate:.1f}% (target: >95%)")
    print(f"  Status: {'PASS' if compliance_rate > 95 else 'FAIL'}")

if __name__ == '__main__':
    main()
