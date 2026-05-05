#!/usr/bin/env python3
"""F232.P6 — verdict-label vs evidence regex check.

Pure module. No I/O, no hook wiring. Per spec workfile 1e963935 (locked
2026-05-04). Catches the "summary-trust gap" failure mode: agent claims
a positive verdict ("all tests pass") in prose while the same response
contains literal evidence to the contrary ("FAILED tests/foo.py").

Usage:
    from evidence_check import evidence_check, Verdict
    verdict = evidence_check(message_text)
    if verdict.kind == Verdict.CONTRADICTION_POSITIVE_LABEL:
        ...

Stays decoupled from the Stop-hook surface so calibration corpus
labelling can run against this module without harness involvement
(spec sequencing step 3, before step 4 hook wire-up).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class VerdictKind(Enum):
    OK = "ok"
    CONTRADICTION_POSITIVE_LABEL = "contradiction_positive_label"
    CONTRADICTION_NEGATIVE_LABEL = "contradiction_negative_label"
    SOFT_FLAG_LABEL_UNSUPPORTED = "soft_flag_label_unsupported"
    SUGGEST_LABEL = "suggest_label"


@dataclass
class Verdict:
    """Result of evidence_check() — verdict + which patterns hit."""
    kind: VerdictKind
    label_hits: List[str] = field(default_factory=list)
    evidence_hits: List[str] = field(default_factory=list)

    OK = VerdictKind.OK
    CONTRADICTION_POSITIVE_LABEL = VerdictKind.CONTRADICTION_POSITIVE_LABEL
    CONTRADICTION_NEGATIVE_LABEL = VerdictKind.CONTRADICTION_NEGATIVE_LABEL
    SOFT_FLAG_LABEL_UNSUPPORTED = VerdictKind.SOFT_FLAG_LABEL_UNSUPPORTED
    SUGGEST_LABEL = VerdictKind.SUGGEST_LABEL


# ---------------------------------------------------------------------------
# Regex sets (see spec § Verdict-Label Regex Set / Evidence Regex Set)
# ---------------------------------------------------------------------------

LABEL_POSITIVE = [
    r"\ball tests? (pass|passed|passing)\b",
    r"\bdeployment (succeeded|successful|complete)\b",
    r"\bno (issues?|errors?|failures?|problems?)\b",
    r"\b(confirmed|verified|validated|ready (to|for) ship)\b",
    r"\beverything (works|is working|is ready|looks good)\b",
    r"\b(passing|green|✅)\b",
    r"\bsuccessfully\s+(deployed|completed|ran|executed|built)\b",
]

LABEL_NEGATIVE = [
    r"\b(failed|failing|broken|errored)\b",
    r"\b(test|tests) (failed|failing)\b",
    r"\b(error|exception|traceback)\b",
    r"\bnon-?zero exit code\b",
    r"\b(rolled? back|reverted)\b",
]

EVIDENCE_NEGATIVE = [
    r"\bFAILED?\b",
    r"\bERROR\b(?!:\s*0)",
    r"\b\d+ failed",
    r"\bexit (code )?[1-9]\b",
    r"\bAssertionError\b",
    r"\bTraceback \(most recent call last\)",
    r"\bSyntaxError\b",
    r"FAIL +\S+",
    r"\b\d+ failing\b",
]

EVIDENCE_POSITIVE = [
    r"\b\d+ passed\b",
    r"\bPASSED?\b",
    r"\bexit (code )?0\b",
    r"\bSUCCESS\b",
]


# ---------------------------------------------------------------------------
# Prose-vs-code splitting
# ---------------------------------------------------------------------------


_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")


def _extract_code_blocks(message: str) -> str:
    """Return the concatenated text inside fenced code blocks only.

    Inline backtick code is NOT included in evidence text — too noisy
    for output-shape evidence; spec restricts evidence detection to
    fenced blocks where real tool output lives.
    """
    return "\n".join(_FENCED_CODE.findall(message))


def _strip_code(message: str) -> str:
    """Return prose with both fenced and inline code stripped out."""
    no_fences = _FENCED_CODE.sub(" ", message)
    no_inline = _INLINE_CODE.sub(" ", no_fences)
    return no_inline


def _matches(patterns: List[str], text: str) -> List[str]:
    hits: List[str] = []
    for p in patterns:
        if re.search(p, text, re.I):
            hits.append(p)
    return hits


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evidence_check(message_text: str) -> Verdict:
    """Two-pass label-vs-evidence consistency check.

    Spec workfile 1e963935 § Two-Pass Algorithm. Conservatism rule:
    when in doubt prefer SOFT_FLAG over CONTRADICTION — the cost of
    false-CONTRADICTION is annoying nudge spam; missed CONTRADICTION
    lets a hallucination ossify.
    """
    if not message_text:
        return Verdict(VerdictKind.OK)

    prose = _strip_code(message_text)
    code = _extract_code_blocks(message_text)

    label_pos_hits = _matches(LABEL_POSITIVE, prose)
    label_neg_hits = _matches(LABEL_NEGATIVE, prose)
    evidence_pos_hits = _matches(EVIDENCE_POSITIVE, code)
    evidence_neg_hits = _matches(EVIDENCE_NEGATIVE, code)

    if label_pos_hits and evidence_neg_hits:
        return Verdict(
            VerdictKind.CONTRADICTION_POSITIVE_LABEL,
            label_hits=label_pos_hits,
            evidence_hits=evidence_neg_hits,
        )
    if label_neg_hits and evidence_pos_hits:
        return Verdict(
            VerdictKind.CONTRADICTION_NEGATIVE_LABEL,
            label_hits=label_neg_hits,
            evidence_hits=evidence_pos_hits,
        )
    if (label_pos_hits or label_neg_hits) and not (
        evidence_pos_hits or evidence_neg_hits
    ):
        return Verdict(
            VerdictKind.SOFT_FLAG_LABEL_UNSUPPORTED,
            label_hits=label_pos_hits + label_neg_hits,
        )
    return Verdict(VerdictKind.OK)


def format_nudge(verdict: Verdict) -> Optional[str]:
    """Render a nudge string for additionalContext injection on CONTRADICTION."""
    if verdict.kind not in (
        VerdictKind.CONTRADICTION_POSITIVE_LABEL,
        VerdictKind.CONTRADICTION_NEGATIVE_LABEL,
    ):
        return None
    direction = (
        "positive" if verdict.kind == VerdictKind.CONTRADICTION_POSITIVE_LABEL
        else "negative"
    )
    label_phrase = verdict.label_hits[0] if verdict.label_hits else "(unknown)"
    evidence_phrase = (
        verdict.evidence_hits[0] if verdict.evidence_hits else "(unknown)"
    )
    return (
        f"⚠ Verdict-evidence mismatch detected ({direction} label).\n"
        f"Your message includes a label matching `{label_phrase}` but the "
        f"output contains evidence matching `{evidence_phrase}`. Re-check "
        f"before storing this conclusion in memory or committing."
    )
