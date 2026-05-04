"""F232.P3 — caller-side cache for hal-semantic-engine.overlay_get_full_context.

Used by the PreToolUse(Edit|Write) hook to avoid re-resolving the same
(qualified_name, file_path, project) triple within a single edit burst.

Three invalidation rules (per workfile 7891e031 / hal spec workfile 737553be):

  1. TTL — entries expire after 5 min by default (configurable per call site).
  2. Stale-resolution — invalidate on every put when an annotated symbol
     just returned coverage_status='unannotated'.
  3. project_mismatch — full clear (not single-key) to be conservative
     against worktree/branch swaps. Cost of being wrong is tiny latency
     on the next ~10 calls; cost of being lax is cross-project leakage.
  4. Explicit override — force_reresolve=True bypasses the cache.

Single-threaded assumption: the F232.P3 hook runs in a single Python
process, one PreToolUse invocation at a time. If async ever happens,
swap the dict for `cachetools.TTLCache` + `asyncio.Lock`.

Future state (after hal task #472 ships): subscribe to
select_drift_events(target_kind='kg_index') and clear on each event.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional, Tuple

CacheKey = Tuple[Optional[str], Optional[str], str]
"""(qualified_name, file_path, project) — project is required."""

DEFAULT_TTL_SECONDS = 300  # 5 minutes


class ResolvedSymbolCache:
    """In-memory TTL cache wrapping overlay_get_full_context calls."""

    def __init__(
        self,
        aggregator: Callable[..., Dict[str, Any]],
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._aggregator = aggregator
        self._ttl = ttl_seconds
        self._clock = clock
        self._store: Dict[CacheKey, Tuple[float, Dict[str, Any]]] = {}

    # -- public ------------------------------------------------------------

    def get_context_with_cache(
        self,
        *,
        qualified_name: Optional[str] = None,
        file_path: Optional[str] = None,
        project: str,
        force_reresolve: bool = False,
        **aggregator_kwargs: Any,
    ) -> Dict[str, Any]:
        """Return overlay_get_full_context payload, caching by triple."""
        key: CacheKey = (qualified_name, file_path, project)

        if not force_reresolve:
            hit = self._get_fresh(key)
            if hit is not None:
                return hit

        payload = self._aggregator(
            qualified_name=qualified_name,
            file_path=file_path,
            project=project,
            **aggregator_kwargs,
        )

        if isinstance(payload, dict) and payload.get("error") == "project_mismatch":
            # Worktree/branch shift suspected — full clear, surface the
            # error to the caller (recovery path retries with force_reresolve).
            self.clear()
            return payload

        self._put(key, payload)
        return payload

    def clear(self) -> None:
        """Drop every entry. Called on project_mismatch and at session end."""
        self._store.clear()

    def invalidate(self, key: CacheKey) -> None:
        """Drop a single entry (used by tests / explicit caller hints)."""
        self._store.pop(key, None)

    def __len__(self) -> int:  # debugging aid
        return len(self._store)

    # -- internals ---------------------------------------------------------

    def _get_fresh(self, key: CacheKey) -> Optional[Dict[str, Any]]:
        entry = self._store.get(key)
        if entry is None:
            return None
        cached_at, payload = entry
        if (self._clock() - cached_at) > self._ttl:
            self._store.pop(key, None)
            return None
        return payload

    def _put(self, key: CacheKey, payload: Dict[str, Any]) -> None:
        self._invalidate_if_stale(key, payload)
        self._store[key] = (self._clock(), payload)

    def _invalidate_if_stale(self, key: CacheKey, new_payload: Dict[str, Any]) -> None:
        """Catch the annotated→unannotated transition at write time.

        If the previous cache entry for this key was 'annotated' and the
        new payload is 'unannotated', the underlying overlay flipped
        state (most likely a re-index dropped the annotation). We must
        not let the stale 'annotated' payload linger — but the caller
        already has the new payload, so this is mostly defensive
        bookkeeping for future puts.
        """
        prior = self._store.get(key)
        if prior is None:
            return
        _, prior_payload = prior
        prior_status = (prior_payload or {}).get("coverage_status")
        new_status = (new_payload or {}).get("coverage_status")
        if prior_status == "annotated" and new_status == "unannotated":
            self._store.pop(key, None)
