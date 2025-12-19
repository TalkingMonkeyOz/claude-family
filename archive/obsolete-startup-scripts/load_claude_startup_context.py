"""
Claude Family Unified Startup Context Loader

Purpose: Load complete identity and context for any Claude instance at session startup
Usage: Run at the beginning of every Claude session to load:
  1. Identity (who am I?)
  2. Universal knowledge (what do I know across all projects?)
  3. Recent session history (what did I work on recently?)
  4. Other Claudes' activity (what did my family members do?)
  5. Current project context (project-specific facts/constraints)

Date: 2025-10-10
Author: Claude Desktop & John
"""

import sys
import os
import io
from datetime import datetime, timedelta

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add ai-workspace to path
sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
from config import POSTGRES_CONFIG

import psycopg2
from psycopg2.extras import RealDictCursor

def detect_platform():
    """
    Detect which Claude instance is running
    Returns: 'desktop', 'cursor', 'vscode', 'claude-code', or 'unknown'
    """
    # For now, default to desktop
    # TODO: Add platform detection logic (check environment variables, process names, etc.)
    return 'claude-code-console' if os.environ.get('CLAUDECODE') or os.environ.get('CLAUDE_CODE') or os.environ.get('CLAUDE_CODE_SESSION') else 'desktop'

def detect_current_project():
    """
    Detect which project we're working on based on current directory
    Returns: (project_schema, project_name) or (None, None)
    """
    cwd = os.getcwd().lower()

    # Check for Nimbus project
    if 'nimbus' in cwd or 'nimbus-user-loader' in cwd:
        return ('nimbus_context', 'Nimbus User Loader')

    # Check for Tax Calculator
    if 'tax-calculator' in cwd or 'tax' in cwd:
        return ('public', 'Tax Calculator')

    # Check for Diana AI Company
    if 'ai-company' in cwd or 'diana' in cwd:
        return ('public', 'Diana AI Company Controller')

    # Default: working directory project
    return (None, 'Current Project')

def load_identity(conn, platform):
    """Load Claude identity from database by platform"""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Query for active identity matching this platform
    cur.execute("""
        SELECT
            identity_id,
            identity_name,
            platform,
            role_description,
            capabilities,
            personality_traits,
            last_active_at
        FROM claude_family.identities
        WHERE platform = %s
        AND status = 'active'
        ORDER BY last_active_at DESC NULLS LAST
        LIMIT 1
    """, (platform,))

    identity = cur.fetchone()

    # Update last_active_at if found
    if identity:
        cur.execute("""
            UPDATE claude_family.identities
            SET last_active_at = CURRENT_TIMESTAMP
            WHERE identity_id = %s
        """, (identity['identity_id'],))
        conn.commit()

    cur.close()

    return dict(identity) if identity else None

def load_universal_knowledge(conn, project_name=None, limit=20):
    """Load universal knowledge that applies to all or specific project"""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT * FROM claude_family.get_universal_knowledge(%s, 5, %s)
    """, (project_name, limit))

    knowledge = [dict(row) for row in cur.fetchall()]
    cur.close()

    return knowledge

def load_recent_sessions(conn, identity_name=None, days=7, limit=5):
    """Load recent session history for this Claude or all Claudes"""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT * FROM claude_family.get_recent_sessions(%s, %s, %s)
    """, (identity_name, days, limit))

    sessions = [dict(row) for row in cur.fetchall()]
    cur.close()

    return sessions

def load_project_context(conn, project_schema, project_name):
    """Load project-specific context if working on known project"""
    if project_schema == 'nimbus_context':
        return load_nimbus_context(conn)
    elif project_schema == 'public' and 'Diana' in project_name:
        return load_diana_context(conn)
    else:
        return None

def load_nimbus_context(conn):
    """Load Nimbus User Loader specific context"""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get critical facts
    cur.execute("""
        SELECT fact_type, fact_category, title, description, importance
        FROM nimbus_context.project_facts
        WHERE importance <= 3
        ORDER BY importance ASC, created_at DESC
        LIMIT 10
    """)

    facts = [dict(row) for row in cur.fetchall()]

    # Get recent learnings
    cur.execute("""
        SELECT learning_type, lesson_learned, outcome
        FROM nimbus_context.project_learnings
        ORDER BY created_at DESC
        LIMIT 5
    """)

    learnings = [dict(row) for row in cur.fetchall()]

    cur.close()

    return {
        'facts': facts,
        'learnings': learnings
    }

def load_diana_context(conn):
    """Load Diana's company status"""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get Diana's identity
    cur.execute("""
        SELECT identity_id, capabilities
        FROM claude_family.identities
        WHERE identity_name = 'diana'
    """)

    diana = cur.fetchone()

    if not diana:
        return None

    # Get recent company activity
    cur.execute("""
        SELECT session_type, created_at, metadata
        FROM public.ai_sessions
        WHERE initiated_by_identity = %s
        ORDER BY created_at DESC
        LIMIT 5
    """, (diana['identity_id'],))

    sessions = [dict(row) for row in cur.fetchall()]

    cur.close()

    return {
        'capabilities': diana['capabilities'],
        'recent_sessions': sessions
    }

def format_startup_brief(identity, universal_knowledge, my_sessions, other_sessions, project_context):
    """Generate formatted startup brief"""
    lines = []

    # Header
    lines.append('━' * 80)
    lines.append(f'🤖 IDENTITY LOADED: {identity["identity_name"]}')
    lines.append('━' * 80)
    lines.append('')

    # Identity section
    lines.append('WHO AM I:')
    lines.append(f'  Platform: {identity["platform"]}')
    lines.append(f'  Role: {identity["role_description"][:100]}...' if len(identity["role_description"]) > 100 else f'  Role: {identity["role_description"]}')
    lines.append('')

    # Capabilities
    capabilities = identity.get('capabilities', {})
    if capabilities:
        lines.append('MY CAPABILITIES:')
        if capabilities.get('mcp_servers'):
            lines.append(f'  ✅ MCP Servers: {", ".join(capabilities["mcp_servers"][:3])}{"..." if len(capabilities["mcp_servers"]) > 3 else ""}')
        if capabilities.get('has_own_company'):
            lines.append(f'  ✅ Has AI Company: {capabilities.get("company_system", "Unknown")} in {capabilities.get("company_schema", "?")} schema')
        if capabilities.get('can_run_commands'):
            lines.append('  ✅ Can run system commands')
        if capabilities.get('file_operations'):
            lines.append('  ✅ File operations enabled')
        lines.append('')

    # Universal knowledge
    lines.append('━' * 80)
    lines.append(f'📚 UNIVERSAL KNOWLEDGE (Top {min(len(universal_knowledge), 5)} most relevant)')
    lines.append('━' * 80)
    lines.append('')

    for i, k in enumerate(universal_knowledge[:5], 1):
        confidence_bar = '█' * k['confidence_level'] + '░' * (10 - k['confidence_level'])
        lines.append(f'{i}. [{k["knowledge_type"].upper()}] {k["title"]}')
        lines.append(f'   Category: {k["knowledge_category"]} | Confidence: {confidence_bar} ({k["confidence_level"]}/10) | Applied: {k["times_applied"]}x')
        lines.append(f'   {k["description"][:120]}...' if len(k["description"]) > 120 else f'   {k["description"]}')
        lines.append('')

    # My recent sessions
    if my_sessions:
        lines.append('━' * 80)
        lines.append(f'📅 MY RECENT SESSIONS (Last {len(my_sessions)})')
        lines.append('━' * 80)
        lines.append('')

        for session in my_sessions:
            session_date = session['session_start'].strftime('%Y-%m-%d %H:%M') if session['session_start'] else 'Unknown'
            lines.append(f'• {session_date} - {session["project_name"]} ({session["project_schema"]})')
            if session['tasks_completed']:
                for task in session['tasks_completed'][:3]:
                    lines.append(f'  ✅ {task}')
            if session['session_summary']:
                lines.append(f'  Summary: {session["session_summary"][:100]}...' if len(session["session_summary"]) > 100 else f'  Summary: {session["session_summary"]}')
            lines.append('')

    # Other Claudes' activity
    if other_sessions:
        lines.append('━' * 80)
        lines.append('👥 OTHER CLAUDE FAMILY MEMBERS')
        lines.append('━' * 80)
        lines.append('')

        # Group by identity
        by_identity = {}
        for session in other_sessions:
            name = session['identity_name']
            if name not in by_identity:
                by_identity[name] = {
                    'role': session['role_description'],
                    'sessions': []
                }
            by_identity[name]['sessions'].append(session)

        for name, data in by_identity.items():
            role = data['role'][:50] + '...' if len(data['role']) > 50 else data['role']
            lines.append(f'• {name} ({role})')
            lines.append(f'  Last active: {data["sessions"][0]["session_start"].strftime("%Y-%m-%d") if data["sessions"][0]["session_start"] else "Never"}')
            lines.append(f'  Recent sessions: {len(data["sessions"])}')
            lines.append('')

    # Project context
    if project_context:
        lines.append('━' * 80)
        lines.append('📋 CURRENT PROJECT CONTEXT')
        lines.append('━' * 80)
        lines.append('')

        if 'facts' in project_context:
            lines.append('CRITICAL FACTS:')
            for i, fact in enumerate(project_context['facts'][:5], 1):
                importance_label = ['[CRITICAL]', '[HIGH]', '[MEDIUM]'][min(fact['importance'] - 1, 2)]
                lines.append(f'{i}. {importance_label} {fact["title"]}')
                lines.append(f'   {fact["description"][:100]}...' if len(fact["description"]) > 100 else f'   {fact["description"]}')
            lines.append('')

        if 'learnings' in project_context:
            lines.append('RECENT LEARNINGS:')
            for learning in project_context['learnings'][:3]:
                lines.append(f'• [{learning["learning_type"].upper()}] {learning["lesson_learned"][:80]}...' if len(learning["lesson_learned"]) > 80 else f'• [{learning["learning_type"].upper()}] {learning["lesson_learned"]}')
            lines.append('')

        if 'capabilities' in project_context:
            # Diana's company info
            lines.append('DIANA\'S COMPANY:')
            caps = project_context['capabilities']
            lines.append(f'  System: {caps.get("company_system", "AI Company Controller")}')
            lines.append(f'  Departments: {", ".join(caps.get("departments", []))}')
            lines.append(f'  Status: Can be activated when complex orchestration needed')
            lines.append('')

    # Footer
    lines.append('━' * 80)
    lines.append('✅ READY TO WORK')
    lines.append('━' * 80)
    lines.append('')
    lines.append('Context loaded successfully. All critical knowledge and constraints available.')
    lines.append(f'Session started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append('')

    return '\n'.join(lines)

def main():
    """Main entry point"""
    try:
        print('🔄 Loading Claude Family startup context...\n')

        # Connect to database
        conn = psycopg2.connect(**POSTGRES_CONFIG)

        # Detect platform and project
        platform = detect_platform()
        project_schema, project_name = detect_current_project()

        print(f'Platform: {platform}')
        print(f'Current directory: {os.getcwd()}')
        if project_schema:
            print(f'Detected project: {project_name} ({project_schema} schema)')
        print()

        # Load identity
        identity = load_identity(conn, platform)
        if not identity:
            print(f'❌ Identity not found for platform: {platform}')
            print('Have you run 02_seed_claude_identities.sql?')
            return 1

        # Load universal knowledge
        universal_knowledge = load_universal_knowledge(conn, project_name, limit=20)

        # Load my recent sessions
        my_sessions = load_recent_sessions(conn, identity['identity_name'], days=7, limit=5)

        # Load other Claudes' sessions
        all_sessions = load_recent_sessions(conn, None, days=7, limit=20)
        other_sessions = [s for s in all_sessions if s['identity_name'] != identity['identity_name']]

        # Load project-specific context
        project_context = None
        if project_schema:
            project_context = load_project_context(conn, project_schema, project_name)

        # Close connection
        conn.close()

        # Generate and print startup brief
        brief = format_startup_brief(identity, universal_knowledge, my_sessions, other_sessions, project_context)
        print(brief)

        # Save to file (optional)
        script_dir = os.path.dirname(__file__)
        logs_dir = os.path.join(os.path.dirname(script_dir), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        output_file = os.path.join(logs_dir, f'startup_context_{identity["identity_name"]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(brief)
        print(f'💾 Startup context saved to: {output_file}')

        return 0

    except Exception as e:
        print(f'\n❌ ERROR: {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
