"""F232.P6 — unit tests for scripts/evidence_check.py.

Covers the 5 minimum cases from spec workfile 1e963935 § Test Plan,
plus a few extension cases. Standalone module — no harness or DB.

Run:
    python -m pytest scripts/test_evidence_check.py -v
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evidence_check import VerdictKind, evidence_check, format_nudge


# Spec test case 1 — pure positive label, positive evidence
def test_positive_label_positive_evidence_ok():
    msg = """All tests pass.

```
collected 12 items
12 passed in 0.42s
```
"""
    assert evidence_check(msg).kind == VerdictKind.OK


# Spec test case 2 — positive label in prose, FAIL in code block
def test_positive_label_failed_evidence_contradiction():
    msg = """All tests pass and we are ready to ship.

```
============================== short test summary info ===============================
FAILED tests/test_foo.py::test_bar - AssertionError
3 failed in 1.23s
```
"""
    v = evidence_check(msg)
    assert v.kind == VerdictKind.CONTRADICTION_POSITIVE_LABEL
    assert v.label_hits, "should record which label phrase matched"
    assert v.evidence_hits, "should record which evidence phrase matched"


# Spec test case 3 — negative label in prose, all-passed in code block
def test_negative_label_passed_evidence_contradiction():
    msg = """The deployment failed and the tests are broken.

```
12 passed in 0.42s
exit code 0
```
"""
    v = evidence_check(msg)
    assert v.kind == VerdictKind.CONTRADICTION_NEGATIVE_LABEL


# Spec test case 4 — tutorial-style "should print FAILED" inline, no real evidence
def test_tutorial_style_inline_failed_ok():
    msg = "If the assertion fails, pytest should print `FAILED tests/foo.py`."
    assert evidence_check(msg).kind == VerdictKind.OK


# Spec test case 5 — label without any code-block evidence
def test_label_no_evidence_soft_flag():
    msg = "All tests pass. Ready to ship."
    v = evidence_check(msg)
    assert v.kind == VerdictKind.SOFT_FLAG_LABEL_UNSUPPORTED
    assert v.label_hits, "should record which label phrase matched"


# Extension — empty message
def test_empty_ok():
    assert evidence_check("").kind == VerdictKind.OK


# Extension — pure prose, no labels, no evidence
def test_pure_prose_ok():
    assert evidence_check("Refactored the module to use dataclasses.").kind == VerdictKind.OK


# Extension — multiple positive labels with mixed evidence
def test_multiple_positives_one_failure_contradiction():
    msg = """Successfully ran the suite and verified the deployment.

```
12 passed
1 failed
exit 1
```
"""
    v = evidence_check(msg)
    # Mixed evidence — there's both positive and negative. Spec rule:
    # any negative evidence with a positive label = CONTRADICTION.
    assert v.kind == VerdictKind.CONTRADICTION_POSITIVE_LABEL


# Extension — fenced code containing instructive output (mentioned by spec § Risks)
def test_fenced_instructive_output_with_no_label_ok():
    msg = """Here is what failure output looks like:

```
FAILED tests/foo.py
```
"""
    # No verdict label in prose at all → OK regardless of code-block content.
    assert evidence_check(msg).kind == VerdictKind.OK


# Extension — format_nudge produces a string only on CONTRADICTION
def test_format_nudge_only_on_contradiction():
    msg_contradiction = """All tests pass.

```
1 failed
```
"""
    v = evidence_check(msg_contradiction)
    nudge = format_nudge(v)
    assert nudge is not None and "mismatch" in nudge.lower()

    msg_ok = "Refactored the module."
    assert format_nudge(evidence_check(msg_ok)) is None
