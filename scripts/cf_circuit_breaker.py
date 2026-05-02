#!/usr/bin/env python3
"""Circuit breaker with DB-persisted state — generic, reusable across codebase.

Extracted from embedding_crashloop_detector.py (BT699 / F224).
Trips after `threshold_fails` failures within `window_secs`, persists state to DB
so multiple processes/restarts share state. Designed for embedding service,
task_worker per-template breakers, and any future consumer.

Usage:
    cb = CircuitBreaker(
        name='embedding-service',
        threshold_fails=5,
        window_secs=600,
        on_trip=lambda: capture_failure(...)
    )

    if cb.record_failure(error_class='ModelLoadError', error_message='...'):
        # Breaker just tripped
        pass

    if cb.is_tripped():
        # Don't try to work; wait for manual reset() or timeout
        sys.exit(1)

    cb.record_success()  # Inform telemetry
"""
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Callable, Optional

import psycopg2
from psycopg2.extensions import connection as Connection

# Default DB connection factory (reads DATABASE_URL)
def _default_db_conn() -> Optional[Connection]:
    """Return a psycopg2 connection or None on failure."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True  # For immediate visibility across processes
        return conn
    except Exception:
        return None


class CircuitBreaker:
    """
    Trips after threshold_fails failures within window_secs.
    State persisted to claude.circuit_breaker_state so survives restarts.
    """

    def __init__(
        self,
        name: str,
        threshold_fails: int = 5,
        window_secs: int = 600,
        on_trip: Optional[Callable[[], None]] = None,
        db_conn_factory: Optional[Callable[[], Optional[Connection]]] = None,
    ):
        """
        Args:
            name: unique identifier (e.g., 'embedding-service', 'job_template:reindex-ckg')
            threshold_fails: failure count that trips the breaker
            window_secs: rolling window over which failures are counted
            on_trip: optional callback invoked when breaker trips (e.g., capture_failure)
            db_conn_factory: callable returning a psycopg connection (or None for default)
        """
        self.name = name
        self.threshold_fails = threshold_fails
        self.window_secs = window_secs
        self.on_trip = on_trip
        self._db_conn_factory = db_conn_factory or _default_db_conn
        self._ensure_schema()

    def _ensure_schema(self):
        """Create circuit_breaker_state table if it doesn't exist."""
        conn = self._db_conn_factory()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
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
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_circuit_breaker_tripped
                ON claude.circuit_breaker_state (is_tripped)
                WHERE is_tripped = true;
                """
            )
            cursor.close()
        except Exception as e:
            print(f"[CircuitBreaker] schema creation failed: {e}", file=sys.stderr)
        finally:
            conn.close()

    def record_failure(self, error_class: Optional[str] = None, error_message: Optional[str] = None) -> bool:
        """
        Record a failure. Returns True if this failure tripped the breaker.
        Prunes old events outside the window.
        """
        conn = self._db_conn_factory()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=self.window_secs)

            # Upsert: get current state or create it
            cursor.execute(
                """
                INSERT INTO claude.circuit_breaker_state
                  (name, threshold_fails, window_secs, fail_events, created_at, updated_at)
                VALUES (%s, %s, %s, '[]'::jsonb, now(), now())
                ON CONFLICT (name) DO NOTHING
                RETURNING name;
                """,
                (self.name, self.threshold_fails, self.window_secs),
            )
            cursor.fetchall()

            # Get current state
            cursor.execute(
                """
                SELECT fail_events, is_tripped FROM claude.circuit_breaker_state
                WHERE name = %s;
                """,
                (self.name,),
            )
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return False

            fail_events, is_tripped = row
            if fail_events is None:
                fail_events = []

            # Filter out old events outside window
            fail_events = [
                evt
                for evt in fail_events
                if datetime.fromisoformat(evt["ts"]) >= window_start
            ]

            # Append new event
            new_event = {
                "ts": now.isoformat(),
                "error_class": error_class or "Unknown",
                "error_message": (error_message or "")[:500],
            }
            fail_events.append(new_event)

            # Check if we trip
            tripped_this_call = False
            if len(fail_events) >= self.threshold_fails and not is_tripped:
                tripped_this_call = True

            # Update DB
            cursor.execute(
                """
                UPDATE claude.circuit_breaker_state
                SET fail_events = %s,
                    is_tripped = %s,
                    tripped_at = CASE WHEN %s AND NOT is_tripped THEN now() ELSE tripped_at END,
                    tripped_reason = CASE WHEN %s AND NOT is_tripped THEN %s ELSE tripped_reason END,
                    updated_at = now()
                WHERE name = %s;
                """,
                (
                    json.dumps(fail_events),
                    True if len(fail_events) >= self.threshold_fails else False,
                    tripped_this_call,
                    tripped_this_call,
                    f"{self.threshold_fails} failures in {self.window_secs}s window",
                    self.name,
                ),
            )

            cursor.close()

            # Invoke callback if tripped
            if tripped_this_call and self.on_trip:
                try:
                    self.on_trip()
                except Exception as e:
                    print(f"[CircuitBreaker] on_trip callback failed: {e}", file=sys.stderr)

            return tripped_this_call
        except Exception as e:
            print(f"[CircuitBreaker] record_failure failed: {e}", file=sys.stderr)
            return False
        finally:
            conn.close()

    def record_success(self) -> None:
        """Record a success — informs telemetry but does NOT reset."""
        conn = self._db_conn_factory()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE claude.circuit_breaker_state
                SET last_success_at = now(), updated_at = now()
                WHERE name = %s;
                """,
                (self.name,),
            )
            cursor.close()
        except Exception as e:
            print(f"[CircuitBreaker] record_success failed: {e}", file=sys.stderr)
        finally:
            conn.close()

    def is_tripped(self) -> bool:
        """Live check — true if breaker is currently in tripped state."""
        conn = self._db_conn_factory()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT is_tripped FROM claude.circuit_breaker_state WHERE name = %s;",
                (self.name,),
            )
            row = cursor.fetchone()
            cursor.close()
            return row[0] if row else False
        except Exception as e:
            print(f"[CircuitBreaker] is_tripped failed: {e}", file=sys.stderr)
            return False
        finally:
            conn.close()

    def reset(self, reason: Optional[str] = None) -> None:
        """Manual unpause — clears tripped state."""
        conn = self._db_conn_factory()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE claude.circuit_breaker_state
                SET is_tripped = false, tripped_at = NULL, tripped_reason = %s,
                    fail_events = '[]'::jsonb, updated_at = now()
                WHERE name = %s;
                """,
                (f"Manual reset: {reason}" if reason else "Manual reset", self.name),
            )
            cursor.close()
        except Exception as e:
            print(f"[CircuitBreaker] reset failed: {e}", file=sys.stderr)
        finally:
            conn.close()

    def state(self) -> dict:
        """Returns {tripped, fail_count_in_window, last_failure_at, tripped_at, tripped_reason}."""
        conn = self._db_conn_factory()
        if not conn:
            return {}

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT is_tripped, fail_events, tripped_at, tripped_reason
                FROM claude.circuit_breaker_state
                WHERE name = %s;
                """,
                (self.name,),
            )
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return {
                    "tripped": False,
                    "fail_count_in_window": 0,
                    "last_failure_at": None,
                    "tripped_at": None,
                    "tripped_reason": None,
                }

            is_tripped, fail_events, tripped_at, tripped_reason = row
            fail_events = fail_events or []
            last_failure_at = None
            if fail_events:
                last_failure_at = fail_events[-1].get("ts")

            return {
                "tripped": is_tripped,
                "fail_count_in_window": len(fail_events),
                "last_failure_at": last_failure_at,
                "tripped_at": tripped_at.isoformat() if tripped_at else None,
                "tripped_reason": tripped_reason,
            }
        except Exception as e:
            print(f"[CircuitBreaker] state failed: {e}", file=sys.stderr)
            return {}
        finally:
            conn.close()
