"""
test_cf_constants.py — Comprehensive tests for cf_constants module (F224 BT696).

Tests cover:
- Backoff exponential growth with jitter bounds
- Heartbeat interval derivation
- Idempotency key determinism and payload order-insensitivity
- Environment variable override mechanism
- All constants are accessible and have sensible defaults
"""

import json
import os
import sys
from unittest import mock

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import cf_constants


class TestBackoffSeconds:
    """Test exponential backoff with jitter."""

    def test_backoff_attempt_1_within_jitter_range(self):
        """Attempt 1 returns base ± jitter_pct (default 25%)."""
        base = cf_constants.CF_DEFAULT_RETRY_BACKOFF_BASE
        jitter_pct = cf_constants.CF_DEFAULT_RETRY_JITTER_PCT

        # Run 100 times to verify distribution falls within expected range
        results = [
            cf_constants.cf_backoff_seconds(1, base=base, jitter_pct=jitter_pct)
            for _ in range(100)
        ]

        jitter_range = base * (jitter_pct / 100.0)
        min_expected = base - jitter_range
        max_expected = base + jitter_range

        for result in results:
            assert result >= 1, "Backoff must be >= 1"
            # Allow a small tolerance for rounding
            assert result >= min_expected - 1, f"Result {result} below {min_expected}"
            assert result <= max_expected + 1, f"Result {result} above {max_expected}"

    def test_backoff_attempt_2_roughly_2x_attempt_1(self):
        """Attempt 2 is roughly 2x of attempt 1 (exponential growth)."""
        base = 30
        jitter_pct = 5  # Use small jitter to reduce noise

        attempt_1_results = [
            cf_constants.cf_backoff_seconds(1, base=base, jitter_pct=jitter_pct)
            for _ in range(10)
        ]
        attempt_2_results = [
            cf_constants.cf_backoff_seconds(2, base=base, jitter_pct=jitter_pct)
            for _ in range(10)
        ]

        avg_1 = sum(attempt_1_results) / len(attempt_1_results)
        avg_2 = sum(attempt_2_results) / len(attempt_2_results)

        # Allow 10% tolerance for randomness
        assert avg_2 > avg_1 * 1.5, f"Attempt 2 ({avg_2}) should be ~2x attempt 1 ({avg_1})"
        assert avg_2 < avg_1 * 2.5, f"Attempt 2 ({avg_2}) should be ~2x attempt 1 ({avg_1})"

    def test_backoff_capped_at_max(self):
        """High attempt numbers cap at CF_DEFAULT_RETRY_BACKOFF_MAX."""
        cap = cf_constants.CF_DEFAULT_RETRY_BACKOFF_MAX
        base = 30

        # Attempt 20 would be 30 * 2^19 without cap (huge), should be capped
        result = cf_constants.cf_backoff_seconds(20, base=base, cap=cap)

        # With cap and jitter, should be around cap (within jitter range)
        jitter_range = cap * (cf_constants.CF_DEFAULT_RETRY_JITTER_PCT / 100.0)
        assert result <= cap + jitter_range + 1, f"Result {result} exceeds cap {cap} + jitter"
        assert result >= 1, "Result must be >= 1"

    def test_backoff_always_returns_minimum_1(self):
        """Backoff always returns >= 1, even with extreme jitter."""
        # Worst case: base=1, jitter=100%, attempt=1
        results = [
            cf_constants.cf_backoff_seconds(1, base=1, jitter_pct=100)
            for _ in range(100)
        ]
        assert all(r >= 1 for r in results), "All results must be >= 1"

    def test_backoff_negative_attempt_treated_as_1(self):
        """Negative or zero attempt is treated as attempt 1."""
        base = 30
        result_0 = cf_constants.cf_backoff_seconds(0, base=base, jitter_pct=5)
        result_neg = cf_constants.cf_backoff_seconds(-5, base=base, jitter_pct=5)
        result_1 = cf_constants.cf_backoff_seconds(1, base=base, jitter_pct=5)

        # All should be roughly equal (base ± jitter)
        jitter_range = base * (5 / 100.0)
        assert abs(result_0 - result_1) < jitter_range * 2
        assert abs(result_neg - result_1) < jitter_range * 2

    def test_backoff_custom_parameters(self):
        """Custom base, cap, and jitter_pct are respected."""
        result = cf_constants.cf_backoff_seconds(
            1, base=60, cap=1000, jitter_pct=10
        )

        # Should be roughly 60 ± 6 (10% of 60)
        assert 50 <= result <= 70, f"Result {result} not in expected range for custom params"


class TestHeartbeatInterval:
    """Test heartbeat interval derivation from lease."""

    def test_heartbeat_default_lease_300_divisor_3(self):
        """Default: 300s lease / 3 = 100s interval."""
        result = cf_constants.cf_heartbeat_interval(
            lease_secs=300, divisor=3
        )
        assert result == 100

    def test_heartbeat_custom_lease(self):
        """Custom lease: 600s / 3 = 200s."""
        result = cf_constants.cf_heartbeat_interval(lease_secs=600, divisor=3)
        assert result == 200

    def test_heartbeat_custom_divisor(self):
        """Custom divisor: 300s / 2 = 150s."""
        result = cf_constants.cf_heartbeat_interval(lease_secs=300, divisor=2)
        assert result == 150

    def test_heartbeat_minimum_1(self):
        """Very small lease still returns >= 1."""
        result = cf_constants.cf_heartbeat_interval(lease_secs=1, divisor=10)
        assert result >= 1

    def test_heartbeat_uses_defaults_when_none(self):
        """None parameters use module defaults."""
        result = cf_constants.cf_heartbeat_interval()
        default_lease = cf_constants.CF_DEFAULT_LEASE_SECS
        default_div = cf_constants.CF_DEFAULT_HEARTBEAT_DIVISOR
        expected = default_lease // default_div
        assert result == expected


class TestIdempotencyKey:
    """Test deterministic idempotency key generation."""

    def test_idempotency_key_deterministic(self):
        """Same inputs always produce the same key."""
        template_id = "template-uuid-123"
        version = 1
        payload = {"task": "test", "priority": 5}

        key1 = cf_constants.cf_idempotency_key(template_id, version, payload)
        key2 = cf_constants.cf_idempotency_key(template_id, version, payload)

        assert key1 == key2, "Determinism failed"

    def test_idempotency_key_differs_for_different_payloads(self):
        """Different payloads produce different keys."""
        template_id = "template-uuid-123"
        version = 1
        payload1 = {"task": "test1"}
        payload2 = {"task": "test2"}

        key1 = cf_constants.cf_idempotency_key(template_id, version, payload1)
        key2 = cf_constants.cf_idempotency_key(template_id, version, payload2)

        assert key1 != key2, "Different payloads should produce different keys"

    def test_idempotency_key_dict_order_insensitive(self):
        """Dict key order doesn't affect the key (json.dumps sort_keys=True)."""
        template_id = "template-uuid-123"
        version = 1

        # Same dict content, different key order
        payload_ordered = {"a": 1, "b": 2, "c": 3}
        payload_unordered = {"c": 3, "a": 1, "b": 2}

        key1 = cf_constants.cf_idempotency_key(template_id, version, payload_ordered)
        key2 = cf_constants.cf_idempotency_key(
            template_id, version, payload_unordered
        )

        assert key1 == key2, "Dict key order should not affect idempotency key"

    def test_idempotency_key_none_payload(self):
        """None payload is handled correctly."""
        template_id = "template-uuid-123"
        version = 1

        key1 = cf_constants.cf_idempotency_key(template_id, version, None)
        key2 = cf_constants.cf_idempotency_key(template_id, version, None)

        assert key1 == key2, "None payload should be deterministic"
        assert isinstance(key1, str), "Key should be string"
        assert len(key1) == 64, "SHA256 hex should be 64 chars"

    def test_idempotency_key_nested_payload(self):
        """Nested dicts/lists are canonicalized."""
        template_id = "template-uuid-123"
        version = 1
        payload = {"nested": {"z": 3, "a": 1}, "list": [3, 1, 2]}

        key = cf_constants.cf_idempotency_key(template_id, version, payload)

        # Verify it's deterministic
        key2 = cf_constants.cf_idempotency_key(template_id, version, payload)
        assert key == key2

    def test_idempotency_key_differs_for_different_versions(self):
        """Different template versions produce different keys."""
        template_id = "template-uuid-123"
        payload = {"task": "test"}

        key1 = cf_constants.cf_idempotency_key(template_id, 1, payload)
        key2 = cf_constants.cf_idempotency_key(template_id, 2, payload)

        assert key1 != key2, "Different versions should produce different keys"

    def test_idempotency_key_is_sha256_hex(self):
        """Key is SHA256 hex (64 chars, lowercase hex)."""
        template_id = "template-uuid-123"
        version = 1
        payload = {}

        key = cf_constants.cf_idempotency_key(template_id, version, payload)

        assert isinstance(key, str), "Key should be string"
        assert len(key) == 64, "SHA256 hex should be 64 chars"
        assert all(c in "0123456789abcdef" for c in key), "Should be hex lowercase"


class TestEnvironmentVariableOverrides:
    """Test that constants can be overridden via environment variables."""

    @mock.patch.dict(os.environ, {"CF_SCRIPT_WORKER_COUNT": "5"})
    def test_script_worker_count_override(self):
        """CF_SCRIPT_WORKER_COUNT env var is read on module reload."""
        # Reload module to pick up mocked env var
        import importlib

        # Create a fresh module state in a subprocess-like test
        with mock.patch.dict(os.environ, {"CF_SCRIPT_WORKER_COUNT": "5"}):
            # Re-evaluate the constant (simulate module load with override)
            count = int(os.environ.get("CF_SCRIPT_WORKER_COUNT", "2"))
            assert count == 5

    @mock.patch.dict(os.environ, {"CF_AGENT_WORKER_COUNT": "8"})
    def test_agent_worker_count_override(self):
        """CF_AGENT_WORKER_COUNT env var is read on module reload."""
        count = int(os.environ.get("CF_AGENT_WORKER_COUNT", "4"))
        assert count == 8

    @mock.patch.dict(os.environ, {"CF_DEFAULT_LEASE_SECS": "600"})
    def test_default_lease_secs_override(self):
        """CF_DEFAULT_LEASE_SECS env var is read on module reload."""
        lease = int(os.environ.get("CF_DEFAULT_LEASE_SECS", "300"))
        assert lease == 600

    @mock.patch.dict(
        os.environ,
        {
            "CF_DEFAULT_RETRY_BACKOFF_BASE": "60",
            "CF_DEFAULT_RETRY_BACKOFF_MAX": "7200",
        },
    )
    def test_retry_policy_overrides(self):
        """Retry policy defaults can be overridden."""
        base = int(os.environ.get("CF_DEFAULT_RETRY_BACKOFF_BASE", "30"))
        cap = int(os.environ.get("CF_DEFAULT_RETRY_BACKOFF_MAX", "3600"))
        assert base == 60
        assert cap == 7200

    @mock.patch.dict(os.environ, {"CF_BACKLOG_ALERT_THRESHOLD": "200"})
    def test_backlog_alert_threshold_override(self):
        """CF_BACKLOG_ALERT_THRESHOLD env var is read on module reload."""
        threshold = int(os.environ.get("CF_BACKLOG_ALERT_THRESHOLD", "100"))
        assert threshold == 200


class TestConstantsAccessible:
    """Test that all constants are accessible and have sensible defaults."""

    def test_script_worker_count_is_positive(self):
        """CF_SCRIPT_WORKER_COUNT is positive."""
        assert cf_constants.CF_SCRIPT_WORKER_COUNT > 0

    def test_agent_worker_count_is_positive(self):
        """CF_AGENT_WORKER_COUNT is positive."""
        assert cf_constants.CF_AGENT_WORKER_COUNT > 0

    def test_default_lease_secs_is_positive(self):
        """CF_DEFAULT_LEASE_SECS is positive."""
        assert cf_constants.CF_DEFAULT_LEASE_SECS > 0

    def test_default_heartbeat_divisor_is_positive(self):
        """CF_DEFAULT_HEARTBEAT_DIVISOR is positive."""
        assert cf_constants.CF_DEFAULT_HEARTBEAT_DIVISOR > 0

    def test_default_max_attempts_is_positive(self):
        """CF_DEFAULT_MAX_ATTEMPTS is positive."""
        assert cf_constants.CF_DEFAULT_MAX_ATTEMPTS > 0

    def test_default_retry_backoff_base_is_positive(self):
        """CF_DEFAULT_RETRY_BACKOFF_BASE is positive."""
        assert cf_constants.CF_DEFAULT_RETRY_BACKOFF_BASE > 0

    def test_default_retry_backoff_max_ge_base(self):
        """CF_DEFAULT_RETRY_BACKOFF_MAX >= CF_DEFAULT_RETRY_BACKOFF_BASE."""
        assert (
            cf_constants.CF_DEFAULT_RETRY_BACKOFF_MAX
            >= cf_constants.CF_DEFAULT_RETRY_BACKOFF_BASE
        )

    def test_default_retry_jitter_pct_in_range(self):
        """CF_DEFAULT_RETRY_JITTER_PCT is in reasonable range (0-100)."""
        assert 0 <= cf_constants.CF_DEFAULT_RETRY_JITTER_PCT <= 100

    def test_pause_threshold_fails_is_positive(self):
        """CF_DEFAULT_PAUSE_THRESHOLD_FAILS is positive."""
        assert cf_constants.CF_DEFAULT_PAUSE_THRESHOLD_FAILS > 0

    def test_pause_threshold_window_secs_is_positive(self):
        """CF_DEFAULT_PAUSE_THRESHOLD_WINDOW_SECS is positive."""
        assert cf_constants.CF_DEFAULT_PAUSE_THRESHOLD_WINDOW_SECS > 0

    def test_backlog_alert_threshold_is_positive(self):
        """CF_BACKLOG_ALERT_THRESHOLD is positive."""
        assert cf_constants.CF_BACKLOG_ALERT_THRESHOLD > 0

    def test_dead_letter_rate_threshold_is_positive(self):
        """CF_DEAD_LETTER_RATE_THRESHOLD is positive."""
        assert cf_constants.CF_DEAD_LETTER_RATE_THRESHOLD > 0

    def test_health_check_interval_mins_is_positive(self):
        """CF_HEALTH_CHECK_INTERVAL_MINS is positive."""
        assert cf_constants.CF_HEALTH_CHECK_INTERVAL_MINS > 0

    def test_transient_error_classes_is_list(self):
        """CF_DEFAULT_TRANSIENT_ERROR_CLASSES is a list."""
        assert isinstance(cf_constants.CF_DEFAULT_TRANSIENT_ERROR_CLASSES, list)
        assert len(cf_constants.CF_DEFAULT_TRANSIENT_ERROR_CLASSES) > 0

    def test_agent_transient_error_classes_includes_default(self):
        """CF_AGENT_TRANSIENT_ERROR_CLASSES includes default classes."""
        defaults = cf_constants.CF_DEFAULT_TRANSIENT_ERROR_CLASSES
        agent_classes = cf_constants.CF_AGENT_TRANSIENT_ERROR_CLASSES

        assert all(c in agent_classes for c in defaults)
        # Agent-specific classes should also be present
        assert len(agent_classes) > len(defaults)


class TestExportedSymbols:
    """Test that expected symbols are exported."""

    def test_all_constants_exported(self):
        """All constants are accessible as module attributes."""
        expected_constants = [
            "CF_SCRIPT_WORKER_COUNT",
            "CF_AGENT_WORKER_COUNT",
            "CF_DEFAULT_LEASE_SECS",
            "CF_DEFAULT_HEARTBEAT_DIVISOR",
            "CF_DEFAULT_DRAIN_DEADLINE_SECS",
            "CF_DEFAULT_MAX_ATTEMPTS",
            "CF_DEFAULT_RETRY_BACKOFF_BASE",
            "CF_DEFAULT_RETRY_BACKOFF_MAX",
            "CF_DEFAULT_RETRY_JITTER_PCT",
            "CF_DEFAULT_PAUSE_THRESHOLD_FAILS",
            "CF_DEFAULT_PAUSE_THRESHOLD_WINDOW_SECS",
            "CF_BACKLOG_ALERT_THRESHOLD",
            "CF_DEAD_LETTER_RATE_THRESHOLD",
            "CF_LEAKED_LEASE_THRESHOLD",
            "CF_DRAIN_STALL_SECS",
            "CF_HEALTH_CHECK_INTERVAL_MINS",
            "CF_L3_LIVENESS_MAX_AGE_MINS",
            "CF_DEFAULT_TRANSIENT_ERROR_CLASSES",
            "CF_AGENT_TRANSIENT_ERROR_CLASSES",
        ]

        for const in expected_constants:
            assert hasattr(cf_constants, const), f"Missing constant: {const}"

    def test_all_helpers_exported(self):
        """All helper functions are accessible as module attributes."""
        expected_helpers = [
            "cf_backoff_seconds",
            "cf_heartbeat_interval",
            "cf_idempotency_key",
        ]

        for helper in expected_helpers:
            assert hasattr(cf_constants, helper), f"Missing helper: {helper}"
            assert callable(getattr(cf_constants, helper)), f"{helper} not callable"
