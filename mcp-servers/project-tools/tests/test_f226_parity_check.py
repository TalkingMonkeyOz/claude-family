"""
test_f226_parity_check.py — F226 / BT719 verification.

Tests the parity-check script logic + scheduled_jobs registration.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "f226_parity_check.py"


def _run_script(*args) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True, text=True, cwd=str(SCRIPT_PATH.parent.parent),
    )
    return result.returncode, result.stdout + result.stderr


class TestParityCheckBaseline:
    """Against the cleanly-resynced baseline, parity check should detect no drift."""

    def test_clean_baseline_returns_zero_exit_code(self):
        exit_code, output = _run_script("--no-feedback")
        assert exit_code == 0, f"expected 0 (no drift); output:\n{output}"
        assert "drift_detected=False" in output

    def test_json_mode_returns_drift_detected_false(self):
        exit_code, output = _run_script("--no-feedback", "--json")
        assert exit_code == 0
        # Drop any human-readable preamble (there isn't supposed to be any) and
        # parse the JSON payload.
        payload = json.loads(output)
        assert payload['drift_detected'] is False
        for r in payload['row_counts']:
            assert r['delta'] == 0
        for s in payload['status_distribution']:
            assert s['diff'] == {}
        for m in payload['missing_legacy_codes']:
            assert m['missing_count'] == 0


class TestSchedulingRegistration:
    """The job is registered in claude.scheduled_jobs and active."""

    def test_job_registered_and_active(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT job_name, schedule, is_active, command "
                "FROM claude.scheduled_jobs WHERE job_name='f226-parity-check'"
            )
            row = cur.fetchone()
        assert row is not None, "f226-parity-check not registered"
        assert row['is_active'] is True
        assert row['schedule'] == '*/15 * * * *'
        assert 'f226_parity_check.py' in (row['command'] or '')


class TestDriftDetection:
    """Inject a divergent row, assert drift detected, then roll back."""

    def test_injected_row_count_drift_is_detected(self, db_conn):
        # Pick a real backfilled work_item and simulate a missing legacy code by
        # deleting its code_history entry inside the rollback fixture.
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT h.history_id, wi.work_item_id "
                "FROM claude.work_item_code_history h "
                "JOIN claude.work_items wi ON wi.work_item_id = h.work_item_id "
                "WHERE h.code_kind='legacy' AND h.short_code LIKE 'F%' "
                "  AND h.short_code !~ '^F[A-Z]' "
                "LIMIT 1"
            )
            row = cur.fetchone()
            assert row is not None
            # Remove the legacy code → compat view loses this row → row-count drift.
            cur.execute(
                "DELETE FROM claude.work_item_code_history WHERE history_id=%s::uuid",
                (row['history_id'],),
            )
            db_conn.commit()
        try:
            exit_code, output = _run_script("--no-feedback")
            assert exit_code == 1, f"expected 1 (drift); output:\n{output}"
            assert "drift_detected=True" in output
        finally:
            db_conn.rollback()
