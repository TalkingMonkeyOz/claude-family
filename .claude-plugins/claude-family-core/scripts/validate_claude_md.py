#!/usr/bin/env python3
"""
Pre-tool validation for CLAUDE.md edits.

Checks:
- CLAUDE.md file size (max 250 lines recommended)
- Required sections present
- Project ID format

Usage:
    python validate_claude_md.py <file_path> [--content <new_content>]

Exit codes:
    0 = Valid
    1 = Warning (non-blocking)
    2 = Error (blocking)
"""

import json
import sys
import os
import re


MAX_LINES = 250
REQUIRED_SECTIONS = [
    'Problem Statement',
    'Work Tracking',
    'Session Protocol',
]


def count_lines(content):
    """Count non-empty lines."""
    return len([l for l in content.split('\n') if l.strip()])


def check_required_sections(content):
    """Check for required sections."""
    missing = []
    for section in REQUIRED_SECTIONS:
        if section.lower() not in content.lower():
            missing.append(section)
    return missing


def check_project_id(content):
    """Check for valid project ID."""
    # Look for UUID pattern in Project ID line
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    project_id_match = re.search(r'Project ID.*?(' + uuid_pattern + ')', content, re.IGNORECASE)
    return project_id_match is not None


def validate_claude_md(file_path, new_content=None):
    """Validate CLAUDE.md file."""
    result = {
        "decision": "allow",
        "reason": "",
        "warnings": [],
        "errors": []
    }

    # Determine content to validate
    if new_content:
        content = new_content
    elif os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        # New file being created
        result["warnings"].append("Creating new CLAUDE.md - ensure it follows governance template")
        print(json.dumps(result))
        return 0

    # Check line count
    line_count = count_lines(content)
    if line_count > MAX_LINES:
        result["warnings"].append(f"CLAUDE.md has {line_count} lines (recommended max: {MAX_LINES})")
        result["warnings"].append("Consider moving detailed content to separate docs")

    # Check required sections
    missing = check_required_sections(content)
    if missing:
        result["warnings"].append(f"Missing recommended sections: {', '.join(missing)}")

    # Check project ID
    if not check_project_id(content):
        result["warnings"].append("No Project ID found - add project_id from claude.projects table")

    # Determine final decision
    if result["errors"]:
        result["decision"] = "block"
        result["reason"] = "; ".join(result["errors"])
        print(json.dumps(result))
        return 2
    elif result["warnings"]:
        result["decision"] = "allow"
        result["reason"] = "Warnings: " + "; ".join(result["warnings"])
        print(json.dumps(result))
        return 1
    else:
        result["decision"] = "allow"
        result["reason"] = "CLAUDE.md validation passed"
        print(json.dumps(result))
        return 0


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "decision": "allow",
            "reason": "No file path provided"
        }))
        return 0

    file_path = sys.argv[1]

    # Check if this is a CLAUDE.md file
    if not file_path.lower().endswith('claude.md'):
        print(json.dumps({
            "decision": "allow",
            "reason": "Not a CLAUDE.md file"
        }))
        return 0

    # Get new content if provided
    new_content = None
    if '--content' in sys.argv:
        content_idx = sys.argv.index('--content') + 1
        if content_idx < len(sys.argv):
            new_content = sys.argv[content_idx]

    return validate_claude_md(file_path, new_content)


if __name__ == "__main__":
    sys.exit(main())
