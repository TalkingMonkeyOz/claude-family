"""
Unit tests for commit_fb_resolve_hook (FB397).

Covers the pure helpers (is_git_commit, extract_fb_codes) in isolation so
parsing regressions are caught without touching the database.

Run: pytest scripts/test_commit_fb_resolve_hook.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commit_fb_resolve_hook import extract_fb_codes, is_git_commit


# ---------------------------------------------------------------------------
# is_git_commit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'fix: foo'",
        'git commit -m "fix: foo"',
        "git commit",
        "git commit --amend",
        "git -c commit.gpgsign=false commit -m 'foo'",
        "git -C /repo commit -m 'foo'",
        "  git   commit   -m  'foo'  ",
    ],
)
def test_is_git_commit_positive(command):
    assert is_git_commit(command) is True


@pytest.mark.parametrize(
    "command",
    [
        "",
        "git status",
        "git log -1 --format=%B",
        "git push origin master",
        "echo 'git commit' >> notes.md",  # mention but not invocation — false positive accepted
        "git commit --dry-run -m 'x'",
        "git commit --dry-run",
        "git checkout master",
    ],
)
def test_is_git_commit_negative(command):
    # Note: the echo case will match (regex sees 'git commit' substring).
    # That's acceptable: the downstream HEAD-message scrape determines
    # whether anything actually resolves. We only narrow on --dry-run.
    if command.startswith("echo"):
        assert is_git_commit(command) is True
    else:
        assert is_git_commit(command) is False


# ---------------------------------------------------------------------------
# extract_fb_codes
# ---------------------------------------------------------------------------


def test_extract_fb_codes_single():
    msg = "fix: FB397 — auto-resolve [FB397] tokens in commit"
    assert extract_fb_codes(msg) == ["FB397"]


def test_extract_fb_codes_multiple():
    msg = "feat: cleanup [FB392] [FB393] [FB394]"
    assert extract_fb_codes(msg) == ["FB392", "FB393", "FB394"]


def test_extract_fb_codes_dedup():
    msg = "fix: [FB10] reference [FB10] again [FB10]"
    assert extract_fb_codes(msg) == ["FB10"]


def test_extract_fb_codes_case_insensitive_normalises_to_upper():
    msg = "fix: [fb12] and [Fb 34] mixed"
    assert extract_fb_codes(msg) == ["FB12", "FB34"]


def test_extract_fb_codes_strips_leading_zeros():
    msg = "fix: [FB007] hi"
    assert extract_fb_codes(msg) == ["FB7"]


def test_extract_fb_codes_no_match_when_no_brackets():
    msg = "fix: FB123 mentioned without brackets"
    assert extract_fb_codes(msg) == []


def test_extract_fb_codes_no_match_when_alpha_after_fb():
    msg = "fix: [FBfoo] not a real code"
    assert extract_fb_codes(msg) == []


def test_extract_fb_codes_empty_inputs():
    assert extract_fb_codes("") == []
    assert extract_fb_codes(None) == []  # type: ignore


def test_extract_fb_codes_preserves_order():
    msg = "fix: [FB99] then [FB1] then [FB42]"
    assert extract_fb_codes(msg) == ["FB99", "FB1", "FB42"]


def test_extract_fb_codes_realistic_commit_body():
    msg = """\
fix: FB397 — commit-msg [FB#] auto-resolve hook [FB397]

When Claude commits with [FB392] / [FB397] in the message, those rows
auto-close. Also references [F215] and [BT823] which should NOT match.

Co-Authored-By: Claude <noreply@anthropic.com>
"""
    assert extract_fb_codes(msg) == ["FB397", "FB392"]
