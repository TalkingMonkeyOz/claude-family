#!/usr/bin/env python3
"""
Dossier Auto-Population — Coding Intelligence System (F156/BT447)

Gathers context from multiple sources and populates a component dossier
via the existing stash/unstash (Filing Cabinet) system. This is the
foundation for the Research → Plan → Implement workflow.

Sources:
1. CKG (Code Knowledge Graph) — related symbols, module map
2. Memory — relevant decisions, patterns, gotchas
3. Coding standards — file-type specific rules
4. Existing dossier — preserve user notes during merge

Usage:
    from scripts.dossier_auto_populate import populate_dossier
    result = populate_dossier("caching-layer", files=["src/cache.py", "src/redis.py"])

Author: Claude Family
Date: 2026-03-21
Feature: F156 (Coding Intelligence System)
"""

import json
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import POSTGRES_CONFIG

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    return psycopg2.connect(**POSTGRES_CONFIG, cursor_factory=RealDictCursor)


def _get_project_id(conn, project_name: str) -> Optional[str]:
    """Look up project UUID from name."""
    cur = conn.cursor()
    cur.execute(
        "SELECT project_id::text FROM claude.projects WHERE project_name = %s",
        (project_name,),
    )
    row = cur.fetchone()
    return row["project_id"] if row else None


def gather_ckg_context(
    conn,
    project_name: str,
    files: list[str],
    query: str = "",
    max_symbols: int = 15,
) -> dict:
    """Gather symbols and structure from Code Knowledge Graph.

    Returns dict with:
    - symbols: list of {name, kind, file_path, line_number, signature}
    - module_maps: dict of {file_path: [symbols]}
    - similar: list of similar implementations found
    """
    cur = conn.cursor()
    project_id = _get_project_id(conn, project_name)
    if not project_id:
        return {"symbols": [], "module_maps": {}, "similar": []}

    symbols = []
    module_maps = {}

    # Get symbols from each file
    for fp in files:
        cur.execute("""
            SELECT name, kind, file_path, line_number, signature, visibility
            FROM claude.code_symbols
            WHERE project_id = %s AND file_path = %s
            ORDER BY line_number
        """, (project_id, fp))
        file_symbols = [dict(r) for r in cur.fetchall()]
        module_maps[fp] = file_symbols
        symbols.extend(file_symbols)

    # If query provided, find related symbols across project
    if query:
        cur.execute("""
            SELECT name, kind, file_path, line_number, signature, visibility
            FROM claude.code_symbols
            WHERE project_id = %s
              AND (name ILIKE %s OR signature ILIKE %s)
              AND file_path NOT IN %s
            ORDER BY
                CASE WHEN name ILIKE %s THEN 0 ELSE 1 END,
                name
            LIMIT %s
        """, (
            project_id,
            f"%{query}%", f"%{query}%",
            tuple(files) if files else ("__none__",),
            f"{query}%",
            max_symbols,
        ))
        related = [dict(r) for r in cur.fetchall()]
        symbols.extend(related)

    # Find similar symbols (by name patterns in the files)
    similar = []
    seen_names = {s["name"] for s in symbols}
    for sym in list(symbols)[:5]:  # Check top 5 symbols for duplicates
        cur.execute("""
            SELECT name, kind, file_path, line_number, signature
            FROM claude.code_symbols
            WHERE project_id = %s
              AND name ILIKE %s
              AND file_path NOT IN %s
              AND symbol_id::text NOT IN (
                  SELECT symbol_id::text FROM claude.code_symbols
                  WHERE file_path = ANY(%s)
              )
            LIMIT 3
        """, (project_id, f"%{sym['name']}%", tuple(files) if files else ("__none__",), files))
        for r in cur.fetchall():
            if r["name"] not in seen_names:
                similar.append(dict(r))
                seen_names.add(r["name"])

    return {
        "symbols": symbols[:max_symbols],
        "module_maps": module_maps,
        "similar": similar[:10],
    }


def gather_memory_context(conn, project_name: str, query: str, budget: int = 500) -> dict:
    """Gather relevant memories (decisions, patterns, gotchas).

    Returns dict with:
    - decisions: list of relevant decision memories
    - patterns: list of relevant pattern memories
    """
    cur = conn.cursor()

    # Search knowledge table for relevant entries
    results = {"decisions": [], "patterns": []}

    try:
        from embedding_provider import embed as _embed_text
        embedding = _embed_text(query)
        if embedding is None:
            raise RuntimeError("Embedding provider returned None")
        embedding_str = json.dumps(embedding)

        cur.execute("""
            SELECT title, description, knowledge_type, tier,
                   1 - (embedding <=> %s::vector) as similarity
            FROM claude.knowledge
            WHERE tier IN ('mid', 'long')
              AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector ASC
            LIMIT 10
        """, (embedding_str, embedding_str))

        for row in cur.fetchall():
            if row["similarity"] < 0.3:
                continue
            entry = {
                "title": row["title"],
                "description": row["description"][:200],
                "type": row["knowledge_type"],
                "similarity": round(float(row["similarity"]), 3),
            }
            if row["knowledge_type"] in ("decision", "learned"):
                results["decisions"].append(entry)
            else:
                results["patterns"].append(entry)
    except Exception:
        pass  # Memory search is optional enhancement

    return results


def gather_standards_context(files: list[str]) -> dict:
    """Gather applicable coding standards based on file types.

    Returns dict with:
    - standards: list of {language, rules}
    """
    standards = {}
    extension_map = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript-react",
        ".js": "javascript",
        ".jsx": "javascript-react",
        ".cs": "csharp",
        ".rs": "rust",
        ".sql": "sql",
    }

    for fp in files:
        ext = os.path.splitext(fp)[1].lower()
        lang = extension_map.get(ext)
        if lang and lang not in standards:
            standards[lang] = _get_standards_for_language(lang)

    return {"standards": standards}


def _get_standards_for_language(language: str) -> list[str]:
    """Get coding standards rules for a language."""
    rules = {
        "python": [
            "PEP 8 naming: snake_case for functions/variables, PascalCase for classes",
            "Type hints where helpful, especially function signatures",
            "Docstrings for public functions (Google style)",
            "Use pathlib over os.path where possible",
            "Explicit imports, no wildcard imports",
        ],
        "typescript": [
            "camelCase for variables/functions, PascalCase for types/interfaces/components",
            "Prefer const over let, never use var",
            "Use TypeScript strict mode types, avoid any",
            "Named exports preferred over default exports for utilities",
            "Interface over type alias for object shapes",
        ],
        "typescript-react": [
            "camelCase for variables/functions, PascalCase for components",
            "Functional components with hooks, no class components",
            "Custom hooks must start with 'use' prefix",
            "Props interface named ComponentNameProps",
            "Prefer composition over prop drilling",
        ],
        "csharp": [
            "PascalCase for public members, camelCase for private with _ prefix",
            "MVVM pattern: ViewModel never references View",
            "Async methods suffixed with Async",
            "Use using statements for disposable resources",
            "Dependency injection over static singletons",
        ],
        "rust": [
            "snake_case for functions/variables, PascalCase for types",
            "Prefer Result<T, E> over panicking",
            "Use clippy suggestions",
            "Derive common traits (Debug, Clone) where appropriate",
        ],
        "sql": [
            "Use claude.* schema, never legacy schemas",
            "Check column_registry for valid values before writes",
            "Use parameterized queries, never string interpolation",
            "Explicit column lists, no SELECT *",
        ],
    }
    return rules.get(language, [])


def format_dossier_content(
    component: str,
    ckg: dict,
    memory: dict,
    standards: dict,
    existing_notes: str = "",
) -> str:
    """Format gathered context into a structured dossier document."""
    sections = []

    # Header
    sections.append(f"# Dossier: {component}")
    sections.append(f"_Auto-populated by Coding Intelligence System_\n")

    # Existing notes (preserved at top)
    if existing_notes:
        sections.append("## User Notes (Preserved)")
        sections.append(existing_notes)
        sections.append("")

    # Module structure
    if ckg.get("module_maps"):
        sections.append("## Module Structure")
        for fp, syms in ckg["module_maps"].items():
            sections.append(f"\n### {fp}")
            for s in syms:
                vis = "+" if s.get("visibility") == "public" else "-"
                sections.append(f"  {vis} {s['kind']}: {s['name']} — {s.get('signature', 'N/A')}")
        sections.append("")

    # Related symbols
    related = [s for s in ckg.get("symbols", []) if not any(
        s["file_path"] == fp for fp in ckg.get("module_maps", {})
    )]
    if related:
        sections.append("## Related Symbols (from CKG)")
        for s in related[:10]:
            sections.append(f"- **{s['name']}** ({s['kind']}) in `{s['file_path']}:{s.get('line_number', '?')}`")
            if s.get("signature"):
                sections.append(f"  `{s['signature']}`")
        sections.append("")

    # Similar implementations (duplication check)
    if ckg.get("similar"):
        sections.append("## Similar Implementations (Check for Duplication)")
        for s in ckg["similar"]:
            sections.append(f"- **{s['name']}** in `{s['file_path']}:{s.get('line_number', '?')}`")
        sections.append("")

    # Memory context
    if memory.get("decisions"):
        sections.append("## Relevant Decisions")
        for d in memory["decisions"][:5]:
            sections.append(f"- **{d['title']}**: {d['description']}")
        sections.append("")

    if memory.get("patterns"):
        sections.append("## Relevant Patterns")
        for p in memory["patterns"][:5]:
            sections.append(f"- **{p['title']}**: {p['description']}")
        sections.append("")

    # Standards
    if standards.get("standards"):
        sections.append("## Applicable Standards")
        for lang, rules in standards["standards"].items():
            sections.append(f"\n### {lang}")
            for rule in rules:
                sections.append(f"- {rule}")
        sections.append("")

    return "\n".join(sections)


def populate_dossier(
    component: str,
    project_name: str = "claude-family",
    files: list[str] = None,
    query: str = "",
    preserve_notes: bool = True,
) -> dict:
    """Main entry point: gather context and populate dossier.

    Args:
        component: Component name (e.g., "caching-layer", "auth-flow")
        project_name: Project to search in CKG
        files: List of file paths involved in the task
        query: Search query for finding related code/memory
        preserve_notes: If True, preserve existing user notes in dossier

    Returns:
        dict with: success, component, sections_populated, content_preview
    """
    files = files or []
    conn = get_db_connection()

    try:
        # Get existing dossier notes if preserve mode
        existing_notes = ""
        if preserve_notes:
            project_id = _get_project_id(conn, project_name)
            if project_id:
                cur = conn.cursor()
                cur.execute("""
                    SELECT content FROM claude.project_workfiles
                    WHERE project_id = %s AND component = %s AND is_active = true
                    ORDER BY updated_at DESC LIMIT 1
                """, (project_id, component))
                row = cur.fetchone()
                if row and row["content"]:
                    # Extract user notes section if present
                    content = row["content"]
                    if "## User Notes" in content:
                        start = content.index("## User Notes")
                        end = content.index("\n## ", start + 1) if "\n## " in content[start + 1:] else len(content)
                        existing_notes = content[start + len("## User Notes (Preserved)"):end].strip()
                    elif not content.startswith("# Dossier:"):
                        # Existing content is all user notes (manual stash)
                        existing_notes = content

        # Gather context from all sources
        search_query = query or component
        ckg = gather_ckg_context(conn, project_name, files, search_query)
        memory = gather_memory_context(conn, project_name, search_query)
        standards = gather_standards_context(files)

        # Format and stash
        content = format_dossier_content(
            component, ckg, memory, standards, existing_notes
        )

        # Use stash via direct DB write (same as MCP tool)
        project_id = _get_project_id(conn, project_name)
        if not project_id:
            return {"success": False, "error": f"Project '{project_name}' not found"}

        cur = conn.cursor()

        # Generate embedding for semantic search
        embedding_str = None
        try:
            from embedding_provider import embed as _embed_text_2
            embed_text = f"{component}: {search_query}. Files: {', '.join(files)}"
            embedding = _embed_text_2(embed_text)
            embedding_str = json.dumps(embedding) if embedding else None
        except Exception:
            pass

        # UPSERT into project_workfiles
        cur.execute("""
            INSERT INTO claude.project_workfiles
                (project_id, component, title, content, workfile_type, is_pinned, embedding)
            VALUES (%s, %s, 'auto-populated dossier', %s, 'notes', true,
                    CASE WHEN %s IS NOT NULL THEN %s::vector ELSE NULL END)
            ON CONFLICT (project_id, component, title)
            DO UPDATE SET
                content = EXCLUDED.content,
                updated_at = NOW(),
                access_count = claude.project_workfiles.access_count + 1,
                embedding = COALESCE(EXCLUDED.embedding, claude.project_workfiles.embedding)
            RETURNING workfile_id::text
        """, (project_id, component, content, embedding_str, embedding_str))

        workfile_id = cur.fetchone()["workfile_id"]
        conn.commit()

        sections = []
        if ckg["symbols"]:
            sections.append(f"CKG: {len(ckg['symbols'])} symbols")
        if ckg["module_maps"]:
            sections.append(f"Maps: {len(ckg['module_maps'])} files")
        if ckg["similar"]:
            sections.append(f"Similar: {len(ckg['similar'])} implementations")
        if memory["decisions"]:
            sections.append(f"Decisions: {len(memory['decisions'])}")
        if memory["patterns"]:
            sections.append(f"Patterns: {len(memory['patterns'])}")
        if standards["standards"]:
            sections.append(f"Standards: {', '.join(standards['standards'].keys())}")

        return {
            "success": True,
            "component": component,
            "workfile_id": workfile_id,
            "sections_populated": sections,
            "content_length": len(content),
            "content_preview": content[:300],
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Populate a coding dossier")
    parser.add_argument("component", help="Component name")
    parser.add_argument("--project", default="claude-family", help="Project name")
    parser.add_argument("--files", nargs="+", default=[], help="Files involved")
    parser.add_argument("--query", default="", help="Search query")
    args = parser.parse_args()

    result = populate_dossier(args.component, args.project, args.files, args.query)
    print(json.dumps(result, indent=2, default=str))
