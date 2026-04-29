#!/usr/bin/env python3
"""Task Drift Sweep (FB398).

Scheduled job (daily) implementing task_drift_detection.bpmn Path B.

Scans claude.build_tasks WHERE status IN ('todo','in_progress') AND files_affected
IS NOT NULL. For each candidate:

  1. Verify all paths in files_affected exist on disk.
  2. git log on each path; collect short_codes mentioned in commit messages.
  3. If commits reference this BT### OR a sibling short_code from the same
     feature, mark as likely-duplicate.
  4. Dedupe on title prefix so re-runs do not stack feedback.
  5. File 'design' priority='medium' feedback titled
     "BT### may be duplicate: <task_name>" with file + commit detail.

Run output is logged to claude.scheduled_jobs.last_output as JSON:
    {"checked": N, "drifted": M, "feedback_filed": K}

Fail-open: any error is captured to ~/.claude/logs/task_drift_sweep.jsonl
and the script exits 0 so the job runner stays green.

Usage:
    python task_drift_sweep.py [--dry-run] [--verbose] [--project NAME]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

PROJECT_ROOT = SCRIPT_DIR.parent
LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
FAIL_LOG = LOG_DIR / "task_drift_sweep.jsonl"

# Match "BT123", "FB45", "F8" tokens in commit messages
_BT_TOKEN = re.compile(r"\b(BT|FB|F)(\d+)\b")


def _capture_failure(stage, exc):
    try:
        with FAIL_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "script": "task_drift_sweep",
                "stage": stage,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=5),
            }) + "\n")
    except Exception:
        pass


def _connect():
    import psycopg2
    import psycopg2.extras
    try:
        from config import get_database_uri
        uri = get_database_uri()
    except Exception:
        uri = os.environ.get("DATABASE_URI") or os.environ.get("DATABASE_URL")
    if not uri:
        raise RuntimeError("No DATABASE_URI/DATABASE_URL configured")
    conn = psycopg2.connect(uri, connect_timeout=10)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn


def gather_candidates(conn, project_name=None):
    """Return open build_tasks with non-empty files_affected."""
    cur = conn.cursor()
    sql = """
        SELECT bt.short_code, bt.task_name, bt.files_affected, bt.feature_id,
               bt.task_id::text AS task_id, p.project_name
        FROM claude.build_tasks bt
        JOIN claude.projects p ON p.project_id = bt.project_id
        WHERE bt.status IN ('todo', 'in_progress')
          AND bt.files_affected IS NOT NULL
          AND array_length(bt.files_affected, 1) > 0
    """
    args = []
    if project_name:
        sql += " AND p.project_name = %s"
        args.append(project_name)
    cur.execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return rows


def sibling_short_codes(conn, feature_id, exclude_short_code):
    """Return short_codes of completed sibling tasks under the same feature."""
    cur = conn.cursor()
    cur.execute("""
        SELECT short_code FROM claude.build_tasks
        WHERE feature_id = %s::uuid
          AND status = 'completed'
          AND short_code != %s
    """, (feature_id, exclude_short_code))
    out = [row["short_code"] for row in cur.fetchall()]
    cur.close()
    return out


def all_paths_exist(files_affected, root=PROJECT_ROOT):
    """All paths must resolve to a real file/dir under project root."""
    if not files_affected:
        return False
    for rel in files_affected:
        p = (root / rel).resolve()
        if not p.exists():
            return False
    return True


def git_short_codes_for_path(rel_path, root=PROJECT_ROOT):
    """Return set of integer short_codes referenced in commit messages touching rel_path.

    Looks across all branches via --all. Returns empty set on git error.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--all", "--pretty=%s", "--", rel_path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return set()
        out = set()
        for msg in result.stdout.splitlines():
            for prefix, num in _BT_TOKEN.findall(msg):
                try:
                    out.add(int(num))
                except ValueError:
                    pass
        return out
    except Exception:
        return set()


def git_short_codes_for_files(files_affected, root=PROJECT_ROOT):
    """Union short_codes referenced across all paths in files_affected."""
    out = set()
    for rel in files_affected:
        out |= git_short_codes_for_path(rel, root)
    return out


def is_likely_duplicate(candidate, conn, root=PROJECT_ROOT):
    """All paths exist on disk AND git log mentions this BT or a completed sibling."""
    files = candidate["files_affected"]
    if not all_paths_exist(files, root):
        return False, None
    refs = git_short_codes_for_files(files, root)
    if not refs:
        return False, None
    own = candidate["short_code"]
    siblings = sibling_short_codes(conn, candidate["feature_id"], own)
    if own in refs or any(s in refs for s in siblings):
        # Pick the most informative referenced code: prefer own > sibling > any
        if own in refs:
            evidence_code = own
        else:
            for s in siblings:
                if s in refs:
                    evidence_code = s
                    break
            else:
                evidence_code = next(iter(refs))
        return True, {"refs": sorted(refs), "evidence_code": evidence_code, "siblings": siblings}
    return False, None


def feedback_title(candidate):
    return "BT{} may be duplicate: {}".format(
        candidate["short_code"], (candidate["task_name"] or "")[:80]
    )


def already_filed(conn, candidate):
    cur = conn.cursor()
    title_prefix = "BT{} may be duplicate".format(candidate["short_code"])
    cur.execute("""
        SELECT 1 FROM claude.feedback
        WHERE title ILIKE %s
          AND (status IS NULL OR status NOT IN ('resolved', 'wont_fix', 'duplicate'))
        LIMIT 1
    """, (title_prefix + "%",))
    found = cur.fetchone() is not None
    cur.close()
    return found


def file_feedback(conn, project_id, candidate, evidence):
    cur = conn.cursor()
    title = feedback_title(candidate)
    refs_str = ", ".join("BT{}".format(r) for r in evidence["refs"])
    description = (
        "Build task BT{bt} ('{name}') is still status='todo'/'in_progress', but:\n"
        "  - All files in files_affected exist on disk: {files}\n"
        "  - Commits touching those files reference: {refs}\n"
        "  - Strongest evidence: BT{ev} (own short_code or completed sibling under same feature)\n"
        "\n"
        "Detected by: scripts/task_drift_sweep.py (FB398, BPMN task_drift_detection rule B)\n"
        "\n"
        "Action: verify the work was already shipped under a different short_code and close BT{bt} "
        "via work_status(item_code='BT{bt}', action='complete') with a completion_note pointing at "
        "the original commit. If this is a false positive, resolve this feedback as wont_fix."
    ).format(
        bt=candidate["short_code"],
        name=(candidate["task_name"] or "")[:120],
        files=", ".join(candidate["files_affected"]),
        refs=refs_str,
        ev=evidence["evidence_code"],
    )
    try:
        cur.execute("""
            INSERT INTO claude.feedback
                (feedback_id, project_id, feedback_type, priority, status,
                 title, description, created_at, updated_at, assigned_to)
            VALUES (gen_random_uuid(), %s, 'design', 'medium', 'new',
                    %s, %s, NOW(), NOW(), 'claude-family')
            RETURNING feedback_id
        """, (project_id, title[:500], description))
        cur.fetchone()
        cur.close()
        return True
    except Exception as exc:
        cur.close()
        _capture_failure("file_feedback", exc)
        return False


def _resolve_project_id(conn, project_name):
    cur = conn.cursor()
    cur.execute(
        "SELECT project_id FROM claude.projects WHERE project_name = %s",
        (project_name,),
    )
    row = cur.fetchone()
    cur.close()
    return str(row["project_id"]) if row else None


def run(dry_run=False, verbose=False, project_name=None, root=PROJECT_ROOT):
    summary = {"checked": 0, "drifted": 0, "feedback_filed": 0, "dry_run": dry_run}
    conn = _connect()
    try:
        candidates = gather_candidates(conn, project_name)
        summary["checked"] = len(candidates)

        for cand in candidates:
            drift, evidence = is_likely_duplicate(cand, conn, root)
            if not drift:
                continue
            summary["drifted"] += 1

            if already_filed(conn, cand):
                if verbose:
                    print("[dup] feedback exists for BT{}".format(cand["short_code"]))
                continue

            if dry_run:
                if verbose:
                    print("[dry-run] would file:", feedback_title(cand))
                continue

            project_id = _resolve_project_id(conn, cand["project_name"])
            if not project_id:
                continue
            if file_feedback(conn, project_id, cand, evidence):
                summary["feedback_filed"] += 1
                if verbose:
                    print("[filed]", feedback_title(cand))

        if not dry_run:
            conn.commit()
    finally:
        conn.close()
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Do not insert feedback")
    ap.add_argument("--verbose", action="store_true", help="Print per-candidate log")
    ap.add_argument("--project", default=None, help="Limit scan to one project")
    args = ap.parse_args()

    try:
        summary = run(dry_run=args.dry_run, verbose=args.verbose, project_name=args.project)
        print(json.dumps(summary))
        return 0
    except Exception as exc:
        _capture_failure("main", exc)
        print(json.dumps({
            "checked": 0, "drifted": 0, "feedback_filed": 0,
            "error": str(exc),
        }))
        return 0


if __name__ == "__main__":
    sys.exit(main())
