#!/usr/bin/env python3
"""
Add Vault Embeddings Scheduled Job - FB134

This script adds (or updates) the vault embeddings scheduled job to the database.
The job runs daily to incrementally update Voyage AI embeddings for changed vault documents.

Usage:
    python scripts/add_vault_embeddings_job.py
"""

import sys
import os
from datetime import datetime

# Try multiple ways to import psycopg
PSYCOPG_VERSION = 0
psycopg = None

try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        PSYCOPG_VERSION = 2
    except ImportError:
        print("ERROR: Neither psycopg nor psycopg2 installed.", file=sys.stderr)
        sys.exit(1)


def get_db_connection():
    """Get PostgreSQL connection from environment."""
    conn_string = os.environ.get('DATABASE_URI') or os.environ.get('POSTGRES_CONNECTION_STRING')

    if not conn_string:
        # Try ai-workspace config as fallback
        try:
            sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
            from config import POSTGRES_CONFIG
            # psycopg3 uses 'dbname' not 'database'
            cfg = dict(POSTGRES_CONFIG)
            if 'database' in cfg and 'dbname' not in cfg:
                cfg['dbname'] = cfg.pop('database')
            if PSYCOPG_VERSION == 3:
                return psycopg.connect(**cfg, row_factory=dict_row)
            else:
                return psycopg.connect(**POSTGRES_CONFIG, cursor_factory=RealDictCursor)
        except ImportError:
            print("ERROR: No database connection configured.", file=sys.stderr)
            print("Set DATABASE_URI or POSTGRES_CONNECTION_STRING environment variable.", file=sys.stderr)
            sys.exit(1)

    if PSYCOPG_VERSION == 3:
        return psycopg.connect(conn_string, row_factory=dict_row)
    else:
        return psycopg.connect(conn_string, cursor_factory=RealDictCursor)


def main():
    """Main entry point."""
    print("=" * 70)
    print("FB134: Add Vault Embeddings Scheduled Job")
    print("=" * 70)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Step 1: Check if scheduled_jobs table exists
        print("\n[1] Checking if claude.scheduled_jobs table exists...")
        if PSYCOPG_VERSION == 3:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'claude' AND table_name = 'scheduled_jobs'
            """)
        else:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'claude' AND table_name = 'scheduled_jobs'
            """)

        if not cur.fetchone():
            print("    ERROR: Table claude.scheduled_jobs does not exist!")
            print("    This table should have been created during infrastructure setup.")
            print("    Verify your database schema is up to date.")
            conn.close()
            return 1

        print("    ✓ Table exists")

        # Step 2: Check table schema
        print("\n[2] Checking table schema...")
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'claude' AND table_name = 'scheduled_jobs'
            ORDER BY ordinal_position
        """)

        columns = cur.fetchall()
        required_cols = {
            'job_name', 'command', 'working_directory', 'schedule',
            'trigger_type', 'timeout_seconds', 'is_active', 'next_run', 'job_description'
        }

        found_cols = {col['column_name'] for col in columns}
        missing = required_cols - found_cols

        if missing:
            print(f"    WARNING: Missing columns: {missing}")
            print("    Table schema may be different than expected.")

        print(f"    ✓ Found {len(found_cols)} columns")

        # Step 3: Check if job already exists
        print("\n[3] Checking if job already exists...")
        cur.execute("""
            SELECT job_id, is_active, last_run, next_run, last_status
            FROM claude.scheduled_jobs
            WHERE job_name = 'vault-embeddings-update'
        """)

        existing = cur.fetchone()

        if existing:
            print(f"    ✓ Job exists (ID: {existing['job_id']})")
            print(f"      Active: {existing['is_active']}")
            print(f"      Last run: {existing['last_run']}")
            print(f"      Last status: {existing['last_status']}")

            # Update existing job to be active
            print("\n[4] Updating existing job...")
            cur.execute("""
                UPDATE claude.scheduled_jobs
                SET is_active = true,
                    next_run = NOW(),
                    updated_at = NOW()
                WHERE job_name = 'vault-embeddings-update'
            """)
            conn.commit()
            print("    ✓ Updated: is_active=true, next_run=NOW()")
        else:
            # Insert new job
            print("    Job does not exist, will create new one")
            print("\n[4] Inserting new scheduled job...")

            cur.execute("""
                INSERT INTO claude.scheduled_jobs (
                    job_id,
                    job_name,
                    command,
                    working_directory,
                    schedule,
                    trigger_type,
                    timeout_seconds,
                    is_active,
                    next_run,
                    job_description,
                    created_at,
                    updated_at
                ) VALUES (
                    gen_random_uuid(),
                    'vault-embeddings-update',
                    'python scripts/embed_vault_documents.py --all-projects',
                    'C:\\Projects\\claude-family',
                    'daily',
                    'scheduled',
                    600,
                    true,
                    NOW(),
                    'Daily incremental update of Voyage AI embeddings for vault documents and project files. Only re-embeds changed files (SHA256 hash check). Supports --force for full refresh.',
                    NOW(),
                    NOW()
                )
                RETURNING job_id
            """)

            result = cur.fetchone()
            job_id = result['job_id']
            conn.commit()
            print(f"    ✓ Created new job with ID: {job_id}")

        # Step 5: Verify current state
        print("\n[5] Verifying current state...")
        cur.execute("""
            SELECT job_name, schedule, trigger_type, is_active, next_run, last_run, last_status
            FROM claude.scheduled_jobs
            WHERE job_name = 'vault-embeddings-update'
        """)

        job = cur.fetchone()
        if job:
            print(f"    ✓ Job: {job['job_name']}")
            print(f"      Schedule: {job['schedule']}")
            print(f"      Type: {job['trigger_type']}")
            print(f"      Active: {job['is_active']}")
            print(f"      Next run: {job['next_run']}")
            print(f"      Last run: {job['last_run']}")
            print(f"      Last status: {job['last_status']}")

        # Step 6: Check vault embeddings status
        print("\n[6] Checking vault embeddings status...")
        cur.execute("""
            SELECT COUNT(*) as total_embeddings,
                   MIN(embedded_at) as oldest,
                   MAX(embedded_at) as newest
            FROM claude.vault_embeddings
        """)

        stats = cur.fetchone()
        if stats:
            print(f"    ✓ Total embeddings: {stats['total_embeddings']}")
            print(f"      Oldest: {stats['oldest']}")
            print(f"      Newest: {stats['newest']}")

        conn.close()

        print("\n" + "=" * 70)
        print("SUCCESS: Vault embeddings job is ready")
        print("=" * 70)
        print("\nNext steps:")
        print("1. The scheduler_runner.py will execute this job based on the schedule")
        print("2. Run manually with: python scripts/scheduler_runner.py --force vault-embeddings-update")
        print("3. List all jobs with: python scripts/scheduler_runner.py --list")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        conn.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
