#!/usr/bin/env python3
"""
Tests for scripts/lock_enforcement_hook.py (FB392 lock doctrine).

Covers:
  - classify_governed() across all governed file kinds
  - non-governed paths (fixtures, code, docs)
  - bypass via CLAUDE_LOCK_BYPASS env var
  - bypass via "LOCK BYPASS:" comment in content / new_string / Bash
  - Bash redirect detection (`>`, `>>`, `tee`, `cp`, `mv`)
  - end-to-end: subprocess invocation with stdin JSON and JSON stdout

Run:
  cd C:/Projects/claude-family && python -m pytest scripts/test_lock_enforcement_hook.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Make `scripts/` importable.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lock_enforcement_hook as leh  # noqa: E402


# ---------------------------------------------------------------------------
# classify_governed()
# ---------------------------------------------------------------------------


class TestClassifyGoverned:
    def test_global_claude_md(self):
        path = str(Path.home() / ".claude" / "CLAUDE.md")
        assert leh.classify_governed(path) == "global_claude_md"

    def test_project_claude_md_with_dot_claude_sibling(self, tmp_path):
        # Simulate <project>/CLAUDE.md with sibling .claude/ directory
        proj = tmp_path / "myproj"
        proj.mkdir()
        (proj / ".claude").mkdir()
        claude_md = proj / "CLAUDE.md"
        claude_md.write_text("# project")
        assert leh.classify_governed(str(claude_md)) == "project_claude_md"

    def test_project_claude_md_lowercase_with_git(self, tmp_path):
        proj = tmp_path / "lowerproj"
        proj.mkdir()
        (proj / ".git").mkdir()
        cmd = proj / "claude.md"
        cmd.write_text("# lower")
        assert leh.classify_governed(str(cmd)) == "project_claude_md"

    def test_loose_claude_md_outside_project_not_governed(self, tmp_path):
        # A CLAUDE.md sitting in a scratch dir without .claude/ or .git nearby.
        loose = tmp_path / "scratch" / "claude.md"
        loose.parent.mkdir(parents=True)
        loose.write_text("# scratch")
        # Lowercase basename would only match the project-CLAUDE pattern; with
        # neither .claude/ nor .git sibling it must NOT be classified.
        assert leh.classify_governed(str(loose)) is None

    def test_settings_local_json_governed(self):
        path = "C:/Projects/claude-family/.claude/settings.local.json"
        assert leh.classify_governed(path) == "settings_local_json"

    def test_settings_local_json_outside_dot_claude_not_governed(self):
        path = "C:/scratch/settings.local.json"
        assert leh.classify_governed(path) is None

    def test_rule_md_governed(self):
        path = "C:/Projects/foo/.claude/rules/storage-rules.md"
        assert leh.classify_governed(path) == "rule"

    def test_skill_md_governed(self):
        path = "C:/Projects/foo/.claude/skills/database/SKILL.md"
        assert leh.classify_governed(path) == "skill"

    def test_skill_nested_md_governed(self):
        path = "C:/Projects/foo/.claude/skills/database/extras/notes.md"
        assert leh.classify_governed(path) == "skill"

    def test_normal_source_file_not_governed(self):
        path = "C:/Projects/claude-family/scripts/lock_enforcement_hook.py"
        assert leh.classify_governed(path) is None

    def test_normal_markdown_not_governed(self):
        path = "C:/Projects/claude-family/docs/some-note.md"
        assert leh.classify_governed(path) is None

    def test_backslash_path_normalized(self):
        path = r"C:\Projects\foo\.claude\rules\bar.md"
        assert leh.classify_governed(path) == "rule"


# ---------------------------------------------------------------------------
# _comment_bypass()
# ---------------------------------------------------------------------------


class TestCommentBypass:
    def test_hash_comment(self):
        assert leh._comment_bypass("# LOCK BYPASS: shipping fb392") is True

    def test_double_slash_comment(self):
        assert leh._comment_bypass("// LOCK BYPASS: c-style") is True

    def test_html_comment(self):
        assert leh._comment_bypass("<!-- LOCK BYPASS: in html -->") is True

    def test_sql_comment(self):
        assert leh._comment_bypass("-- LOCK BYPASS: sql") is True

    def test_token_at_line_start(self):
        assert leh._comment_bypass("LOCK BYPASS: bare token") is True

    def test_token_in_prose_does_not_trigger(self):
        # Mid-prose mention should not be a bypass.
        assert leh._comment_bypass("This text mentions LOCK BYPASS: incidentally") is False

    def test_no_token(self):
        assert leh._comment_bypass("just normal content") is False

    def test_none_payload(self):
        assert leh._comment_bypass(None) is False

    def test_multiple_payloads_any_match(self):
        assert (
            leh._comment_bypass("normal", None, "# LOCK BYPASS: maybe")
            is True
        )


# ---------------------------------------------------------------------------
# extract_bash_targets()
# ---------------------------------------------------------------------------


class TestExtractBashTargets:
    def test_simple_redirect(self):
        targets = leh.extract_bash_targets("echo hi > /tmp/foo.txt")
        assert "/tmp/foo.txt" in targets

    def test_append_redirect(self):
        targets = leh.extract_bash_targets("echo hi >> /tmp/foo.txt")
        assert "/tmp/foo.txt" in targets

    def test_glued_redirect(self):
        targets = leh.extract_bash_targets("echo hi >/tmp/foo.txt")
        assert "/tmp/foo.txt" in targets

    def test_tee_writes_arg(self):
        targets = leh.extract_bash_targets("echo hi | tee /tmp/foo.txt")
        assert "/tmp/foo.txt" in targets

    def test_tee_append(self):
        targets = leh.extract_bash_targets("echo hi | tee -a /tmp/foo.txt")
        assert "/tmp/foo.txt" in targets

    def test_cp_destination(self):
        targets = leh.extract_bash_targets("cp src.txt /tmp/dest.txt")
        assert "/tmp/dest.txt" in targets

    def test_mv_destination(self):
        targets = leh.extract_bash_targets("mv src.txt /tmp/dest.txt")
        assert "/tmp/dest.txt" in targets

    def test_no_redirect(self):
        targets = leh.extract_bash_targets("ls -la")
        assert targets == []


# ---------------------------------------------------------------------------
# evaluate() — the pure decision core
# ---------------------------------------------------------------------------


def _write_input(file_path: str, content: str = "x") -> dict:
    return {
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
    }


def _edit_input(file_path: str, new_string: str = "x") -> dict:
    return {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": file_path,
            "old_string": "old",
            "new_string": new_string,
        },
    }


def _bash_input(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


class TestEvaluate:
    def test_write_to_governed_rule_blocks(self):
        decision, path, kind = leh.evaluate(
            _write_input("C:/Projects/foo/.claude/rules/x.md"),
            env_bypass=False,
        )
        assert decision == "deny"
        assert kind == "rule"
        assert "rules" in (path or "")

    def test_write_to_skill_blocks(self):
        decision, path, kind = leh.evaluate(
            _write_input("C:/Projects/foo/.claude/skills/x/SKILL.md"),
            env_bypass=False,
        )
        assert decision == "deny"
        assert kind == "skill"

    def test_edit_to_settings_local_json_blocks(self):
        decision, path, kind = leh.evaluate(
            _edit_input("C:/Projects/foo/.claude/settings.local.json"),
            env_bypass=False,
        )
        assert decision == "deny"
        assert kind == "settings_local_json"

    def test_write_to_normal_file_allowed(self):
        decision, path, kind = leh.evaluate(
            _write_input("C:/Projects/foo/src/main.py"),
            env_bypass=False,
        )
        assert decision == "allow"
        assert kind is None

    def test_env_bypass_allows(self):
        decision, _, _ = leh.evaluate(
            _write_input("C:/Projects/foo/.claude/rules/x.md"),
            env_bypass=True,
        )
        assert decision == "allow"

    def test_comment_bypass_in_write_content(self):
        decision, _, _ = leh.evaluate(
            _write_input(
                "C:/Projects/foo/.claude/rules/x.md",
                content="# LOCK BYPASS: emergency hotfix\nrest of file",
            ),
            env_bypass=False,
        )
        assert decision == "allow"

    def test_comment_bypass_in_edit_new_string(self):
        decision, _, _ = leh.evaluate(
            _edit_input(
                "C:/Projects/foo/.claude/skills/foo/SKILL.md",
                new_string="// LOCK BYPASS: surgical patch\nupdated",
            ),
            env_bypass=False,
        )
        assert decision == "allow"

    def test_bash_redirect_to_governed_blocks(self):
        decision, path, kind = leh.evaluate(
            _bash_input(
                "echo data > C:/Projects/foo/.claude/rules/storage-rules.md"
            ),
            env_bypass=False,
        )
        assert decision == "deny"
        assert kind == "rule"

    def test_bash_redirect_to_normal_file_allowed(self):
        decision, _, _ = leh.evaluate(
            _bash_input("echo data > /tmp/scratch.log"),
            env_bypass=False,
        )
        assert decision == "allow"

    def test_bash_with_comment_bypass(self):
        decision, _, _ = leh.evaluate(
            _bash_input(
                "# LOCK BYPASS: data repair\n"
                "echo data > C:/Projects/foo/.claude/rules/x.md"
            ),
            env_bypass=False,
        )
        assert decision == "allow"

    def test_unrelated_tool_allowed(self):
        decision, _, _ = leh.evaluate(
            {"tool_name": "Read", "tool_input": {"file_path": "anything"}},
            env_bypass=False,
        )
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Subprocess integration — real stdin/stdout JSON contract
# ---------------------------------------------------------------------------


HOOK_PATH = HERE / "lock_enforcement_hook.py"


def _run_hook(payload: dict, env_bypass: bool = False) -> dict:
    """Invoke the hook as a subprocess and parse its JSON stdout."""
    env = os.environ.copy()
    if env_bypass:
        env["CLAUDE_LOCK_BYPASS"] = "1"
    else:
        env.pop("CLAUDE_LOCK_BYPASS", None)
    proc = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert proc.returncode == 0, (
        f"Hook exited non-zero: rc={proc.returncode} "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert proc.stdout.strip(), f"Hook produced no stdout. stderr={proc.stderr!r}"
    return json.loads(proc.stdout)


class TestSubprocess:
    def test_subprocess_blocks_governed_write(self):
        out = _run_hook(
            _write_input("C:/Projects/foo/.claude/rules/storage-rules.md")
        )
        decision = out["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        assert "FB392" in reason
        assert "rule_update" in reason

    def test_subprocess_allows_normal_write(self):
        out = _run_hook(_write_input("C:/Projects/foo/src/main.py"))
        assert out["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_subprocess_env_bypass(self):
        out = _run_hook(
            _write_input("C:/Projects/foo/.claude/rules/x.md"),
            env_bypass=True,
        )
        assert out["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_subprocess_comment_bypass(self):
        out = _run_hook(
            _write_input(
                "C:/Projects/foo/.claude/skills/foo/SKILL.md",
                content="# LOCK BYPASS: ad-hoc fix per user\nbody here",
            )
        )
        assert out["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_subprocess_empty_stdin_allows(self):
        proc = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0
        out = json.loads(proc.stdout)
        assert out["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_subprocess_malformed_json_fails_open(self):
        proc = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input="{not json",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0
        out = json.loads(proc.stdout)
        # Fail-open: must allow.
        assert out["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_subprocess_bash_redirect_to_rule_blocks(self):
        out = _run_hook(
            _bash_input(
                "echo overwrite > C:/Projects/foo/.claude/rules/x.md"
            )
        )
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        assert "FB392" in reason


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
