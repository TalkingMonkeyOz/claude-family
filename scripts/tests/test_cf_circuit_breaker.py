"""Tests for cf_circuit_breaker (BT699 / F224).

Verifies trip / reset / window-rollover / persistence using the real
claude.circuit_breaker_state table with unique CB-TEST-* names per test
and cleanup teardown.
"""
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cf_circuit_breaker import CircuitBreaker, _default_db_conn


def _db_available() -> bool:
    conn = _default_db_conn()
    if not conn:
        return False
    conn.close()
    return True


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="DATABASE_URL unset or DB unreachable",
)


@pytest.fixture
def cb_name():
    name = f"CB-TEST-{uuid.uuid4().hex[:12]}"
    yield name
    conn = _default_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM claude.circuit_breaker_state WHERE name = %s;",
                (name,),
            )
            cur.close()
        finally:
            conn.close()


def test_trip_at_threshold(cb_name):
    cb = CircuitBreaker(name=cb_name, threshold_fails=3, window_secs=60)
    assert cb.record_failure(error_class="X", error_message="1") is False
    assert cb.record_failure(error_class="X", error_message="2") is False
    tripped = cb.record_failure(error_class="X", error_message="3")
    assert tripped is True, "third failure should trip the breaker"
    assert cb.is_tripped() is True
    state = cb.state()
    assert state["tripped"] is True
    assert state["fail_count_in_window"] == 3
    assert state["tripped_reason"] is not None


def test_subsequent_failure_after_trip_does_not_re_trip(cb_name):
    cb = CircuitBreaker(name=cb_name, threshold_fails=2, window_secs=60)
    cb.record_failure()
    assert cb.record_failure() is True  # tripped
    # Already tripped — next failure should not return True
    assert cb.record_failure() is False
    assert cb.is_tripped() is True


def test_reset_clears_state(cb_name):
    cb = CircuitBreaker(name=cb_name, threshold_fails=2, window_secs=60)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_tripped() is True
    cb.reset(reason="test reset")
    assert cb.is_tripped() is False
    state = cb.state()
    assert state["fail_count_in_window"] == 0
    assert "test reset" in (state["tripped_reason"] or "")


def test_window_rollover_does_not_trip(cb_name):
    """Failures older than window are pruned and don't count toward threshold."""
    cb = CircuitBreaker(name=cb_name, threshold_fails=3, window_secs=1)
    cb.record_failure()
    cb.record_failure()
    time.sleep(1.5)  # wait past the 1s window
    # Both prior failures are now outside the window. New failure starts fresh.
    tripped = cb.record_failure()
    assert tripped is False, "window rollover should prune old failures"
    state = cb.state()
    assert state["fail_count_in_window"] == 1
    assert state["tripped"] is False


def test_persistence_across_instances(cb_name):
    """Tripped state persists in DB so a fresh CircuitBreaker instance sees it."""
    cb1 = CircuitBreaker(name=cb_name, threshold_fails=2, window_secs=60)
    cb1.record_failure()
    cb1.record_failure()
    assert cb1.is_tripped() is True

    # New process / restart simulation: brand-new instance with the same name.
    cb2 = CircuitBreaker(name=cb_name, threshold_fails=2, window_secs=60)
    assert cb2.is_tripped() is True
    assert cb2.state()["fail_count_in_window"] == 2


def test_on_trip_callback_fires_once(cb_name):
    calls = []
    cb = CircuitBreaker(
        name=cb_name,
        threshold_fails=2,
        window_secs=60,
        on_trip=lambda: calls.append(1),
    )
    cb.record_failure()
    assert calls == []
    cb.record_failure()
    assert calls == [1]
    # Subsequent failures should not fire callback again (already tripped)
    cb.record_failure()
    assert calls == [1]


def test_record_success_updates_last_success_at(cb_name):
    cb = CircuitBreaker(name=cb_name, threshold_fails=5, window_secs=60)
    cb.record_failure()
    cb.record_success()
    # No assertion on exact value; just verifying no exception + state still readable.
    state = cb.state()
    assert state["fail_count_in_window"] == 1
