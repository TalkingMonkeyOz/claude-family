#!/usr/bin/env python3
"""
Research script: Pull last session info, messages, and open feedback.
"""
import sys
import json
from pathlib import Path

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_db_connection

conn = get_db_connection()
if not conn:
    print("ERROR: Could not connect to database")
    sys.exit(1)

cur = conn.cursor()

print("=" * 70)
print("RECENT SESSIONS (last 5)")
print("=" * 70)
try:
    cur.execute("""
        SELECT
            s.session_id::text,
            s.created_at,
            s.ended_at,
            s.status,
            s.project_name,
            s.summary,
            s.identity_name
        FROM claude.sessions s
        ORDER BY s.created_at DESC
        LIMIT 5
    """)
    rows = cur.fetchall()
    for row in rows:
        d = dict(row)
        print(f"\nSession ID: {d.get('session_id')}")
        print(f"Project:    {d.get('project_name', 'N/A')}")
        print(f"Identity:   {d.get('identity_name', 'N/A')}")
        print(f"Created:    {d.get('created_at')}")
        print(f"Ended:      {d.get('ended_at')}")
        print(f"Status:     {d.get('status')}")
        if d.get('summary'):
            summary = d['summary']
            if len(summary) > 1000:
                summary = summary[:1000] + "... [TRUNCATED]"
            print(f"Summary:\n{summary}")
        print("-" * 50)
except Exception as e:
    print(f"ERROR querying sessions: {e}")
    # Try alternate column name
    try:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'claude' AND table_name = 'sessions'
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
        print("Sessions table columns:", [dict(c)['column_name'] for c in cols])
    except Exception as e2:
        print(f"Could not get columns: {e2}")

print("\n" + "=" * 70)
print("INTER-CLAUDE MESSAGES (last 20, all statuses)")
print("=" * 70)
try:
    cur.execute("""
        SELECT
            message_id::text,
            created_at,
            status,
            from_project,
            to_project,
            message_type,
            priority,
            subject,
            body,
            thread_id::text
        FROM claude.messages
        ORDER BY created_at DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    if not rows:
        print("No messages found in claude.messages")
    else:
        for row in rows:
            d = dict(row)
            print(f"\nMsg ID:    {d.get('message_id')}")
            print(f"Date:      {d.get('created_at')}")
            print(f"From:      {d.get('from_project', 'N/A')}")
            print(f"To:        {d.get('to_project', 'N/A')}")
            print(f"Type:      {d.get('message_type', 'N/A')}")
            print(f"Priority:  {d.get('priority', 'N/A')}")
            print(f"Status:    {d.get('status')}")
            print(f"Subject:   {d.get('subject', 'N/A')}")
            if d.get('thread_id'):
                print(f"Thread:    {d.get('thread_id')}")
            body = d.get('body', '')
            if body:
                if len(body) > 1500:
                    body = body[:1500] + "... [TRUNCATED]"
                print(f"Body:\n{body}")
            print("-" * 50)
except Exception as e:
    print(f"ERROR querying messages: {e}")
    try:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'claude' AND table_name = 'messages'
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
        print("Messages table columns:", [dict(c)['column_name'] for c in cols])
    except Exception as e2:
        print(f"Could not get columns: {e2}")

print("\n" + "=" * 70)
print("OPEN FEEDBACK (status not resolved/wont_fix/duplicate)")
print("=" * 70)
try:
    cur.execute("""
        SELECT
            f.id,
            f.created_at,
            f.feedback_type,
            f.status,
            f.priority,
            f.title,
            f.description,
            p.project_name
        FROM claude.feedback f
        LEFT JOIN claude.projects p ON f.project_id = p.project_id
        WHERE f.status NOT IN ('resolved', 'wont_fix', 'duplicate')
        ORDER BY f.created_at DESC
        LIMIT 30
    """)
    rows = cur.fetchall()
    if not rows:
        print("No open feedback items found")
    else:
        for row in rows:
            d = dict(row)
            print(f"\nFeedback ID: {d.get('id')}")
            print(f"Date:        {d.get('created_at')}")
            print(f"Project:     {d.get('project_name', 'N/A')}")
            print(f"Type:        {d.get('feedback_type')}")
            print(f"Priority:    {d.get('priority')}")
            print(f"Status:      {d.get('status')}")
            print(f"Title:       {d.get('title')}")
            if d.get('description'):
                desc = d['description']
                if len(desc) > 500:
                    desc = desc[:500] + "... [TRUNCATED]"
                print(f"Description: {desc}")
            print("-" * 50)
except Exception as e:
    print(f"ERROR querying feedback: {e}")

print("\n" + "=" * 70)
print("OPEN BUILD TASKS (not completed/cancelled)")
print("=" * 70)
try:
    cur.execute("""
        SELECT
            bt.id,
            bt.task_code,
            bt.task_name,
            bt.status,
            bt.priority,
            bt.created_at,
            f.feature_name,
            f.feature_code,
            p.project_name
        FROM claude.build_tasks bt
        LEFT JOIN claude.features f ON bt.feature_id = f.id
        LEFT JOIN claude.projects p ON f.project_id = p.project_id
        WHERE bt.status NOT IN ('completed', 'cancelled')
        ORDER BY bt.created_at DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    if not rows:
        print("No open build tasks")
    else:
        for row in rows:
            d = dict(row)
            print(f"\nTask Code: {d.get('task_code', d['id'])}")
            print(f"Name:      {d.get('task_name')}")
            print(f"Status:    {d.get('status')}")
            print(f"Priority:  {d.get('priority')}")
            print(f"Feature:   {d.get('feature_name', 'N/A')} ({d.get('feature_code', 'N/A')})")
            print(f"Project:   {d.get('project_name', 'N/A')}")
            print(f"Created:   {d.get('created_at')}")
            print("-" * 50)
except Exception as e:
    print(f"ERROR querying build_tasks: {e}")

print("\n" + "=" * 70)
print("RECENT SESSION FACTS (last 48 hours)")
print("=" * 70)
try:
    cur.execute("""
        SELECT
            sf.fact_key,
            sf.fact_value,
            sf.fact_type,
            sf.created_at,
            sf.session_id::text
        FROM claude.session_facts sf
        WHERE sf.created_at > NOW() - INTERVAL '48 hours'
        AND sf.is_sensitive = false
        ORDER BY sf.created_at DESC
        LIMIT 30
    """)
    rows = cur.fetchall()
    if not rows:
        print("No recent session facts")
    else:
        for row in rows:
            d = dict(row)
            val = d.get('fact_value', '')
            if val and len(val) > 400:
                val = val[:400] + "... [TRUNCATED]"
            print(f"[{d.get('created_at')}] Key: {d.get('fact_key')} (type: {d.get('fact_type')})")
            print(f"  Session: {d.get('session_id')}")
            print(f"  Value: {val}")
except Exception as e:
    print(f"ERROR querying session_facts: {e}")

print("\n" + "=" * 70)
print("IN-PROGRESS FEATURES (status = in_progress)")
print("=" * 70)
try:
    cur.execute("""
        SELECT
            f.id,
            f.feature_code,
            f.feature_name,
            f.status,
            f.priority,
            f.created_at,
            p.project_name,
            f.description
        FROM claude.features f
        LEFT JOIN claude.projects p ON f.project_id = p.project_id
        WHERE f.status IN ('in_progress', 'planned')
        ORDER BY f.created_at DESC
        LIMIT 15
    """)
    rows = cur.fetchall()
    if not rows:
        print("No in-progress features")
    else:
        for row in rows:
            d = dict(row)
            print(f"\nFeature: {d.get('feature_code')} - {d.get('feature_name')}")
            print(f"Status:  {d.get('status')}")
            print(f"Project: {d.get('project_name', 'N/A')}")
            print(f"Created: {d.get('created_at')}")
            if d.get('description'):
                desc = d['description']
                if len(desc) > 300:
                    desc = desc[:300] + "... [TRUNCATED]"
                print(f"Desc:    {desc}")
            print("-" * 50)
except Exception as e:
    print(f"ERROR querying features: {e}")

conn.close()
print("\nDone.")
