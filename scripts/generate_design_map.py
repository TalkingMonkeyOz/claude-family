#!/usr/bin/env python3
"""
Design Map Generator - Compressed orientation snapshot for large-scale design state.

Queries claude.knowledge for design_concept entries and generates a token-efficient
(~50 lines, ~500 tokens) markdown map that any Claude session can load for instant
project orientation.

Features:
- Area/type extraction from knowledge description text (regex-based)
- Hotspot detection: concepts referenced across 3+ areas
- Connectivity ranking by relation count
- Open gap detection: unmet dependencies/requirements
- Unresolved design feedback summary

Usage:
    python scripts/generate_design_map.py --project PROJECT
    python scripts/generate_design_map.py --project PROJECT --output map.md
    python scripts/generate_design_map.py --project PROJECT --store-fact

Part of F132: Large-Scale Design Management.
"""

import argparse
import re
import sys
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_database_uri, get_db_connection

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_AREA_RE = re.compile(r'\bArea:\s*([^\n|,.]+)', re.IGNORECASE)
_TYPE_RE = re.compile(r'\bType:\s*([^\n|,.]+)', re.IGNORECASE)


def _parse_field(text: Optional[str], pattern: re.Pattern) -> str:
    """Extract first regex group from text, stripped. Returns '' if not found."""
    if not text:
        return ''
    m = pattern.search(text)
    return m.group(1).strip() if m else ''


def _parse_area(description: Optional[str]) -> str:
    return _parse_field(description, _AREA_RE) or 'Unclassified'


def _parse_type(description: Optional[str]) -> str:
    return _parse_field(description, _TYPE_RE).lower()


# ---------------------------------------------------------------------------
# Database queries
# ---------------------------------------------------------------------------

def _get_project_id(cur, project_name: str) -> Optional[str]:
    cur.execute(
        "SELECT project_id::text FROM claude.projects WHERE project_name = %s",
        (project_name,)
    )
    row = cur.fetchone()
    return row['project_id'] if row else None


def _fetch_concepts(cur, project_name: str) -> list:
    """Fetch all design_concept knowledge entries for the project."""
    cur.execute("""
        SELECT
            knowledge_id::text AS knowledge_id,
            title,
            description,
            confidence_level
        FROM claude.knowledge
        WHERE knowledge_category = 'design_concept'
          AND %s = ANY(applies_to_projects)
        ORDER BY created_at
    """, (project_name,))
    return cur.fetchall()


def _fetch_relations(cur, concept_ids: list[str]) -> list:
    """Fetch all relations where either endpoint is in concept_ids."""
    if not concept_ids:
        return []
    cur.execute("""
        SELECT
            from_knowledge_id::text AS from_id,
            to_knowledge_id::text   AS to_id,
            relation_type,
            strength
        FROM claude.knowledge_relations
        WHERE from_knowledge_id = ANY(%s::uuid[])
           OR to_knowledge_id   = ANY(%s::uuid[])
    """, (concept_ids, concept_ids))
    return cur.fetchall()


def _fetch_design_feedback(cur, project_id: str) -> list:
    """Fetch unresolved design feedback items."""
    cur.execute("""
        SELECT
            short_code,
            title,
            priority,
            status
        FROM claude.feedback
        WHERE feedback_type = 'design'
          AND status NOT IN ('resolved', 'wont_fix', 'duplicate')
          AND project_id = %s::uuid
        ORDER BY
            CASE priority
                WHEN 'critical' THEN 1
                WHEN 'high'     THEN 2
                WHEN 'medium'   THEN 3
                WHEN 'low'      THEN 4
                ELSE 5
            END,
            short_code
    """, (project_id,))
    return cur.fetchall()


# ---------------------------------------------------------------------------
# Map computation
# ---------------------------------------------------------------------------

def _build_area_summary(concepts: list) -> dict:
    """
    Returns dict: area -> {count, decisions, key_deps}
    key_deps = titles of 'dependency' or 'component' type concepts in that area.
    """
    areas: dict[str, dict] = {}
    for c in concepts:
        area = _parse_area(c['description'])
        ctype = _parse_type(c['description'])
        rec = areas.setdefault(area, {'count': 0, 'decisions': 0, 'key_deps': []})
        rec['count'] += 1
        if ctype == 'decision':
            rec['decisions'] += 1
        if ctype in ('dependency', 'component', 'technology'):
            dep_label = c['title'][:30]
            if dep_label not in rec['key_deps']:
                rec['key_deps'].append(dep_label)
    return areas


def _build_connectivity(concepts: list, relations: list) -> dict[str, int]:
    """Return concept_id -> total relation count (in + out)."""
    counts: dict[str, int] = defaultdict(int)
    for r in relations:
        counts[r['from_id']] += 1
        counts[r['to_id']] += 1
    return counts


def _find_hotspots(concepts: list) -> list[tuple[str, list[str]]]:
    """
    Return concepts whose title appears (case-insensitive fuzzy) in 3+ distinct areas.
    Returns list of (title, [area1, area2, ...]) sorted by area count desc.
    """
    title_areas: dict[str, set] = defaultdict(set)
    for c in concepts:
        area = _parse_area(c['description'])
        # Use concept title as the key
        title_areas[c['title']].add(area)

    hotspots = [
        (title, sorted(areas))
        for title, areas in title_areas.items()
        if len(areas) >= 3
    ]
    hotspots.sort(key=lambda x: len(x[1]), reverse=True)
    return hotspots[:10]


def _find_top_decisions(concepts: list, connectivity: dict[str, int]) -> list[dict]:
    """Top 5 decisions ranked by connectivity."""
    decisions = [
        {
            'title': c['title'],
            'area': _parse_area(c['description']),
            'relations': connectivity.get(c['knowledge_id'], 0),
        }
        for c in concepts
        if _parse_type(c['description']) == 'decision'
    ]
    decisions.sort(key=lambda d: d['relations'], reverse=True)
    return decisions[:5]


def _find_open_gaps(concepts: list, relations: list) -> list[dict]:
    """
    Find concepts of type 'dependency' or 'requirement' that have no incoming
    'supports' relation — i.e. they are referenced but not yet met.
    """
    concept_ids_with_support: set[str] = set()
    for r in relations:
        if r['relation_type'] == 'supports':
            concept_ids_with_support.add(r['to_id'])

    gaps = []
    for c in concepts:
        ctype = _parse_type(c['description'])
        if ctype in ('dependency', 'requirement', 'gap'):
            if c['knowledge_id'] not in concept_ids_with_support:
                gaps.append({
                    'title': c['title'],
                    'area': _parse_area(c['description']),
                })
    return gaps[:8]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_map(
    project_name: str,
    concepts: list,
    relations: list,
    feedback: list,
) -> str:
    """Render the compressed design map as markdown."""

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    n_concepts = len(concepts)
    n_relations = len(relations)
    n_open_fb = len(feedback)

    if n_concepts == 0:
        return (
            f"# Design Map: {project_name}\n"
            f"Generated: {now}\n\n"
            "No design concepts extracted yet. "
            "Run Phase 1 (EXTRACT) of the Design Coherence skill.\n"
        )

    area_summary = _build_area_summary(concepts)
    connectivity = _build_connectivity(concepts, relations)
    hotspots = _find_hotspots(concepts)
    top_decisions = _find_top_decisions(concepts, connectivity)
    gaps = _find_open_gaps(concepts, relations)

    lines = []

    # Header
    lines.append(f"# Design Map: {project_name}")
    lines.append(
        f"Generated: {now} | "
        f"Concepts: {n_concepts} | "
        f"Relations: {n_relations} | "
        f"Open Design FB: {n_open_fb}"
    )
    lines.append("")

    # Areas table (cap at 10)
    n_areas = len(area_summary)
    lines.append(f"## Areas ({n_areas})")
    lines.append("| Area | Concepts | Decisions | Key Deps |")
    lines.append("|------|----------|-----------|----------|")
    sorted_areas = sorted(area_summary.items(), key=lambda x: x[1]['count'], reverse=True)
    for area, rec in sorted_areas[:10]:
        deps_cell = ', '.join(rec['key_deps'][:3]) or '—'
        lines.append(
            f"| {area} | {rec['count']} | {rec['decisions']} | {deps_cell} |"
        )
    if n_areas > 10:
        lines.append(f"| *(+{n_areas - 10} more areas)* | | | |")
    lines.append("")

    # Hotspots
    if hotspots:
        lines.append("## Hotspots (concepts in 3+ areas)")
        for title, areas in hotspots:
            area_list = ', '.join(areas)
            lines.append(f"- **{title}** — {area_list} ({len(areas)} areas)")
        lines.append("")

    # Top decisions
    if top_decisions:
        lines.append("## Top Decisions (by connectivity)")
        for i, d in enumerate(top_decisions, 1):
            rel_label = f"{d['relations']} relation{'s' if d['relations'] != 1 else ''}"
            lines.append(f"{i}. [D] {d['title']} ({rel_label}) — {d['area']}")
        lines.append("")

    # Open gaps
    if gaps:
        lines.append("## Open Gaps")
        for g in gaps:
            lines.append(f"- {g['title']} — referenced but not defined ({g['area']})")
        lines.append("")

    # Unresolved design feedback
    if feedback:
        lines.append(f"## Unresolved Design Feedback ({n_open_fb})")
        for fb in feedback[:8]:
            priority = fb.get('priority') or 'unknown'
            lines.append(f"- {fb['short_code']}: {fb['title']} ({priority})")
        if n_open_fb > 8:
            lines.append(f"- *(+{n_open_fb - 8} more)*")
        lines.append("")

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Session fact storage
# ---------------------------------------------------------------------------

def _store_as_session_fact(conn, project_name: str, map_content: str) -> bool:
    """Insert design map into claude.session_facts as a 'data' fact."""
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.session_facts
                (fact_id, session_id, project_name, fact_type, fact_key,
                 fact_value, is_sensitive, created_at)
            VALUES
                (gen_random_uuid(), NULL, %s, 'data', 'design_map',
                 %s, FALSE, NOW())
            ON CONFLICT (session_id, fact_key) DO UPDATE SET
                fact_value = EXCLUDED.fact_value,
                fact_type  = EXCLUDED.fact_type,
                created_at = NOW()
        """, (project_name, map_content))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"WARNING: Could not store session fact: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Generate compressed design map from the concept index.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python scripts/generate_design_map.py --project Project-Metis
  python scripts/generate_design_map.py --project Project-Metis --output map.md
  python scripts/generate_design_map.py --project Project-Metis --store-fact
""",
    )
    parser.add_argument(
        '--project',
        required=True,
        help='Project name as stored in claude.projects (e.g. "Project-Metis")',
    )
    parser.add_argument(
        '--output',
        default=None,
        metavar='FILE',
        help='Write map to this file (default: stdout)',
    )
    parser.add_argument(
        '--store-fact',
        action='store_true',
        help='Also store map as a session fact in claude.session_facts',
    )
    args = parser.parse_args()

    uri = get_database_uri()
    if not uri:
        print(
            "ERROR: No database URI. Set DATABASE_URI env var or POSTGRES_PASSWORD in .env",
            file=sys.stderr,
        )
        return 1

    try:
        conn = psycopg.connect(uri, row_factory=dict_row)
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}", file=sys.stderr)
        return 1

    try:
        cur = conn.cursor()

        project_id = _get_project_id(cur, args.project)
        if not project_id:
            print(
                f"ERROR: Project '{args.project}' not found in claude.projects",
                file=sys.stderr,
            )
            return 1

        concepts = _fetch_concepts(cur, args.project)
        concept_ids = [c['knowledge_id'] for c in concepts]
        relations = _fetch_relations(cur, concept_ids)
        feedback = _fetch_design_feedback(cur, project_id)
        cur.close()

        map_content = _render_map(args.project, concepts, relations, feedback)

        # Output
        if args.output:
            output_path = os.path.abspath(args.output)
            with open(output_path, 'w', encoding='utf-8') as fh:
                fh.write(map_content)
            print(f"Design map written to: {output_path}", file=sys.stderr)
        else:
            print(map_content)

        # Optionally store as session fact
        if args.store_fact:
            ok = _store_as_session_fact(conn, args.project, map_content)
            if ok:
                print(
                    f"Stored design map as session fact 'design_map' for {args.project}",
                    file=sys.stderr,
                )

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
