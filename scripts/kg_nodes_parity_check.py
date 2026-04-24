#!/usr/bin/env python3
"""P5 Stage 1 canary: daily parity check for kg_nodes_view.

Runs as a scheduled job (job_runner) OR ad-hoc. Inserts one row into
claude.kg_nodes_parity_log comparing view count vs sum of source tables.

7 consecutive parity_ok=true rows unblocks P5 Stage 2 (physical table +
dual-write). Any parity_ok=false row resets the counter.

Fail-safe: never raises; logs to stderr on DB issue.
"""
import os
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
try:
    from config import DATABASE_URI as _db_uri
    DB_URI = _db_uri or ""
except Exception:
    DB_URI = os.environ.get("DATABASE_URI", "")


def run_check() -> dict:
    """Run one parity check. Returns the inserted row as dict."""
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(DB_URI, connect_timeout=5)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT COUNT(*)::int AS n FROM claude.kg_nodes_view")
        view_rows = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*)::int AS n FROM claude.knowledge")
        k_rows = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*)::int AS n FROM claude.entities")
        e_rows = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*)::int AS n FROM claude.article_sections")
        s_rows = cur.fetchone()["n"]

        parity_ok = view_rows == (k_rows + e_rows + s_rows)

        cur.execute(
            """INSERT INTO claude.kg_nodes_parity_log
                  (view_rows, knowledge_rows, entities_rows, article_sections_rows, parity_ok, notes)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING check_id, checked_at, parity_ok""",
            (view_rows, k_rows, e_rows, s_rows, parity_ok,
             f"auto {datetime.now(timezone.utc).isoformat()}"),
        )
        result = dict(cur.fetchone())
        conn.commit()

        # Compute green streak from most-recent backwards
        cur.execute(
            """WITH recent AS (
                SELECT parity_ok,
                       ROW_NUMBER() OVER (ORDER BY checked_at DESC) AS rn
                FROM claude.kg_nodes_parity_log
              )
              SELECT COALESCE(MIN(rn) - 1, (SELECT COUNT(*) FROM claude.kg_nodes_parity_log))::int AS streak
              FROM recent WHERE NOT parity_ok"""
        )
        streak_row = cur.fetchone()
        result["streak"] = streak_row["streak"] if streak_row else 0

        return {
            "check_id": result["check_id"],
            "checked_at": result["checked_at"].isoformat(),
            "view_rows": view_rows,
            "source_sum": k_rows + e_rows + s_rows,
            "parity_ok": parity_ok,
            "streak": result["streak"],
            "stage2_ready": result["streak"] >= 7 and parity_ok,
        }
    finally:
        conn.close()


def main():
    try:
        import json
        result = run_check()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("parity_ok") else 1)
    except Exception as e:
        print(f"parity_check_failed: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
