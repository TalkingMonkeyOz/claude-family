"""
Session Workflow Compliance Checker
Validates that Claude instances are following session start/end protocols
"""

import psycopg2
from datetime import datetime, timedelta
from tabulate import tabulate

# Database connection
conn = psycopg2.connect(
    dbname="ai_company_foundation",
    user="postgres",
    password="",  # Will prompt if needed
    host="localhost"
)

def check_unclosed_sessions():
    """Find sessions that weren't properly closed"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                i.identity_name,
                sh.project_name,
                sh.session_start,
                EXTRACT(EPOCH FROM (NOW() - sh.session_start))/3600 as hours_open
            FROM claude_family.session_history sh
            LEFT JOIN claude_family.identities i ON sh.identity_id = i.identity_id
            WHERE sh.session_end IS NULL
            ORDER BY sh.session_start DESC;
        """)

        unclosed = cur.fetchall()

        if unclosed:
            print("\n🚨 UNCLOSED SESSIONS (Protocol Violation)")
            print("="*80)
            headers = ["Identity", "Project", "Started", "Hours Open"]
            print(tabulate(unclosed, headers=headers, tablefmt="grid"))
            print(f"\n⚠️  Found {len(unclosed)} unclosed session(s)")
            print("💡 Action: Run /session-end to close these sessions\n")
        else:
            print("\n✅ No unclosed sessions found\n")

def check_recent_compliance():
    """Check compliance rate for last 7 days"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                i.identity_name,
                COUNT(*) as total_sessions,
                COUNT(*) FILTER (WHERE sh.session_end IS NOT NULL) as closed_sessions,
                COUNT(*) FILTER (WHERE sh.session_summary IS NOT NULL) as documented_sessions,
                ROUND(100.0 * COUNT(*) FILTER (WHERE sh.session_end IS NOT NULL) / COUNT(*), 1) as closure_rate,
                ROUND(100.0 * COUNT(*) FILTER (WHERE sh.session_summary IS NOT NULL) / COUNT(*), 1) as documentation_rate
            FROM claude_family.session_history sh
            LEFT JOIN claude_family.identities i ON sh.identity_id = i.identity_id
            WHERE sh.session_start > NOW() - INTERVAL '7 days'
            GROUP BY i.identity_name
            ORDER BY total_sessions DESC;
        """)

        stats = cur.fetchall()

        if stats:
            print("\n📊 7-DAY COMPLIANCE REPORT")
            print("="*80)
            headers = ["Identity", "Total", "Closed", "Documented", "Closure %", "Docs %"]
            print(tabulate(stats, headers=headers, tablefmt="grid"))

            # Calculate overall compliance
            total = sum(row[1] for row in stats)
            closed = sum(row[2] for row in stats)
            documented = sum(row[3] for row in stats)

            overall_closure = (closed / total * 100) if total > 0 else 0
            overall_docs = (documented / total * 100) if total > 0 else 0

            print(f"\n📈 OVERALL COMPLIANCE:")
            print(f"   Closure Rate: {overall_closure:.1f}% (Target: 100%)")
            print(f"   Documentation Rate: {overall_docs:.1f}% (Target: 100%)")

            if overall_closure < 90:
                print(f"\n⚠️  WARNING: Closure rate below 90%!")
            if overall_docs < 80:
                print(f"\n⚠️  WARNING: Documentation rate below 80%!")
            print()
        else:
            print("\n⚠️  No sessions found in last 7 days\n")

def check_orphaned_sessions():
    """Find sessions with NULL identity (manual SQL without proper workflow)"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                project_name,
                session_start,
                session_summary
            FROM claude_family.session_history
            WHERE identity_id IS NULL
              AND session_start > NOW() - INTERVAL '14 days'
            ORDER BY session_start DESC
            LIMIT 10;
        """)

        orphaned = cur.fetchall()

        if orphaned:
            print("\n⚠️  ORPHANED SESSIONS (No Identity)")
            print("="*80)
            print("These sessions were created manually without using /session-start")
            headers = ["Project", "Started", "Summary"]
            print(tabulate(orphaned, headers=headers, tablefmt="grid"))
            print(f"\n💡 Found {len(orphaned)} orphaned session(s)")
            print("💡 Action: Use /session-start and /session-end commands going forward\n")
        else:
            print("\n✅ No orphaned sessions found\n")

def main():
    print("\n" + "="*80)
    print(" SESSION WORKFLOW COMPLIANCE CHECK")
    print("="*80)

    try:
        check_unclosed_sessions()
        check_recent_compliance()
        check_orphaned_sessions()

        print("="*80)
        print("✅ Compliance check complete")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}\n")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
