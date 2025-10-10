"""
Sync PostgreSQL Claude Family data to MCP Memory Graph

Purpose: Populate the MCP memory server's knowledge graph from PostgreSQL
         at the start of each Claude session to restore persistent memory.

This script:
1. Loads all Claude identities from claude_family.identities
2. Loads universal knowledge from claude_family.shared_knowledge
3. Loads recent sessions from claude_family.session_history
4. Creates entities and relations in MCP memory graph

Usage: Run this automatically via Claude Desktop startup config

Date: 2025-10-10
Author: Claude Desktop & John
"""

import sys
import os
import io
import json

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add ai-workspace to path
sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
from config import POSTGRES_CONFIG

import psycopg2
from psycopg2.extras import RealDictCursor

def load_identities(conn):
    """Load all Claude identities"""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT identity_id, identity_name, platform, role_description,
               capabilities, personality_traits, status
        FROM claude_family.identities
        WHERE status = 'active'
    """)
    identities = [dict(row) for row in cur.fetchall()]
    cur.close()
    return identities

def load_knowledge(conn):
    """Load universal knowledge"""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT knowledge_id, knowledge_type, knowledge_category, title,
               description, applies_to_projects, confidence_level, times_applied
        FROM claude_family.shared_knowledge
        ORDER BY confidence_level DESC, times_applied DESC
        LIMIT 50
    """)
    knowledge = [dict(row) for row in cur.fetchall()]
    cur.close()
    return knowledge

def load_sessions(conn, days=30):
    """Load recent sessions"""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT session_id, identity_id, project_schema, project_name,
               session_start, session_end, tasks_completed, learnings_gained, session_summary
        FROM claude_family.session_history
        WHERE session_start >= NOW() - INTERVAL '%s days'
        ORDER BY session_start DESC
        LIMIT 100
    """, (days,))
    sessions = [dict(row) for row in cur.fetchall()]
    cur.close()
    return sessions

def create_mcp_entities(identities, knowledge, sessions):
    """
    Generate MCP memory tool calls to create entities

    Returns: List of tool call dictionaries ready for MCP
    """
    entities = []

    # Create identity entities
    for identity in identities:
        entities.append({
            "name": identity['identity_name'],
            "entityType": "claude_identity",
            "observations": [
                f"Platform: {identity['platform']}",
                f"Role: {identity['role_description']}",
                f"Capabilities: {json.dumps(identity.get('capabilities', {}))}",
                f"Personality: {json.dumps(identity.get('personality_traits', {}))}",
                f"Status: {identity['status']}"
            ]
        })

    # Create knowledge entities
    for k in knowledge:
        entities.append({
            "name": f"knowledge_{k['knowledge_id']}",
            "entityType": k['knowledge_type'],
            "observations": [
                f"Category: {k['knowledge_category']}",
                f"Title: {k['title']}",
                f"Description: {k['description']}",
                f"Applies to: {', '.join(k.get('applies_to_projects', ['all']))}",
                f"Confidence: {k['confidence_level']}/10",
                f"Times applied: {k['times_applied']}"
            ]
        })

    # Create session entities (recent ones only)
    for session in sessions[:20]:  # Only most recent 20
        entities.append({
            "name": f"session_{session['session_id']}",
            "entityType": "session",
            "observations": [
                f"Project: {session['project_name']} ({session['project_schema']})",
                f"Started: {session['session_start']}",
                f"Tasks: {', '.join(session.get('tasks_completed', [])[:3])}",
                f"Summary: {session.get('session_summary', 'No summary')[:200]}"
            ]
        })

    return entities

def create_mcp_relations(identities, sessions):
    """
    Generate MCP memory relations

    Returns: List of relation dictionaries
    """
    relations = []

    # Map identity_id to identity_name
    id_to_name = {str(i['identity_id']): i['identity_name'] for i in identities}

    # Create identity → session relations
    for session in sessions[:20]:
        identity_name = id_to_name.get(str(session['identity_id']))
        if identity_name:
            relations.append({
                "from": identity_name,
                "to": f"session_{session['session_id']}",
                "relationType": "worked_on"
            })

    # Create family relations (all identities know each other)
    identity_names = [i['identity_name'] for i in identities]
    for i, name1 in enumerate(identity_names):
        for name2 in identity_names[i+1:]:
            relations.append({
                "from": name1,
                "to": name2,
                "relationType": "collaborates_with"
            })

    return relations

def format_mcp_commands(entities, relations):
    """
    Format as human-readable MCP tool call instructions

    Since we can't directly call MCP tools from Python, we output
    instructions that Claude can execute
    """
    lines = []

    lines.append("=" * 80)
    lines.append("MCP MEMORY SYNC COMMANDS")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Execute these MCP tool calls to populate the memory graph:")
    lines.append("")

    # Split entities into batches of 10
    batch_size = 10
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i+batch_size]
        lines.append(f"--- Batch {i//batch_size + 1}: Create {len(batch)} entities ---")
        lines.append(json.dumps({"entities": batch}, indent=2))
        lines.append("")

    # Split relations into batches of 20
    batch_size = 20
    for i in range(0, len(relations), batch_size):
        batch = relations[i:i+batch_size]
        lines.append(f"--- Batch {i//batch_size + 1}: Create {len(batch)} relations ---")
        lines.append(json.dumps({"relations": batch}, indent=2))
        lines.append("")

    lines.append("=" * 80)
    lines.append(f"Total: {len(entities)} entities, {len(relations)} relations")
    lines.append("=" * 80)

    return '\n'.join(lines)

def main():
    """Main entry point"""
    try:
        print('🔄 Syncing PostgreSQL → MCP Memory Graph...\n')

        # Connect to PostgreSQL
        conn = psycopg2.connect(**POSTGRES_CONFIG)

        # Load data
        print('📊 Loading data from PostgreSQL...')
        identities = load_identities(conn)
        knowledge = load_knowledge(conn)
        sessions = load_sessions(conn, days=30)

        print(f'  ✅ {len(identities)} identities')
        print(f'  ✅ {len(knowledge)} knowledge items')
        print(f'  ✅ {len(sessions)} sessions')
        print()

        conn.close()

        # Generate MCP entities and relations
        print('🔨 Generating MCP entities and relations...')
        entities = create_mcp_entities(identities, knowledge, sessions)
        relations = create_mcp_relations(identities, sessions)

        print(f'  ✅ {len(entities)} entities to create')
        print(f'  ✅ {len(relations)} relations to create')
        print()

        # Save to files for Claude to execute
        # Save to ../postgres/data/
        script_dir = os.path.dirname(__file__)
        output_dir = os.path.join(os.path.dirname(script_dir), 'postgres', 'data')
        os.makedirs(output_dir, exist_ok=True)

        # Save entities
        entities_file = os.path.join(output_dir, 'mcp_sync_entities.json')
        with open(entities_file, 'w', encoding='utf-8') as f:
            json.dump({"entities": entities}, f, indent=2, default=str)
        print(f'💾 Entities saved to: {entities_file}')

        # Save relations
        relations_file = os.path.join(output_dir, 'mcp_sync_relations.json')
        with open(relations_file, 'w', encoding='utf-8') as f:
            json.dump({"relations": relations}, f, indent=2, default=str)
        print(f'💾 Relations saved to: {relations_file}')

        print()
        print('✅ Sync data prepared. Files ready for MCP import.')
        print()
        print('Next steps:')
        print('1. Claude will automatically read these JSON files')
        print('2. Claude will call MCP memory tools to populate the graph')
        print('3. Memory graph will be restored from PostgreSQL')

        return 0

    except Exception as e:
        print(f'\n❌ ERROR: {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
