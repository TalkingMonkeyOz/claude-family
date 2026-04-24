"""FB331 regression: standards_validator path-scoping.

Validates the path-scope helpers introduced in standards_validator.py to fix
the false-positive block on CLAUDE.md / settings.local.json / .mcp.json when
the target file lives outside any registered workspace (e.g. f245-fixtures).

Per the fail-open philosophy: on DB unreachable, the cache becomes empty and
only the `.claude/` path check remains — fixtures still pass.
"""
import os
import sys

SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, SCRIPT_DIR)

import standards_validator as sv  # noqa: E402


def test_is_inside_workspace_with_known_root(monkeypatch):
    monkeypatch.setattr(sv, '_WORKSPACE_ROOTS_CACHE', ['c:/projects/claude-family'])
    assert sv._is_inside_workspace(r'C:\Projects\claude-family\CLAUDE.md') is True
    assert sv._is_inside_workspace(r'C:\Projects\claude-family\scripts\x.py') is True
    assert sv._is_inside_workspace(r'C:\Projects\f245-fixtures\CLAUDE.md') is False
    assert sv._is_inside_workspace(r'C:\Projects\claude-familiar\CLAUDE.md') is False  # prefix trap


def test_is_deployed_output_target_catches_claude_subdir(monkeypatch):
    # Empty workspace cache — isolate the .claude/ heuristic
    monkeypatch.setattr(sv, '_WORKSPACE_ROOTS_CACHE', [])
    # .claude/ subtree: always deployed-output regardless of workspace membership
    assert sv._is_deployed_output_target(r'C:\anywhere\.claude\settings.local.json') is True
    # Outside workspace, outside .claude/: fixture-safe
    assert sv._is_deployed_output_target(r'C:\Projects\f245-fixtures\CLAUDE.md') is False
    assert sv._is_deployed_output_target(r'C:\Projects\f245-fixtures\.mcp.json') is False


def test_is_deployed_output_target_inside_workspace(monkeypatch):
    monkeypatch.setattr(sv, '_WORKSPACE_ROOTS_CACHE', ['c:/projects/claude-family'])
    # Inside workspace root: deployed-output
    assert sv._is_deployed_output_target(r'C:\Projects\claude-family\CLAUDE.md') is True
    # Outside workspace, outside .claude/: fixture-safe
    assert sv._is_deployed_output_target(r'C:\Projects\f245-fixtures\CLAUDE.md') is False


def test_empty_path_never_blocked():
    assert sv._is_inside_workspace('') is False
    assert sv._is_deployed_output_target('') is False
