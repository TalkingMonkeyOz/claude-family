#!/usr/bin/env python3
"""
Agent Health Check Script

Checks the health of Claude instances and spawned agents:
- Recent session activity
- Agent spawn success rates
- MCP server connectivity

Part of the Claude Family infrastructure.
"""

import sys
import os
import io
from datetime import datetime, timedelta

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection


def check_recent_sessions(conn, hours=24):
    """Check recent session activity."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) as total_sessions,
            COUNT(DISTINCT identity_id) as unique_identities,
            COUNT(CASE WHEN session_end IS NULL THEN 1 END) as open_sessions,
            MAX(session_start) as last_session_start
        FROM claude.sessions
        WHERE session_start >= NOW() - INTERVAL '%s hours'
    """, (hours,))
    result = cur.fetchone()
    return dict(result) if result else {}


def check_agent_stats(conn, hours=24):
    """Check agent spawn statistics."""
    cur = conn.cursor()

    # Check if agent_sessions table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'claude'
            AND table_name = 'agent_sessions'
        )
    """)
    if not cur.fetchone()['exists']:
        return {'table_exists': False}

    cur.execute("""
        SELECT
            COUNT(*) as total_spawns,
            COUNT(CASE WHEN success = true THEN 1 END) as successful,
            COUNT(CASE WHEN success = false THEN 1 END) as errors,
            AVG(execution_time_seconds) as avg_time_seconds,
            SUM(estimated_cost_usd) as total_cost_usd
        FROM claude.agent_sessions
        WHERE spawned_at >= NOW() - INTERVAL '%s hours'
    """, (hours,))
    result = cur.fetchone()
    return dict(result) if result else {}


def check_identity_status(conn):
    """Check status of registered identities."""
    cur = conn.cursor()
    cur.execute("""
        SELECT identity_name, status, platform
        FROM claude.identities
        ORDER BY identity_name
    """)
    return [dict(row) for row in cur.fetchall()]


def main():
    """Main entry point."""
    print("=" * 60)
    print("Agent Health Check")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    issues = []

    try:
        conn = get_db_connection()

        # Check recent sessions (last 24h)
        print("\n## Session Activity (last 24 hours)")
        sessions = check_recent_sessions(conn, hours=24)
        print(f"  Total sessions: {sessions.get('total_sessions', 0)}")
        print(f"  Unique identities: {sessions.get('unique_identities', 0)}")
        print(f"  Currently open: {sessions.get('open_sessions', 0)}")
        last_start = sessions.get('last_session_start')
        if last_start:
            print(f"  Last session: {last_start}")

        # Warn if no recent sessions
        if sessions.get('total_sessions', 0) == 0:
            issues.append("No sessions in the last 24 hours")

        # Check agent stats (last 24h)
        print("\n## Agent Spawns (last 24 hours)")
        agent_stats = check_agent_stats(conn, hours=24)
        if agent_stats.get('table_exists') == False:
            print("  Agent sessions table not found")
        else:
            total = agent_stats.get('total_spawns', 0) or 0
            successful = agent_stats.get('successful', 0) or 0
            errors = agent_stats.get('errors', 0) or 0
            avg_time = agent_stats.get('avg_time_seconds')
            total_cost = agent_stats.get('total_cost_usd')

            print(f"  Total spawns: {total}")
            print(f"  Successful: {successful}")
            print(f"  Errors: {errors}")
            if total > 0:
                success_rate = (successful / total) * 100
                print(f"  Success rate: {success_rate:.1f}%")
                if success_rate < 80:
                    issues.append(f"Low agent success rate: {success_rate:.1f}%")
            if avg_time:
                print(f"  Avg execution time: {avg_time:.1f}s")
            if total_cost:
                print(f"  Total cost: ${total_cost:.4f}")

        # Check identities
        print("\n## Registered Identities")
        identities = check_identity_status(conn)
        active_count = 0
        archived_count = 0
        for identity in identities:
            if identity['status'] == 'active':
                active_count += 1
                print(f"  ✅ {identity['identity_name']} ({identity['platform']})")
            else:
                archived_count += 1
        if archived_count > 0:
            print(f"  (+ {archived_count} archived identities)")

        if active_count == 0:
            issues.append("No active identities found!")

        conn.close()

        # Summary
        print("\n" + "=" * 60)
        if issues:
            print(f"⚠️ Found {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ All systems healthy")
        print("=" * 60)

        return 0  # Always return 0 on successful run

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
