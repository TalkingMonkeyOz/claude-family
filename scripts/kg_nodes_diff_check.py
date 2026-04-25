#!/usr/bin/env python3
"""P5 Stage 3 prep: row-level diff between kg_nodes and the 4 legacy source tables.

Runs nightly (or on demand). Walks each legacy table, asserts a matching kg_nodes
row exists, then compares key columns. Discrepancies land in claude.kg_nodes_diff_log.

Stage 3 unblocks when this job reports zero diffs for 7 consecutive days WITH
the dual-write triggers ENABLED.

Pre-Stage-2-flip: every legacy row will appear as 'missing' (kg_nodes is empty).
That is expected and not a real failure — it just means triggers haven't fired
yet. The check is most meaningful AFTER triggers are enabled and an initial
backfill has run.

Fail-safe: never raises; logs to stderr on DB issue; exit 0=clean, 1=diffs found,
2=infrastructure error.
"""
import json
import os
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
try:
    from config import DATABASE_URI as _db_uri
    DB_URI = _db_uri or ""
except Exception:
    DB_URI = os.environ.get("DATABASE_URI") or os.environ.get("DATABASE_URL", "")


# Source table → (id_column, projection_to_kg_node_columns)
# Each entry tells the diff job how to reconstruct the expected kg_nodes row.
SOURCES = {
    "knowledge": {
        "id_col": "knowledge_id",
        "select": """SELECT knowledge_id AS sid, title AS exp_title,
                            description AS exp_body, knowledge_type AS exp_kind,
                            tier AS exp_tier, status AS exp_status,
                            confidence_level AS exp_confidence
                     FROM claude.knowledge""",
    },
    "entities": {
        "id_col": "entity_id",
        "select": """SELECT entity_id AS sid, display_name AS exp_title,
                            summary AS exp_body, NULL AS exp_kind,
                            NULL AS exp_tier,
                            CASE WHEN is_archived THEN 'archived' ELSE 'active' END AS exp_status,
                            confidence AS exp_confidence
                     FROM claude.entities""",
    },
    "knowledge_articles": {
        "id_col": "article_id",
        "select": """SELECT article_id AS sid, title AS exp_title,
                            abstract AS exp_body, article_type AS exp_kind,
                            NULL AS exp_tier, status AS exp_status,
                            NULL::int AS exp_confidence
                     FROM claude.knowledge_articles""",
    },
    "article_sections": {
        "id_col": "section_id",
        "select": """SELECT section_id AS sid, title AS exp_title,
                            body AS exp_body, NULL AS exp_kind,
                            NULL AS exp_tier, 'active' AS exp_status,
                            NULL::int AS exp_confidence
                     FROM claude.article_sections""",
    },
}


def run_check() -> dict:
    import psycopg2
    import psycopg2.extras
    psycopg2.extras.register_uuid()
    conn = psycopg2.connect(DB_URI, connect_timeout=10)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        diffs = []

        for src, spec in SOURCES.items():
            cur.execute(spec["select"])
            legacy_rows = {r["sid"]: r for r in cur.fetchall()}

            cur.execute(
                """SELECT source_id, title, body, kind, tier, status, confidence
                   FROM claude.kg_nodes WHERE source_table=%s""",
                (src,),
            )
            kg_rows = {r["source_id"]: r for r in cur.fetchall()}

            # missing: in legacy, not in kg
            for sid in legacy_rows.keys() - kg_rows.keys():
                diffs.append((src, sid, "missing", None, None, None,
                              "row exists in legacy but not in kg_nodes"))
            # extra: in kg, not in legacy
            for sid in kg_rows.keys() - legacy_rows.keys():
                diffs.append((src, sid, "extra", None, None, None,
                              "row exists in kg_nodes but not in legacy"))
            # mismatch: present both sides, compare columns
            for sid in legacy_rows.keys() & kg_rows.keys():
                lr, kr = legacy_rows[sid], kg_rows[sid]
                for col, exp_col in (("title", "exp_title"), ("body", "exp_body"),
                                      ("kind", "exp_kind"), ("tier", "exp_tier"),
                                      ("status", "exp_status"), ("confidence", "exp_confidence")):
                    if lr[exp_col] != kr[col]:
                        diffs.append((src, sid, "mismatch", col,
                                      str(lr[exp_col])[:200], str(kr[col])[:200],
                                      f"column {col} mismatch"))

        # Insert diff rows
        if diffs:
            cur.executemany(
                """INSERT INTO claude.kg_nodes_diff_log
                       (source_table, source_id, diff_kind, column_name, legacy_value, kg_value, notes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                diffs,
            )
        conn.commit()

        return {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "sources_checked": list(SOURCES.keys()),
            "total_diffs": len(diffs),
            "by_kind": {kind: sum(1 for d in diffs if d[2] == kind)
                        for kind in ("missing", "extra", "mismatch")},
            "clean": len(diffs) == 0,
        }
    finally:
        conn.close()


def main():
    try:
        result = run_check()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["clean"] else 1)
    except Exception as e:
        print(f"diff_check_failed: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
