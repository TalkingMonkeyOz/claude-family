"""
Show Startup Notification with Claude Family Context

Displays a brief notification/popup showing:
- Your identity
- Top 3 universal knowledge items
- Recent sessions summary

Auto-closes after 10 seconds or when clicked.

Usage: Run at Windows startup via STARTUP.bat
"""

import sys
import os
import io
from datetime import datetime

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import POSTGRES_CONFIG

import psycopg2
from psycopg2.extras import RealDictCursor

def load_identity(conn):
    """Load desktop identity"""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM claude_family.get_identity(%s)", ('claude-desktop-001',))
    identity = dict(cur.fetchone()) if cur.rowcount > 0 else None
    cur.close()
    return identity

def load_top_knowledge(conn, limit=3):
    """Load top universal knowledge"""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM claude_family.get_universal_knowledge(NULL, 5, %s)
    """, (limit,))
    knowledge = [dict(row) for row in cur.fetchall()]
    cur.close()
    return knowledge

def show_notification_windows(title, message, duration=10):
    """Show Windows 10 toast notification"""
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            message,
            duration=duration,
            threaded=False
        )
    except ImportError:
        # Fallback to message box if toast not available
        import ctypes
        MessageBox = ctypes.windll.user32.MessageBoxW
        MessageBox(None, message, title, 0x40 | 0x1000)  # MB_ICONINFORMATION | MB_SYSTEMMODAL

def create_notification_message(identity, knowledge):
    """Create brief notification message"""
    lines = []

    # Identity
    lines.append(f"🤖 {identity['identity_name']}")
    lines.append(f"Role: {identity['role_description'][:50]}...")
    lines.append("")

    # Top knowledge
    lines.append("📚 Top Universal Knowledge:")
    for i, k in enumerate(knowledge[:3], 1):
        lines.append(f"{i}. [{k['knowledge_type'].upper()}] {k['title'][:40]}...")

    lines.append("")
    lines.append(f"✅ Context loaded at {datetime.now().strftime('%H:%M:%S')}")
    lines.append("Ready to work!")

    return '\n'.join(lines)

def main():
    """Show startup notification"""
    try:
        # Connect to database
        conn = psycopg2.connect(**POSTGRES_CONFIG)

        # Load data
        identity = load_identity(conn)
        if not identity:
            print("❌ Identity not found")
            return 1

        knowledge = load_top_knowledge(conn, limit=3)

        conn.close()

        # Create notification message
        message = create_notification_message(identity, knowledge)

        # Show notification
        print("Showing startup notification...")
        show_notification_windows(
            "Claude Family - Context Loaded",
            message,
            duration=10
        )

        print("✅ Notification displayed")
        return 0

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
