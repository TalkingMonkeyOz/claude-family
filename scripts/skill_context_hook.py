#!/usr/bin/env python3
"""
Skill Context Hook - PostToolUse Hook for Claude Code

When a skill is loaded via the Skill tool, automatically surfaces related
resources (entities, workfiles, memories) as additional context.

Hook Event: PostToolUse
Triggers On: tool_name='Skill'

What it does:
1. Extracts skill name from Skill tool_input
2. Looks up skill entity in entity catalog
3. Finds resource_links for the skill entity
4. Finds workfiles in a component matching the skill name
5. Returns assembled context as additionalContext

Author: Claude Family
Date: 2026-04-10
"""

import json
import os
import sys
import logging
from pathlib import Path

# Setup file-based logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('skill_context')

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg

_psycopg_mod, PSYCOPG_VERSION, _, _ = detect_psycopg()


def empty_response():
    print(json.dumps({"additionalContext": ""}))


def get_skill_context(skill_name: str) -> str:
    """Look up related context for a skill."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Find the skill entity
        cur.execute("""
            SELECT e.entity_id::text, e.properties->>'description' as description
            FROM claude.entities e
            JOIN claude.entity_types et ON e.entity_type_id = et.type_id
            WHERE et.type_name = 'skill'
              AND e.properties->>'name' = %s
              AND NOT e.is_archived
            LIMIT 1
        """, (skill_name,))
        skill_entity = cur.fetchone()

        if not skill_entity:
            return ""

        entity_id = skill_entity['entity_id']
        context_parts = []

        # 2. Check resource_links for this skill entity
        cur.execute("""
            SELECT rl.to_type, rl.to_id::text, rl.link_type, rl.strength
            FROM claude.resource_links rl
            WHERE rl.from_type = 'entity' AND rl.from_id = %s::uuid
            UNION ALL
            SELECT rl.from_type, rl.from_id::text, rl.link_type, rl.strength
            FROM claude.resource_links rl
            WHERE rl.to_type = 'entity' AND rl.to_id = %s::uuid
            ORDER BY strength DESC
            LIMIT 10
        """, (entity_id, entity_id))
        links = cur.fetchall()

        if links:
            linked_summaries = []
            for link in links:
                res_type = link['to_type'] if 'to_type' in link else link[0]
                res_id = link['to_id'] if 'to_id' in link else link[1]
                link_type = link['link_type'] if 'link_type' in link else link[2]

                if res_type == 'entity':
                    cur.execute("""
                        SELECT COALESCE(summary, properties->>'name') as summary
                        FROM claude.entities WHERE entity_id = %s::uuid
                    """, (res_id,))
                    row = cur.fetchone()
                    if row and row['summary']:
                        linked_summaries.append(f"  - [{link_type}] {row['summary']}")
                elif res_type == 'workfile':
                    cur.execute("""
                        SELECT component, title FROM claude.project_workfiles
                        WHERE workfile_id = %s::uuid
                    """, (res_id,))
                    row = cur.fetchone()
                    if row:
                        linked_summaries.append(
                            f"  - [{link_type}] Workfile: {row['component']}/{row['title']}"
                        )

            if linked_summaries:
                context_parts.append(
                    "**Linked Resources:**\n" + "\n".join(linked_summaries)
                )

        # 3. Check for workfiles in a component matching the skill name
        cur.execute("""
            SELECT title, workfile_type, LEFT(content, 200) as preview
            FROM claude.project_workfiles
            WHERE component = %s AND is_active = true
            ORDER BY updated_at DESC
            LIMIT 3
        """, (skill_name,))
        workfiles = cur.fetchall()

        if workfiles:
            wf_parts = []
            for wf in workfiles:
                title = wf['title']
                wf_type = wf['workfile_type']
                preview = wf['preview']
                wf_parts.append(f"  - **{title}** ({wf_type}): {preview}...")
            context_parts.append(
                f"**Working Notes ({skill_name}):**\n" + "\n".join(wf_parts)
            )

        if not context_parts:
            return ""

        return (
            f"<skill-context skill=\"{skill_name}\">\n"
            + "\n\n".join(context_parts)
            + "\n</skill-context>"
        )

    except Exception as e:
        logger.error(f"Error getting skill context for '{skill_name}': {e}")
        return ""
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def main():
    try:
        hook_input = json.load(sys.stdin)
        tool_name = hook_input.get('tool_name')

        if tool_name != 'Skill':
            empty_response()
            return

        tool_input = hook_input.get('tool_input', {})
        skill_name = tool_input.get('skill', '')

        if not skill_name:
            empty_response()
            return

        # Strip any namespace prefix (e.g., "ms-office-suite:pdf" -> "pdf")
        if ':' in skill_name:
            skill_name = skill_name.split(':')[-1]

        logger.info(f"Skill activated: {skill_name}")

        context = get_skill_context(skill_name)

        if context:
            logger.info(f"Skill context found for '{skill_name}': {len(context)} chars")
            print(json.dumps({"additionalContext": context}))
        else:
            empty_response()

    except Exception as e:
        logger.error(f"Skill context hook error: {e}")
        empty_response()


if __name__ == "__main__":
    main()
