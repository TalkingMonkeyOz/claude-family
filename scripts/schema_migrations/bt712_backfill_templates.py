"""BT712 — Backfill scheduled_jobs to template_id pattern.

Idempotent. Re-running produces zero changes after first success.

Skips:
- Rows already linked (template_id IS NOT NULL)
- Inactive rows (is_active = false)
- PowerShell jobs (postgres-backup) — keep legacy command path for now
- Interval-schedule jobs (kg_nodes_parity_check uses '24h' format)
- Never-ran jobs (task-drift-sweep, operating-mode-review)

For each remaining row:
- Build template payload {command: [...], cwd, timeout}
- Create job_template with sanitized name
- UPDATE scheduled_jobs.template_id = new_id WHERE template_id IS NULL
"""
import sys, os, json, shlex
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))) + '/mcp-servers/project-tools')

import config
config.get_database_uri()

from handlers.job_template import handle_job_template
from config import get_db_connection

SKIP_JOB_NAMES = {
    'postgres-backup',
    'kg_nodes_parity_check',
    'task-drift-sweep',
    'queue_health_check_15min',
    'dead_letter_sweep_daily',
    'archive_sweep_nightly',
}


def main():
    conn = get_db_connection(strict=True)
    cur = conn.cursor()
    cur.execute("""
        SELECT job_id::text, job_name, schedule, command, working_directory, job_description,
               timeout_seconds, last_status, source
        FROM claude.scheduled_jobs
        WHERE template_id IS NULL AND is_active = true
        ORDER BY job_name
    """)
    rows = cur.fetchall()
    cur.close()

    print(f"Backfill candidates: {len(rows)}\n")

    success, skipped, failed = 0, 0, 0
    for row in rows:
        if isinstance(row, dict):
            job_id, job_name = row['job_id'], row['job_name']
            schedule, command = row['schedule'], row['command']
            cwd = row['working_directory']
            desc = row['job_description'] or job_name
            timeout = row.get('timeout_seconds') or 600
        else:
            job_id, job_name, schedule, command, cwd, desc, timeout, _last_status, _source = row
            desc = desc or job_name
            timeout = timeout or 600

        if job_name in SKIP_JOB_NAMES:
            print(f"  SKIP   {job_name} (special-case)")
            skipped += 1
            continue
        if not command or 'powershell' in command.lower():
            print(f"  SKIP   {job_name} (no python command)")
            skipped += 1
            continue

        tpl_name = ''.join(c if c.isalnum() or c in '_-' else '_' for c in job_name)

        try:
            cmd_list = shlex.split(command, posix=False)
            cmd_list = [a.strip('"') for a in cmd_list]
        except Exception as e:
            print(f"  FAIL   {job_name}: shlex parse error: {e}")
            failed += 1
            continue

        payload = {"command": cmd_list, "timeout": int(timeout)}
        if cwd:
            # Collapse over-escaped backslashes to single backslash
            normalised = cwd
            while "\\\\" in normalised:
                normalised = normalised.replace("\\\\", "\\")
            payload["cwd"] = normalised

        try:
            result = handle_job_template(
                action="create",
                name=tpl_name,
                description=desc[:500],
                kind="script",
                max_concurrent_runs=1,
                max_attempts=2,
                lease_duration_secs=max(int(timeout) + 60, 120),
                is_idempotent=True,
                payload=payload,
            )
        except Exception as e:
            print(f"  FAIL   {job_name}: template create error: {e}")
            failed += 1
            continue

        if not result.get('success'):
            err = str(result.get('error', ''))
            if 'already exists' in err or 'duplicate' in err.lower() or 'unique' in err.lower():
                print(f"  REUSE  {job_name}: template '{tpl_name}' already exists, looking up id")
                c2 = conn.cursor()
                c2.execute("SELECT template_id::text FROM claude.job_templates WHERE name = %s", (tpl_name,))
                r = c2.fetchone()
                c2.close()
                tid = r[0] if not isinstance(r, dict) else r['template_id']
            else:
                print(f"  FAIL   {job_name}: {err}")
                failed += 1
                continue
        else:
            tid = result['template_id']

        c3 = conn.cursor()
        c3.execute("""
            UPDATE claude.scheduled_jobs
            SET template_id = %s::uuid, updated_at = now()
            WHERE job_id = %s::uuid AND template_id IS NULL
        """, (tid, job_id))
        conn.commit()
        c3.close()

        print(f"  OK     {job_name} -> template {tid[:8]}")
        success += 1

    conn.close()
    print(f"\nSummary: {success} backfilled, {skipped} skipped, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
