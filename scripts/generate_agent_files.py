#!/usr/bin/env python3
"""
Generate .claude/agents/*.md files from database agent definitions.

Reads from claude.agent_definitions and generates native Claude Code agent
definition files with YAML frontmatter for deployment to project directories.

Usage:
    python scripts/generate_agent_files.py [project_name] [--all] [--dry-run]

    project_name: Generate for specific project (default: current directory)
    --all: Generate for ALL active projects
    --dry-run: Show what would be generated without writing files

Database is source of truth. Generated files are deployment artifacts.

Author: Claude Family
Date: 2026-02-08
"""

import json
import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_VERSION = 3
except ImportError:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG_VERSION = 2


def _get_pg_config():
    """Read PostgreSQL config from pgpass file."""
    pgpass_locations = [
        Path.home() / ".pgpass",
        Path.home() / "AppData" / "Roaming" / "postgresql" / "pgpass.conf"
    ]
    for pgpass_path in pgpass_locations:
        if pgpass_path.exists():
            try:
                content = pgpass_path.read_text()
                for line in content.strip().split('\n'):
                    if 'ai_company_foundation' in line:
                        parts = line.split(':')
                        if len(parts) >= 5:
                            return {
                                'host': parts[0],
                                'port': parts[1] or '5432',
                                'database': parts[2],
                                'user': parts[3],
                                'password': parts[4]
                            }
            except Exception:
                pass
    return {
        'host': 'localhost', 'port': '5432',
        'database': 'ai_company_foundation',
        'user': 'postgres', 'password': '05OX79HNFCjQwhotDjVx'
    }


_PG_CONFIG = _get_pg_config()
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}:{_PG_CONFIG['port']}/{_PG_CONFIG['database']}"
)


def get_db_connection():
    if PSYCOPG_VERSION == 3:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    else:
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = RealDictCursor
        return conn


def get_agents_for_project(conn, project_name: str) -> List[Dict]:
    """Get agent definitions applicable to a project (global + type + project-specific)."""
    cur = conn.cursor()

    # Get project type
    cur.execute("""
        SELECT project_type FROM claude.workspaces
        WHERE project_name = %s AND is_active = true
    """, (project_name,))
    row = cur.fetchone()
    project_type = dict(row)['project_type'] if row else None

    # Fetch agents: global, matching project_type, or project-specific
    cur.execute("""
        SELECT * FROM claude.agent_definitions
        WHERE is_active = true
          AND (
              scope = 'global'
              OR (scope = 'project_type' AND scope_ref = %s)
              OR (scope = 'project' AND scope_ref = %s)
          )
        ORDER BY agent_name
    """, (project_type or '', project_name))

    return [dict(row) for row in cur.fetchall()]


def get_all_projects(conn) -> List[Dict]:
    """Get all active projects."""
    cur = conn.cursor()
    cur.execute("""
        SELECT project_name, project_path, project_type
        FROM claude.workspaces
        WHERE is_active = true AND project_path IS NOT NULL
        ORDER BY project_name
    """)
    return [dict(row) for row in cur.fetchall()]


def map_tools_for_frontmatter(tools: List[str], spawnable_agents: List[str] = None) -> str:
    """Convert tool list to .claude/agents frontmatter format.

    Maps orchestrator-style tool names to Claude Code native tool names.
    Handles Bash permission patterns and Task(agent) spawning syntax.
    """
    if not tools:
        return ""

    native_tools = []
    seen = set()

    for tool in tools:
        # Skip MCP tool references - those go in mcpServers
        if tool.startswith('mcp__'):
            continue

        # Bash patterns: Bash(git add:*) -> Bash
        # In native agents, Bash is a single tool (granular perms via permissionMode)
        if tool.startswith('Bash'):
            if 'Bash' not in seen:
                native_tools.append('Bash')
                seen.add('Bash')
            continue

        # Standard tools pass through
        if tool not in seen:
            native_tools.append(tool)
            seen.add(tool)

    # Add Task with spawnable agents if coordinator
    if spawnable_agents:
        agent_list = ", ".join(spawnable_agents)
        native_tools.append(f"Task({agent_list})")
    elif 'Task' not in seen:
        # Don't add Task by default - only coordinators get it
        pass

    return ", ".join(native_tools)


def render_agent_md(agent: Dict) -> str:
    """Render an agent definition as a .claude/agents/*.md file.

    Generates YAML frontmatter + markdown body (system prompt).
    """
    lines = ["---"]

    # Required fields
    lines.append(f"name: {agent['agent_name']}")
    lines.append(f"description: \"{agent['description']}\"")

    # Model
    lines.append(f"model: {agent['model']}")

    # Tools
    tool_str = map_tools_for_frontmatter(
        agent.get('tools') or [],
        agent.get('spawnable_agents')
    )
    if tool_str:
        lines.append(f"tools: {tool_str}")

    # Disallowed tools
    if agent.get('disallowed_tools'):
        # Map disallowed tools same way
        disallowed = []
        seen = set()
        for t in agent['disallowed_tools']:
            if t.startswith('mcp__'):
                continue
            base = t.split('(')[0] if '(' in t else t
            if base not in seen:
                disallowed.append(base)
                seen.add(base)
        if disallowed:
            lines.append(f"disallowedTools: {', '.join(disallowed)}")

    # Permission mode
    if agent.get('permission_mode'):
        lines.append(f"permissionMode: {agent['permission_mode']}")

    # Max turns
    if agent.get('max_turns'):
        lines.append(f"maxTurns: {agent['max_turns']}")

    # Memory
    if agent.get('memory'):
        lines.append(f"memory: {agent['memory']}")

    # Skills
    if agent.get('skills'):
        lines.append("skills:")
        for skill in agent['skills']:
            lines.append(f"  - {skill}")

    lines.append("---")
    lines.append("")

    # Body = system prompt + use cases as documentation
    body_parts = []

    # System prompt is the main body
    body_parts.append(agent['system_prompt'])

    # Add use cases as reference section
    if agent.get('use_cases'):
        body_parts.append("")
        body_parts.append("## When to Use")
        body_parts.append("")
        for uc in agent['use_cases']:
            body_parts.append(f"- {uc}")

    # Add not_for as anti-patterns
    if agent.get('not_for'):
        body_parts.append("")
        body_parts.append("## Not For")
        body_parts.append("")
        for nf in agent['not_for']:
            body_parts.append(f"- {nf}")

    lines.extend(body_parts)
    lines.append("")  # trailing newline

    return "\n".join(lines)


def generate_for_project(project_name: str, project_path: str,
                         agents: List[Dict], dry_run: bool = False) -> Dict:
    """Generate .claude/agents/*.md files for a project."""
    results = {'generated': [], 'skipped': [], 'errors': []}

    agents_dir = Path(project_path) / ".claude" / "agents"

    for agent in agents:
        filename = f"{agent['agent_name']}.md"
        target_path = agents_dir / filename

        try:
            content = render_agent_md(agent)

            # Check if file exists and is identical
            if target_path.exists():
                existing = target_path.read_text(encoding='utf-8')
                if existing == content:
                    results['skipped'].append({
                        'name': agent['agent_name'],
                        'reason': 'unchanged'
                    })
                    continue

            if dry_run:
                results['generated'].append({
                    'name': agent['agent_name'],
                    'path': str(target_path),
                    'size': len(content)
                })
                continue

            # Write file
            agents_dir.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding='utf-8')

            results['generated'].append({
                'name': agent['agent_name'],
                'path': str(target_path),
                'size': len(content)
            })

        except Exception as e:
            results['errors'].append({
                'name': agent['agent_name'],
                'error': str(e)
            })

    # Remove .md files in agents dir that are no longer in DB
    if not dry_run and agents_dir.exists():
        active_names = {a['agent_name'] for a in agents}
        for existing_file in agents_dir.glob("*.md"):
            if existing_file.stem not in active_names:
                existing_file.unlink()
                results['generated'].append({
                    'name': existing_file.stem,
                    'path': str(existing_file),
                    'action': 'removed (no longer active)'
                })

    return results


def print_results(project: str, results: Dict):
    """Print generation results."""
    total = len(results['generated']) + len(results['skipped']) + len(results['errors'])

    print(f"\n  {project}: ", end="")

    if results['generated']:
        print(f"{len(results['generated'])} generated", end="")
    if results['skipped']:
        print(f", {len(results['skipped'])} unchanged", end="")
    if results['errors']:
        print(f", {len(results['errors'])} ERRORS", end="")
    if not any([results['generated'], results['skipped'], results['errors']]):
        print("no agents", end="")

    print()

    # Show details for generated files
    for item in results['generated']:
        action = item.get('action', 'written')
        print(f"    + {item['name']}.md ({action})")

    for item in results['errors']:
        print(f"    ! {item['name']}: {item['error']}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate .claude/agents/*.md from database agent definitions'
    )
    parser.add_argument('project_name', nargs='?',
                        help='Project name (default: current directory)')
    parser.add_argument('--all', action='store_true',
                        help='Generate for ALL active projects')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be generated')

    args = parser.parse_args()

    project_name = args.project_name
    if not project_name and not args.all:
        project_name = Path.cwd().name

    conn = get_db_connection()

    try:
        print(f"\n{'=' * 60}")
        print(f"  AGENT FILE GENERATION")
        if args.dry_run:
            print(f"  (DRY RUN - no files will be written)")
        print(f"{'=' * 60}")

        if args.all:
            projects = get_all_projects(conn)
            print(f"\n  Generating for {len(projects)} active projects...")

            total_generated = 0
            total_skipped = 0
            total_errors = 0

            for project in projects:
                agents = get_agents_for_project(conn, project['project_name'])
                results = generate_for_project(
                    project['project_name'],
                    project['project_path'],
                    agents,
                    dry_run=args.dry_run
                )
                print_results(project['project_name'], results)
                total_generated += len(results['generated'])
                total_skipped += len(results['skipped'])
                total_errors += len(results['errors'])

            print(f"\n{'=' * 60}")
            print(f"  TOTAL: {total_generated} generated, {total_skipped} unchanged, {total_errors} errors")
            print(f"{'=' * 60}\n")

        else:
            # Single project
            cur = conn.cursor()
            cur.execute("""
                SELECT project_path FROM claude.workspaces
                WHERE project_name = %s AND is_active = true
            """, (project_name,))
            row = cur.fetchone()
            if not row:
                print(f"\n  ERROR: Project '{project_name}' not found in workspaces")
                sys.exit(1)

            project_path = dict(row)['project_path']
            agents = get_agents_for_project(conn, project_name)

            print(f"\n  Project: {project_name}")
            print(f"  Agents: {len(agents)} definitions found")

            results = generate_for_project(
                project_name, project_path, agents,
                dry_run=args.dry_run
            )
            print_results(project_name, results)

            print(f"\n{'=' * 60}\n")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
