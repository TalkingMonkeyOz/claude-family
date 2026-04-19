"""
FB242 test: verify stale session task archive SQL.

Creates synthetic todos in claude-family with various content prefixes and session
linkage, runs the archive SQL from session_startup_hook_enhanced.py, and asserts
only [S]-prefixed todos from prior sessions are archived.

Runs against live DB. Cleans up test rows at end.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import get_db_connection  # type: ignore

TEST_PROJECT = 'claude-family'


def run_archive_sql(conn, project_name: str, current_session_id: str) -> int:
    """Mirror the FB242 SQL block in session_startup_hook_enhanced.py."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE claude.todos t
        SET status = 'archived', updated_at = NOW()
        FROM claude.projects p
        WHERE t.project_id = p.project_id
          AND p.project_name = %s
          AND NOT t.is_deleted
          AND t.status IN ('pending', 'in_progress')
          AND t.content LIKE '[S]%%'
          AND (%s::uuid IS NULL OR t.created_session_id IS DISTINCT FROM %s::uuid)
    """, (project_name, current_session_id, current_session_id))
    count = cur.rowcount
    conn.commit()
    cur.close()
    return count


def main() -> int:
    conn = get_db_connection()
    assert conn, "DB connection failed"

    project_cur = conn.cursor()
    project_cur.execute(
        "SELECT project_id FROM claude.projects WHERE project_name = %s",
        (TEST_PROJECT,)
    )
    row = project_cur.fetchone()
    assert row, f"Project {TEST_PROJECT} not found"
    project_id = row['project_id'] if isinstance(row, dict) else row[0]
    project_cur.close()

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO claude.sessions (session_id, project_name, session_start, session_end, session_summary)
        VALUES (gen_random_uuid(), %s, NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days' + INTERVAL '1 hour', 'FB242 test: prior session')
        RETURNING session_id::text
    """, (TEST_PROJECT,))
    prior_row = cur.fetchone()
    prior_session = prior_row['session_id'] if isinstance(prior_row, dict) else prior_row[0]
    cur.execute("""
        INSERT INTO claude.sessions (session_id, project_name, session_start, session_summary)
        VALUES (gen_random_uuid(), %s, NOW(), 'FB242 test: current session')
        RETURNING session_id::text
    """, (TEST_PROJECT,))
    cur_row = cur.fetchone()
    current_session = cur_row['session_id'] if isinstance(cur_row, dict) else cur_row[0]
    conn.commit()
    cur.close()

    test_marker = f'FB242_TEST_{uuid.uuid4().hex[:8]}'
    fixtures = [
        ('[S] FB242TEST session task from prior session',     prior_session,   'pending',     True),
        ('[S] FB242TEST session task in_progress prior',      prior_session,   'in_progress', True),
        ('[S] FB242TEST session task from current session',   current_session, 'pending',     False),
        ('[P] FB242TEST persistent task from prior session',  prior_session,   'pending',     False),
        ('FB242TEST unprefixed task from prior session',      prior_session,   'pending',     False),
        ('[S] FB242TEST completed task from prior session',   prior_session,   'completed',   False),
    ]

    cur = conn.cursor()
    todo_ids = []
    for i, (content, sid, status, _) in enumerate(fixtures):
        cur.execute("""
            INSERT INTO claude.todos (todo_id, project_id, created_session_id, content, active_form, status, priority)
            VALUES (gen_random_uuid(), %s, %s::uuid, %s, %s, %s, 3)
            RETURNING todo_id
        """, (project_id, sid, content, content, status))
        rr = cur.fetchone()
        todo_ids.append(rr['todo_id'] if isinstance(rr, dict) else rr[0])
    conn.commit()
    cur.close()

    archived_count = run_archive_sql(conn, TEST_PROJECT, current_session)

    cur = conn.cursor()
    assertions = []
    for todo_id, (content, _, _, should_archive) in zip(todo_ids, fixtures):
        cur.execute("SELECT status FROM claude.todos WHERE todo_id = %s", (todo_id,))
        rr = cur.fetchone()
        actual_status = rr['status'] if isinstance(rr, dict) else rr[0]
        expected = 'archived' if should_archive else ('completed' if 'completed' in content else ('pending' if 'in_progress' not in content else 'in_progress'))
        ok = actual_status == expected
        assertions.append((ok, content, actual_status, expected))

    cur.execute(
        "DELETE FROM claude.todos WHERE content LIKE %s",
        ('%FB242TEST%',)
    )
    cleaned = cur.rowcount
    cur.execute(
        "DELETE FROM claude.sessions WHERE session_id IN (%s::uuid, %s::uuid)",
        (prior_session, current_session)
    )
    conn.commit()
    cur.close()
    conn.close()

    all_passed = all(a[0] for a in assertions)
    for ok, content, actual, expected in assertions:
        mark = 'PASS' if ok else 'FAIL'
        print(f"  [{mark}] status={actual!r} expected={expected!r} -- {content}")

    print()
    print(f"Archive SQL total row count (includes pre-existing stale tasks in project): {archived_count}")
    print(f"Test fixtures cleaned up: {cleaned}")
    print()
    print(f"RESULT: {'ALL FIXTURE ASSERTIONS PASSED' if all_passed else 'FAILED'}")
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
