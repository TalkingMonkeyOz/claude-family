#!/usr/bin/env python3
"""
Instruction Matcher - Auto-Apply Hook for Claude Code

This script runs as a PreToolUse hook for Edit/Write operations.
It matches file paths against instruction patterns and injects
relevant coding standards into the context automatically.

Inspired by: github.com/github/awesome-copilot instructions system

Search Order (first match wins for same-named files):
    1. {project}/.claude/instructions/  - Project-specific overrides
    2. ~/.claude/instructions/          - Global shared instructions

Usage:
    Called by Claude Code hooks with file path as argument
    Returns JSON with additionalContext for matching instructions

File Format (.instructions.md):
    ---
    description: 'Guidelines for X'
    applyTo: '**/*.cs'  # glob pattern
    ---

    # Instructions content...

Author: Claude Family
Date: 2025-12-21
Updated: 2025-12-22 - Added global instruction support
"""

import sys
import os
import io
import json
import glob
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import fnmatch

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Instruction file locations (searched in order, first match wins for same-named files)
# Project-specific instructions are added dynamically from CWD in main()
GLOBAL_INSTRUCTION_PATH = Path.home() / ".claude" / "instructions"

# Cache for parsed instructions (per-session)
_instruction_cache: Dict[str, Dict] = {}


def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """
    Parse YAML frontmatter from instruction file.

    Returns:
        Tuple of (frontmatter dict, body content)
    """
    if not content.startswith('---'):
        return {}, content

    # Find end of frontmatter
    end_match = re.search(r'\n---\s*\n', content[3:])
    if not end_match:
        return {}, content

    frontmatter_text = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3:]

    # Simple YAML parsing (key: value)
    frontmatter = {}
    for line in frontmatter_text.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            frontmatter[key] = value

    return frontmatter, body


def load_instructions(base_paths: List[str]) -> List[Dict]:
    """
    Load all instruction files from the given paths.

    Returns:
        List of instruction dicts with keys: path, description, applyTo, content
    """
    instructions = []
    seen_names = set()  # Deduplicate by name (project-specific overrides global)

    for base_path in base_paths:
        if not os.path.isdir(base_path):
            continue

        pattern = os.path.join(base_path, "*.instructions.md")
        for filepath in glob.glob(pattern):
            name = os.path.basename(filepath).replace('.instructions.md', '')

            # Skip if we've already seen this instruction name
            # (project-specific takes precedence since it comes first)
            if name in seen_names:
                continue

            # Check cache
            mtime = os.path.getmtime(filepath)
            cache_key = filepath

            if cache_key in _instruction_cache:
                cached = _instruction_cache[cache_key]
                if cached.get('mtime') == mtime:
                    instructions.append(cached['data'])
                    seen_names.add(name)
                    continue

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                frontmatter, body = parse_frontmatter(content)

                if 'applyTo' not in frontmatter:
                    continue  # Skip instructions without patterns

                instruction = {
                    'path': filepath,
                    'name': name,
                    'description': frontmatter.get('description', ''),
                    'applyTo': frontmatter['applyTo'],
                    'content': body.strip()
                }

                # Cache it
                _instruction_cache[cache_key] = {
                    'mtime': mtime,
                    'data': instruction
                }

                instructions.append(instruction)
                seen_names.add(name)

            except Exception as e:
                print(f"Error loading {filepath}: {e}", file=sys.stderr)
                continue

    return instructions


def matches_pattern(file_path: str, pattern: str) -> bool:
    """
    Check if file path matches the glob pattern.

    Supports:
        - **/*.cs (any .cs file)
        - **/tests/*.spec.ts (test files)
        - *.Designer.cs (designer files in any dir)
        - src/**/*.py (Python files in src)
    """
    # Normalize paths
    file_path = file_path.replace('\\', '/')
    pattern = pattern.replace('\\', '/')

    # Handle ** patterns
    if '**' in pattern:
        # Convert glob pattern to regex
        regex_pattern = pattern.replace('.', r'\.')
        regex_pattern = regex_pattern.replace('**/', '(.*/)?')
        regex_pattern = regex_pattern.replace('**', '.*')
        regex_pattern = regex_pattern.replace('*', '[^/]*')
        regex_pattern = f'^(.*/)?{regex_pattern}$'

        return bool(re.match(regex_pattern, file_path, re.IGNORECASE))
    else:
        # Simple glob match
        return fnmatch.fnmatch(os.path.basename(file_path), pattern)


def find_matching_instructions(file_path: str, instructions: List[Dict]) -> List[Dict]:
    """
    Find all instructions that match the given file path.
    """
    matches = []

    for instruction in instructions:
        patterns = instruction['applyTo']

        # Handle multiple patterns (comma-separated)
        if ',' in patterns:
            pattern_list = [p.strip() for p in patterns.split(',')]
        else:
            pattern_list = [patterns]

        for pattern in pattern_list:
            if matches_pattern(file_path, pattern):
                matches.append(instruction)
                break  # Don't add same instruction twice

    return matches


def build_context(matches: List[Dict]) -> str:
    """
    Build the context injection from matching instructions.
    """
    if not matches:
        return ""

    parts = []
    parts.append("[AUTO-APPLIED INSTRUCTIONS]")
    parts.append(f"The following {len(matches)} instruction(s) apply to this file:\n")

    for instruction in matches:
        parts.append(f"## {instruction['name'].upper()}")
        if instruction['description']:
            parts.append(f"*{instruction['description']}*\n")
        parts.append(instruction['content'])
        parts.append("\n---\n")

    parts.append("**Follow the above instructions when modifying this file.**")

    return "\n".join(parts)


def main():
    """Main entry point for the hook."""
    # Get file path from argument or stdin
    file_path = None

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Try reading from stdin (hook input)
        try:
            hook_input = json.load(sys.stdin)
            # Extract file path from tool input
            tool_input = hook_input.get('toolInput', {})
            file_path = tool_input.get('file_path') or tool_input.get('filePath')
        except:
            pass

    if not file_path or file_path in ('$FILE_PATH', ''):
        # No file path provided, exit silently
        print(json.dumps({}))
        return 0

    # Build search paths: project-specific first (highest priority), then global
    cwd = Path.cwd()
    search_paths = [
        str(cwd / ".claude" / "instructions"),  # Project-specific (highest priority)
        str(GLOBAL_INSTRUCTION_PATH),            # Global ~/.claude/instructions/
    ]

    # Load all instructions
    instructions = load_instructions(search_paths)

    if not instructions:
        print(json.dumps({}))
        return 0

    # Find matches
    matches = find_matching_instructions(file_path, instructions)

    if not matches:
        print(json.dumps({}))
        return 0

    # Build context
    context = build_context(matches)

    # Return hook output
    response = {
        "hookSpecificOutput": {
            "additionalContext": context
        }
    }

    # Log what was matched (for debugging)
    match_names = [m['name'] for m in matches]
    print(f"[instruction_matcher] Applied: {', '.join(match_names)} to {file_path}", file=sys.stderr)

    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    sys.exit(main())
