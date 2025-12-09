#!/usr/bin/env python3
"""
Consistency Check - Scheduled Job

Compares hooks and slash commands across all Claude Family projects.
Reports any drift or differences that need to be addressed.

Usage:
    python check_consistency.py

Author: claude-code-unified
Date: 2025-12-08
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Projects to check
PROJECTS = [
    'claude-family',
    'ATO-Tax-Agent',
    'mission-control-web',
    'nimbus-user-loader'
]

PROJECTS_BASE = Path('C:/Projects')

# Commands that should exist in ALL projects (universal)
UNIVERSAL_COMMANDS = [
    'session-start.md',
    'session-end.md',
    'session-resume.md',
    'broadcast.md',
    'inbox-check.md',
    'team-status.md',
    'feedback-check.md',
    'feedback-create.md',
    'feedback-list.md',
    'check-compliance.md',
    'review-docs.md',
    'review-data.md'
]

# Commands only for claude-family
CLAUDE_FAMILY_ONLY = [
    'project-init.md',
    'retrofit-project.md',
    'phase-advance.md',
    'session-commit.md'
]


@dataclass
class CheckResult:
    project: str
    check_type: str  # 'hook' or 'command'
    item: str
    status: str  # 'ok', 'missing', 'different', 'extra'
    details: Optional[str] = None


def get_file_hash(file_path: Path) -> Optional[str]:
    """Get MD5 hash of file contents."""
    if not file_path.exists():
        return None
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None


def load_hooks(project_path: Path) -> Optional[Dict]:
    """Load hooks.json from a project."""
    hooks_path = project_path / '.claude' / 'hooks.json'
    if not hooks_path.exists():
        return None
    try:
        with open(hooks_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def get_commands(project_path: Path) -> List[str]:
    """Get list of command files in a project."""
    commands_path = project_path / '.claude' / 'commands'
    if not commands_path.exists():
        return []
    return [f.name for f in commands_path.glob('*.md')]


def compare_hooks(source_hooks: Dict, target_hooks: Dict, target_project: str) -> List[CheckResult]:
    """Compare hooks between source (claude-family) and target project."""
    results = []

    source_hook_types = set(source_hooks.get('hooks', {}).keys())
    target_hook_types = set(target_hooks.get('hooks', {}).keys())

    # Check for missing hook types
    for hook_type in source_hook_types:
        if hook_type not in target_hook_types:
            results.append(CheckResult(
                project=target_project,
                check_type='hook',
                item=hook_type,
                status='missing',
                details=f'Hook type {hook_type} exists in claude-family but not in {target_project}'
            ))
        else:
            # Compare the hooks content
            source_config = json.dumps(source_hooks['hooks'][hook_type], sort_keys=True)
            target_config = json.dumps(target_hooks['hooks'][hook_type], sort_keys=True)

            if source_config != target_config:
                results.append(CheckResult(
                    project=target_project,
                    check_type='hook',
                    item=hook_type,
                    status='different',
                    details=f'{hook_type} configuration differs from claude-family'
                ))
            else:
                results.append(CheckResult(
                    project=target_project,
                    check_type='hook',
                    item=hook_type,
                    status='ok'
                ))

    # Check for extra hook types in target
    for hook_type in target_hook_types:
        if hook_type not in source_hook_types:
            results.append(CheckResult(
                project=target_project,
                check_type='hook',
                item=hook_type,
                status='extra',
                details=f'Hook type {hook_type} exists in {target_project} but not in claude-family'
            ))

    return results


def compare_commands(source_path: Path, target_path: Path, target_project: str) -> List[CheckResult]:
    """Compare commands between source (claude-family) and target project."""
    results = []

    source_commands = set(get_commands(source_path))
    target_commands = set(get_commands(target_path))

    # Check universal commands
    for cmd in UNIVERSAL_COMMANDS:
        if cmd not in target_commands:
            results.append(CheckResult(
                project=target_project,
                check_type='command',
                item=cmd,
                status='missing',
                details=f'Universal command {cmd} missing from {target_project}'
            ))
        elif cmd in source_commands:
            # Compare content hash
            source_hash = get_file_hash(source_path / '.claude' / 'commands' / cmd)
            target_hash = get_file_hash(target_path / '.claude' / 'commands' / cmd)

            if source_hash != target_hash:
                results.append(CheckResult(
                    project=target_project,
                    check_type='command',
                    item=cmd,
                    status='different',
                    details=f'{cmd} content differs from claude-family'
                ))
            else:
                results.append(CheckResult(
                    project=target_project,
                    check_type='command',
                    item=cmd,
                    status='ok'
                ))

    # Check for claude-family-only commands in other projects (should not exist)
    if target_project != 'claude-family':
        for cmd in CLAUDE_FAMILY_ONLY:
            if cmd in target_commands:
                results.append(CheckResult(
                    project=target_project,
                    check_type='command',
                    item=cmd,
                    status='extra',
                    details=f'{cmd} should only exist in claude-family'
                ))

    return results


def run_consistency_check() -> List[CheckResult]:
    """Run full consistency check across all projects."""
    all_results = []

    source_path = PROJECTS_BASE / 'claude-family'
    source_hooks = load_hooks(source_path)

    if not source_hooks:
        print("ERROR: Could not load claude-family hooks.json")
        return []

    for project in PROJECTS:
        if project == 'claude-family':
            continue

        project_path = PROJECTS_BASE / project

        if not project_path.exists():
            all_results.append(CheckResult(
                project=project,
                check_type='project',
                item='directory',
                status='missing',
                details=f'Project directory {project_path} does not exist'
            ))
            continue

        # Check hooks
        target_hooks = load_hooks(project_path)
        if target_hooks:
            all_results.extend(compare_hooks(source_hooks, target_hooks, project))
        else:
            all_results.append(CheckResult(
                project=project,
                check_type='hook',
                item='hooks.json',
                status='missing',
                details=f'No hooks.json found in {project}'
            ))

        # Check commands
        all_results.extend(compare_commands(source_path, project_path, project))

    return all_results


def format_results(results: List[CheckResult]) -> str:
    """Format results for output."""
    output = []
    output.append(f"Consistency Check Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    output.append("=" * 60)

    # Group by status
    issues = [r for r in results if r.status != 'ok']
    ok_count = len([r for r in results if r.status == 'ok'])

    output.append(f"\nSummary: {ok_count} OK, {len(issues)} issues")

    if issues:
        output.append("\nIssues Found:")
        output.append("-" * 40)

        # Group by project
        projects_seen = []
        for result in issues:
            if result.project not in projects_seen:
                projects_seen.append(result.project)
                output.append(f"\n[{result.project}]")

            status_icon = {
                'missing': '[-]',
                'different': '[~]',
                'extra': '[+]'
            }.get(result.status, '[?]')

            output.append(f"  {status_icon} {result.check_type}/{result.item}: {result.details}")
    else:
        output.append("\nNo issues found - all projects are consistent!")

    return '\n'.join(output)


def main():
    """Main entry point."""
    print("Running consistency check across Claude Family projects...")
    print()

    results = run_consistency_check()
    report = format_results(results)
    print(report)

    # Return exit code based on issues
    issues = [r for r in results if r.status != 'ok']
    return 0 if not issues else 1


if __name__ == "__main__":
    exit(main())
