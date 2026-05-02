-- BT699 / F224: Generic circuit-breaker state table
-- Extracted from embedding_crashloop_detector.py, reusable across codebase
-- Non-destructive: idempotent CREATE TABLE IF NOT EXISTS

CREATE TABLE IF NOT EXISTS claude.circuit_breaker_state (
    name              varchar PRIMARY KEY,
    threshold_fails   int NOT NULL,
    window_secs       int NOT NULL,
    fail_events       jsonb DEFAULT '[]'::jsonb,
    is_tripped        bool DEFAULT false,
    tripped_at        timestamptz,
    tripped_reason    text,
    last_success_at   timestamptz,
    created_at        timestamptz DEFAULT now(),
    updated_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_circuit_breaker_tripped
ON claude.circuit_breaker_state (is_tripped)
WHERE is_tripped = true;

COMMENT ON TABLE claude.circuit_breaker_state IS
'Circuit-breaker state for fault-tolerance across processes.
Trips after threshold_fails failures within window_secs.
State persists so survives daemon restarts. Extracted from embedding_crashloop_detector (BT699).';

COMMENT ON COLUMN claude.circuit_breaker_state.fail_events IS
'Array of {ts: ISO8601, error_class, error_message} events within the rolling window.
Pruned each record_failure call to keep only events within window_secs.';
