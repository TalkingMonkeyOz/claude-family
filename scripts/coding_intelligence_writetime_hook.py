#!/usr/bin/env python3
"""F232.P3 — PreToolUse(Edit|Write) coding intelligence hook.

Composes additionalContext from two sources, gated by anti-pollution
invariants from `coding_intelligence_writetime.bpmn`:

  TIME axis  — claude.knowledge rows whose kg_links anchor to symbols
               or files in the edit target.
  SPACE axis — hal-semantic-engine.overlay_get_full_context for the
               same symbols (intent, invariants, concerns, similar
               siblings).

Output shape (Claude Code 2.1.9 PreToolUse):
    {"decision": "allow", "additionalContext": "..."}
    {"decision": "allow"}                              (no context)

Fail-open on every error path. Latency budget <100ms p95.

Aggregator client is dependency-injected so the same code runs against
the live hal MCP, an in-process mock, or in disabled mode (no overlay
calls — TIME axis only). Mode controlled by F232_AGGREGATOR_MODE env
var: 'live' | 'mock' | 'disabled' (default).
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Local imports (config + cache)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import detect_psycopg, get_db_connection
from overlay_resolved_symbol_cache import ResolvedSymbolCache

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("f232_writetime")

if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

INJECTION_HARD_CAP_TOKENS = 2000
INJECTION_DEFAULT_BUDGET = 1500
DEFAULT_LATENCY_BUDGET_MS = 100
MEMORIES_PER_QUERY = 5
SIMILAR_SIBLINGS_K = 3

# Files we never bother indexing.
UNINDEXABLE_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".lock", ".sqlite", ".db",
    ".min.js", ".min.css", ".woff", ".woff2", ".ttf",
}


# ---------------------------------------------------------------------------
# Aggregator client factory (dependency injection point)
# ---------------------------------------------------------------------------


def _disabled_aggregator(**_: Any) -> Dict[str, Any]:
    """No-op aggregator — returns empty payload."""
    return {
        "resolved_symbol_id": None,
        "intent": None,
        "relationships": [],
        "invariants": [],
        "concerns": [],
        "purpose_similar_siblings": [],
        "coverage_status": "unannotated",
        "has_intent_drift": None,
        "has_intent_drift_basis": None,
    }


def _mock_aggregator(**kwargs: Any) -> Dict[str, Any]:
    """Smoke-test mock — returns a synthetic annotated payload."""
    qn = kwargs.get("qualified_name") or "mock.symbol"
    return {
        "resolved_symbol_id": f"mock::{qn}",
        "intent": {"purpose": f"mock intent for {qn}"},
        "relationships": [],
        "invariants": ["mock invariant"],
        "concerns": ["mock"],
        "purpose_similar_siblings": [],
        "coverage_status": "annotated",
        "has_intent_drift": False,
        "has_intent_drift_basis": "extracted_at_vs_mtime",
    }


_HAL_PATH = os.environ.get("HAL_REPO_PATH", "C:/Projects/project-hal")
_LIVE_FN: Optional[Callable] = None


def _load_live_aggregator() -> Callable:
    """Lazy import of hal-semantic-engine.overlay_get_full_context.

    Wire-path verified 2026-05-04 against hal commit f60b4ce (task #466
    stub: full v1.1 envelope, validation, project_mismatch detection,
    UUID resolution path). Direct Python import — same process, no MCP
    JSON-RPC overhead.
    """
    global _LIVE_FN
    if _LIVE_FN is not None:
        return _LIVE_FN
    if not os.environ.get("DATABASE_URI"):
        try:
            from config import get_database_uri
            os.environ["DATABASE_URI"] = get_database_uri()
        except Exception:
            pass
    if _HAL_PATH not in sys.path:
        sys.path.insert(0, _HAL_PATH)
    from src.core.server import overlay_get_full_context as fn  # type: ignore
    _LIVE_FN = fn
    return fn


def _live_aggregator(**kwargs: Any) -> Dict[str, Any]:
    """Live client — calls hal-semantic-engine.overlay_get_full_context."""
    fn = _load_live_aggregator()
    raw = fn(**{k: v for k, v in kwargs.items() if v is not None})
    if isinstance(raw, str):
        return json.loads(raw)
    return raw  # already a dict (defensive)


def get_aggregator() -> Callable[..., Dict[str, Any]]:
    """Return the configured aggregator callable based on env."""
    mode = (os.environ.get("F232_AGGREGATOR_MODE") or "disabled").lower()
    if mode == "live":
        return _live_aggregator
    if mode == "mock":
        return _mock_aggregator
    return _disabled_aggregator


# ---------------------------------------------------------------------------
# Pure helpers (testable without DB or hal MCP)
# ---------------------------------------------------------------------------


def is_indexable(file_path: Optional[str]) -> bool:
    if not file_path:
        return False
    p = Path(file_path).name.lower()
    for suffix in UNINDEXABLE_SUFFIXES:
        if p.endswith(suffix):
            return False
    return True


def extract_target(input_data: Dict[str, Any]) -> Dict[str, Any]:
    tool_name = input_data.get("tool_name") or ""
    tool_input = input_data.get("tool_input") or {}
    file_path = tool_input.get("file_path") if tool_name in ("Edit", "Write") else None
    project = (
        os.environ.get("CLAUDE_PROJECT_NAME")
        or os.environ.get("HAL_PROJECT_NAME")
        or "claude-family"
    )
    return {"tool_name": tool_name, "file_path": file_path, "project": project}


def compose_injection(
    *,
    file_path: str,
    memories: List[Dict[str, Any]],
    overlay_results: List[Dict[str, Any]],
    similar_siblings: List[Dict[str, Any]],
    budget_tokens: int = INJECTION_DEFAULT_BUDGET,
) -> str:
    """Compose the additionalContext markdown. Hard cap honoured."""
    if not memories and not overlay_results and not similar_siblings:
        return ""

    lines: List[str] = [f"## Editing context for `{file_path}`"]

    if overlay_results:
        first = overlay_results[0]
        intent = (first.get("intent") or {}).get("purpose")
        if intent:
            lines.append(f"**Intent**: {intent}")
        invariants = first.get("invariants") or []
        if invariants:
            lines.append("**Invariants in scope**: " + "; ".join(invariants[:5]))
        concerns = first.get("concerns") or []
        if concerns:
            lines.append("**Concerns**: " + ", ".join(concerns[:5]))

    if memories:
        lines.append(f"**Patterns previously used here** ({len(memories)} entries):")
        for m in memories[:5]:
            title = m.get("title") or (m.get("content") or "")[:80]
            kid = str(m.get("knowledge_id") or m.get("id") or "")
            lines.append(f"- [{kid[:8]}] {title}")

    if similar_siblings:
        lines.append("**Symbols with similar purpose** (consider reusing):")
        for s in similar_siblings[:SIMILAR_SIBLINGS_K]:
            qn = s.get("qualified_name") or s.get("symbol_id")
            score = s.get("score")
            lines.append(f"- {qn}" + (f" (similarity {score:.2f})" if score else ""))

    text = "\n".join(lines)

    # Token cap (rough: 4 chars per token).
    max_chars = INJECTION_HARD_CAP_TOKENS * 4
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[truncated to budget]"
    return text


# ---------------------------------------------------------------------------
# DB-backed steps (best-effort, fail-open)
# ---------------------------------------------------------------------------


def _row_to_dict(cur, row: Any) -> Dict[str, Any]:
    """Normalise psycopg2/3 row variants (tuple, namedtuple, dict-like) to dict."""
    if isinstance(row, dict):
        return dict(row)
    cols = [d[0] for d in cur.description]
    try:
        return {col: row[i] for i, col in enumerate(cols)}
    except (TypeError, KeyError):
        # dict-like rows where positional access fails — fall back to attr names.
        return {col: row[col] for col in cols}


def query_anchored_memories(conn, file_path: str, symbol_ids: List[str]) -> List[Dict[str, Any]]:
    """Return up to MEMORIES_PER_QUERY rows whose kg_links anchor here.

    Best-effort: returns [] if claude.knowledge.kg_links is missing
    (migration not yet applied) — graceful pre-migration behaviour.
    """
    if not conn:
        return []
    try:
        cur = conn.cursor()
        # Match every plausible spelling of the path — kg_links rows may
        # have been seeded as absolute Windows, absolute POSIX, or
        # project-relative form. The seed pipeline canonicalises to
        # backslash absolute, but defensive matching keeps us robust to
        # alternative seeders / hand-edits.
        path_forms = _normalize_file_paths(file_path) if file_path else [file_path]
        clauses = []
        params: List[Any] = []
        for pf in path_forms:
            clauses.append("kg_links @> %s::jsonb")
            params.append(json.dumps([{"kind": "file", "path": pf}]))
        for sid in symbol_ids:
            clauses.append("kg_links @> %s::jsonb")
            params.append(json.dumps([{"kind": "symbol", "id": str(sid)}]))
        where = " OR ".join(clauses)
        cur.execute(
            f"""
            SELECT knowledge_id, title, description AS content,
                   knowledge_type, times_applied
            FROM   claude.knowledge
            WHERE  ({where})
              AND  status IS DISTINCT FROM 'archived'
            ORDER  BY COALESCE(times_applied, 0) DESC,
                      created_at DESC
            LIMIT  %s
            """,
            params + [MEMORIES_PER_QUERY],
        )
        rows = cur.fetchall()
        return [_row_to_dict(cur, r) for r in rows]
    except Exception as exc:
        msg = str(exc)
        if "kg_links" in msg:
            logger.debug("kg_links column not yet present — pre-migration; "
                         "anchored memory query disabled")
        else:
            logger.warning(f"anchored memory query failed: {exc}")
        return []


def _normalize_file_paths(file_path: str) -> List[str]:
    """Return all path forms claude.code_symbols may have stored.

    The CKG stores absolute Windows paths (e.g. C:\\Projects\\...). The
    hook may receive either absolute or project-relative input. Try
    several forms so the lookup matches regardless.
    """
    if not file_path:
        return []
    forms = {file_path}
    fwd = file_path.replace("\\", "/")
    bwd = file_path.replace("/", "\\")
    forms.add(fwd)
    forms.add(bwd)
    if not (file_path.startswith("/") or (len(file_path) > 1 and file_path[1] == ":")):
        # Project-relative — qualify against likely CF root.
        cf_root = os.environ.get("CLAUDE_PROJECT_PATH", "C:\\Projects\\claude-family")
        joined = os.path.join(cf_root, file_path).replace("/", "\\")
        forms.add(joined)
        forms.add(joined.replace("\\", "/"))
    return list(forms)


def resolve_symbols_for_file(conn, file_path: str) -> List[Dict[str, Any]]:
    """Return symbols indexed in CKG for this file (best-effort)."""
    if not conn or not file_path:
        return []
    candidates = _normalize_file_paths(file_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT symbol_id,
                   COALESCE(NULLIF(scope, '') || '.' || name, name) AS qualified_name,
                   kind, line_number
            FROM   claude.code_symbols
            WHERE  file_path = ANY(%s)
            ORDER  BY line_number NULLS LAST
            LIMIT  20
            """,
            (candidates,),
        )
        rows = cur.fetchall()
        return [_row_to_dict(cur, r) for r in rows]
    except Exception as exc:
        logger.debug(f"symbol resolve skipped: {exc}")
        return []


def log_event(conn, *, tool_name: str, file_path: str, target_symbols: List[str],
              memories_n: int, overlay_calls_n: int, injection_chars: int,
              fallback_reason: Optional[str], outcome: str, latency_ms: float) -> None:
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO claude.mcp_usage (
              mcp_server, tool_name, tool_kind,
              target_files, target_symbols,
              would_have_been, bypass_detected, nudge_fired,
              duration_ms, called_at, metadata
            ) VALUES (
              %s, %s, 'hook',
              %s, %s,
              NULL, FALSE, FALSE,
              %s, NOW(),
              %s::jsonb
            )
            """,
            (
                "hal-semantic-engine",
                "coding_intelligence_writetime",
                [file_path] if file_path else None,
                target_symbols or None,
                latency_ms,
                json.dumps({
                    "tool": tool_name,
                    "memories_surfaced_n": memories_n,
                    "overlay_calls_n": overlay_calls_n,
                    "injection_chars": injection_chars,
                    "fallback_reason": fallback_reason,
                    "outcome": outcome,
                }),
            ),
        )
        conn.commit()
    except Exception as exc:
        logger.debug(f"mcp_usage log skipped: {exc}")
        try:
            conn.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Orchestrator (mirrors the BPMN flow)
# ---------------------------------------------------------------------------


def run(input_data: Dict[str, Any], aggregator: Optional[Callable] = None,
        conn: Any = None) -> Dict[str, Any]:
    """Pure orchestrator — returns the response dict, doesn't print."""
    start = time.perf_counter()
    target = extract_target(input_data)
    file_path = target["file_path"]
    project = target["project"]
    tool_name = target["tool_name"]

    if not is_indexable(file_path):
        return {"_response": {"decision": "allow"}, "outcome": "allowed_no_context",
                "fallback_reason": "not_indexable"}

    # Phase 2 — symbol resolution
    symbols = resolve_symbols_for_file(conn, file_path)
    symbol_ids = [s["symbol_id"] for s in symbols if s.get("symbol_id")]

    # Phase 3 — memory query (TIME axis)
    memories = query_anchored_memories(conn, file_path, symbol_ids)

    # Phase 4 — overlay enrichment (SPACE axis), gated
    overlay_results: List[Dict[str, Any]] = []
    similar_siblings: List[Dict[str, Any]] = []
    fallback_reason: Optional[str] = None
    overlay_calls_n = 0

    aggregator = aggregator or get_aggregator()
    cache = ResolvedSymbolCache(aggregator=aggregator)

    if symbols and aggregator is not _disabled_aggregator:
        for sym in symbols[:5]:  # Limit overlay calls per hook invocation
            qn = sym.get("qualified_name")
            if not qn:
                continue
            try:
                payload = cache.get_context_with_cache(
                    qualified_name=qn,
                    file_path=file_path,
                    project=project,
                    sibling_n=SIMILAR_SIBLINGS_K,
                )
                overlay_calls_n += 1
                if payload.get("error") == "project_mismatch":
                    # Retry once with force_reresolve (cache already cleared).
                    payload = cache.get_context_with_cache(
                        qualified_name=qn, file_path=file_path,
                        project=project, sibling_n=SIMILAR_SIBLINGS_K,
                        force_reresolve=True,
                    )
                    overlay_calls_n += 1
                if payload.get("intent") or payload.get("invariants"):
                    overlay_results.append(payload)
                for sib in payload.get("purpose_similar_siblings") or []:
                    similar_siblings.append(
                        {"qualified_name": sib} if isinstance(sib, str) else sib
                    )
            except NotImplementedError as exc:
                # Phase 4.1 gate 3: NOT silent-degrade. Emit marker, allow op.
                logger.warning(f"aggregator init failure: {exc}")
                latency_ms = (time.perf_counter() - start) * 1000
                log_event(conn, tool_name=tool_name, file_path=file_path or "",
                          target_symbols=symbol_ids, memories_n=len(memories),
                          overlay_calls_n=overlay_calls_n, injection_chars=0,
                          fallback_reason="init_failure",
                          outcome="aborted_init_failure", latency_ms=latency_ms)
                return {"_response": {"decision": "allow"},
                        "outcome": "aborted_init_failure",
                        "fallback_reason": "init_failure"}
            except Exception as exc:
                logger.info(f"overlay call failed for {qn}: {exc}")
                fallback_reason = fallback_reason or "overlay_unavailable"

    # Phase 5 — compose + log
    text = compose_injection(
        file_path=file_path or "",
        memories=memories,
        overlay_results=overlay_results,
        similar_siblings=similar_siblings,
    )
    latency_ms = (time.perf_counter() - start) * 1000
    outcome = "allowed_with_context" if text else "allowed_no_context"

    log_event(conn, tool_name=tool_name, file_path=file_path or "",
              target_symbols=symbol_ids, memories_n=len(memories),
              overlay_calls_n=overlay_calls_n, injection_chars=len(text),
              fallback_reason=fallback_reason, outcome=outcome,
              latency_ms=latency_ms)

    response: Dict[str, Any] = {"decision": "allow"}
    if text:
        response["additionalContext"] = text
    return {"_response": response, "outcome": outcome, "fallback_reason": fallback_reason,
            "memories_surfaced_n": len(memories), "overlay_calls_n": overlay_calls_n,
            "injection_chars": len(text), "latency_ms": latency_ms}


# ---------------------------------------------------------------------------
# Entry point (stdin → stdout)
# ---------------------------------------------------------------------------


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except Exception as exc:
        logger.error(f"invalid stdin: {exc}")
        print(json.dumps({"decision": "allow"}))
        return

    conn = None
    try:
        conn = get_db_connection() if detect_psycopg()[0] else None
        result = run(input_data, conn=conn)
        print(json.dumps(result["_response"]))
    except Exception as exc:
        logger.error(f"writetime hook error: {exc}", exc_info=True)
        try:
            from failure_capture import capture_failure
            capture_failure(
                "coding_intelligence_writetime_hook",
                str(exc),
                "scripts/coding_intelligence_writetime_hook.py",
            )
        except Exception:
            pass
        print(json.dumps({"decision": "allow"}))
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
