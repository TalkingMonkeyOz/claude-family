"""BT695 — Register column_registry entries for F224 task_queue / job_templates.

Idempotent. Uses ON CONFLICT (table_name, column_name) DO NOTHING so re-running
preserves any post-hoc edits to existing rows (per storage-rules non-destructive
migration discipline).

Scope per BT695:
  - The 5 enum/state CHECK columns (status, resolution_status, kind,
    origin_role, trigger_kind) were already registered during F224 ship —
    this script asserts they exist.
  - Adds the documentation rows that BT695 explicitly calls out as missing:
      job_templates.is_idempotent     (boolean state flag, mirrors is_paused)
      task_queue.cancel_requested     (boolean state flag, signals cancel-soft)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config  # noqa: F401  -- side-effect: load env
from config import get_db_connection


REQUIRED_EXISTING = [
    ("task_queue", "status"),
    ("task_queue", "resolution_status"),
    ("task_queue", "priority"),
    ("job_templates", "kind"),
    ("job_templates", "is_paused"),
    ("job_template_origins", "origin_kind"),
    ("job_template_origins", "origin_role"),
    ("job_run_history", "trigger_kind"),
]


NEW_ROWS = [
    {
        "table_name": "job_templates",
        "column_name": "is_idempotent",
        "data_type": "boolean",
        "is_nullable": True,
        "default_value": "false",
        "description": (
            "F224 — when true, identical (template_id, version, payload) "
            "enqueues collapse to one task via idempotency_key uniqueness "
            "(only enforced over active states pending|in_progress)."
        ),
        "valid_values": [True, False],
        "constraints": "Boolean state flag. Used by job_enqueue to derive idempotency_key.",
    },
    {
        "table_name": "task_queue",
        "column_name": "cancel_requested",
        "data_type": "boolean",
        "is_nullable": True,
        "default_value": "false",
        "description": (
            "F224 — soft-cancel signal. Worker checks this at heartbeat / "
            "checkpoint boundaries and exits cleanly if true. Force-cancel "
            "(job_cancel force=true) revokes the lease instead."
        ),
        "valid_values": [True, False],
        "constraints": "Boolean state flag. Read by task_worker cancel-check loop.",
    },
]


def main() -> int:
    conn = get_db_connection(strict=True)
    cur = conn.cursor()

    cur.execute(
        "SELECT table_name, column_name FROM claude.column_registry "
        "WHERE table_name = ANY(%s)",
        (list({t for t, _ in REQUIRED_EXISTING}),),
    )
    found_existing = {(r[0], r[1]) if not isinstance(r, dict) else (r["table_name"], r["column_name"])
                      for r in cur.fetchall()}
    missing_required = [pair for pair in REQUIRED_EXISTING if pair not in found_existing]
    if missing_required:
        print(f"[FAIL] Required pre-existing rows missing: {missing_required}")
        cur.close(); conn.close()
        return 1
    print(f"[OK] All {len(REQUIRED_EXISTING)} pre-existing F224 enum rows present")

    inserted = 0
    skipped = 0
    import json as _json
    for row in NEW_ROWS:
        cur.execute(
            """
            INSERT INTO claude.column_registry
              (table_name, column_name, data_type, is_nullable,
               default_value, description, valid_values, constraints)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (table_name, column_name) DO NOTHING
            RETURNING id
            """,
            (
                row["table_name"], row["column_name"], row["data_type"],
                row["is_nullable"], row["default_value"], row["description"],
                _json.dumps(row["valid_values"]), row["constraints"],
            ),
        )
        if cur.fetchone() is not None:
            inserted += 1
            print(f"[INSERT] {row['table_name']}.{row['column_name']}")
        else:
            skipped += 1
            print(f"[SKIP]   {row['table_name']}.{row['column_name']} (already present)")

    conn.commit()
    cur.close(); conn.close()

    print(f"\nDone. inserted={inserted} skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
