#!/usr/bin/env python3
"""End current session and log summary to PostgreSQL."""
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

# Database connection
DB_CONFIG = {
    'dbname': 'ai_company_foundation',
    'user': 'postgres',
    'password': 'Blaster5',
    'host': 'localhost',
    'port': 5432
}

def end_session():
    """Close the current session with summary."""

    # Session summary
    summary = """Build Tracker v0.3.1 - Project-Feature Linking & Grey Box Fix Attempts

COMPLETED:
- Added project_id column to features table with foreign key
- Implemented get_features_by_project() with UUID text casting
- Created feature_modal.py for creating new features
- Wired "New Feature" button to open modal
- Enhanced component display with file paths and planned functions
- Fixed border syntax issues (ft.border.only)
- Incremented version to v0.3.1 in app title and batch file

ATTEMPTED (Grey Box Issue - 4 iterations):
1. Removed scroll mode from feature list Column
2. Removed expand=True from content Column
3. Removed bgcolor and height from tab container in main.py
4. Flattened Column structure using list concatenation

STATUS: Grey box still present per user - needs different approach

NEXT STEPS:
- Try complete UI rebuild with different layout (ListView instead of Column)
- Create component and task modals once grey box is resolved
- Wire up filter dropdowns
"""

    outcome = "partial-success"

    files_modified = [
        'src/database/build_tracker.py',
        'src/views/build_tracker_tab.py',
        'src/views/build_tracker_tab.py.backup',
        'src/views/modals/feature_modal.py',
        'src/views/modals/__init__.py',
        'src/main_v0.3.0_simple.py',
        'BUILD_STATUS_v0.3.1.md',
        'C:/Users/johnd/OneDrive/Desktop/claude-mission-control.bat'
    ]

    # Database changes
    schema_changes = [
        'ALTER TABLE claude_mission_control.features ADD COLUMN project_id UUID',
        'CREATE OR REPLACE VIEW claude_mission_control.v_feature_progress (added project info)'
    ]

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get latest session
        cur.execute("""
            SELECT id, session_start, project_name
            FROM claude.sessions
            WHERE identity_id = 5
            ORDER BY session_start DESC
            LIMIT 1
        """)

        session = cur.fetchone()

        if not session:
            print("ERROR: No open session found for identity_id=5")
            return False

        session_id = session['id']
        print(f"Found session {session_id}: {session['project_name']} started at {session['session_start']}")

        # Update session
        cur.execute("""
            UPDATE claude.sessions
            SET
                session_end = NOW(),
                summary = %s,
                files_modified = %s,
                outcome = %s,
                tokens_used = 72000
            WHERE id = %s
        """, (summary, files_modified, outcome, session_id))

        conn.commit()

        print(f"✅ Session {session_id} closed successfully")
        print(f"   Duration: {session['session_start']} to NOW()")
        print(f"   Files modified: {len(files_modified)}")
        print(f"   Outcome: {outcome}")

        cur.close()
        conn.close()

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = end_session()
    sys.exit(0 if success else 1)
