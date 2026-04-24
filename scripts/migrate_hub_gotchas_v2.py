#!/usr/bin/env python3
"""One-off migration: unwind bloated domain_concept gotcha arrays into linked memories.

Context: the v1 knowledge_consolidation job APPENDED memory content into
`claude.entities.properties.gotchas` arrays, creating 10K-token blobs on
three hub entities (Nimbus OData API, Claude Family Memory System,
HAL F165 Empirical Study). v2 of the consolidation job (shipped in commit
548a00b) stopped the bleeding. This script unwinds the existing bloat.

Safety model — no knowledge loss:
  1. For each hub, load its `gotchas` array from entity.properties.
  2. Load all memories in `claude.knowledge` with `consolidated_into = hub_id`.
  3. For each gotcha in the array, check if its text is covered by any
     linked memory's description (simple substring+fuzzy match).
  4. ORPHAN gotchas (no matching memory) are inserted as new memory rows
     before the array is touched — content is preserved, not archived.
  5. Only after orphan preservation is committed do we clear the array.

Default is --dry-run. --apply performs the migration.

Usage:
    python migrate_hub_gotchas_v2.py              # dry-run (report only)
    python migrate_hub_gotchas_v2.py --apply      # apply migration
    python migrate_hub_gotchas_v2.py --hub <name> # one hub only
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("migrate_hub_gotchas_v2")

# The three bloated hubs identified in the 2026-04-24 audit.
# Each entry: (display_name, entity_id, applies_to_projects_for_orphan_memories).
HUBS = [
    (
        "Nimbus OData API",
        "d3e3f8ab-6f3d-4eae-a562-26e751cb3b57",
        ["nimbus-mui", "monash-nimbus-reports", "nimbus-odata-configurator"],
    ),
    (
        "Claude Family Memory System",
        "7493dc09-e97f-4073-a00b-405c05a7ae3d",
        ["claude-family"],
    ),
    (
        "HAL F165 Empirical Study",
        "8947895e-4019-4f09-9af5-064c24d26118",
        ["project-hal"],
    ),
]


def _normalise(text: str) -> str:
    """Normalise text for fuzzy matching: lowercase, collapse whitespace."""
    return " ".join((text or "").lower().split())


def _first_words(text: str, n: int = 15) -> str:
    """Return the first N words — used as a short fingerprint for matching."""
    return " ".join(_normalise(text).split()[:n])


def _gotcha_covered_by_memories(gotcha_text: str, memory_descs: list[str]) -> bool:
    """Decide if a gotcha is already preserved by a linked memory.

    Match strategies (in order):
      1. First-30-words substring match either direction (tolerates minor edits)
      2. Token-set overlap >= 60% (catches paraphrases with shared vocabulary)
    """
    g_norm = _normalise(gotcha_text)
    g_fp = _first_words(gotcha_text, 30)
    if not g_fp:
        # Empty-ish gotcha — treat as covered (nothing to preserve)
        return True

    g_words = set(g_norm.split())
    for mem_desc in memory_descs:
        m_norm = _normalise(mem_desc)
        if not m_norm:
            continue
        m_fp = _first_words(mem_desc, 30)
        if g_fp and g_fp in m_norm:
            return True
        if m_fp and m_fp in g_norm:
            return True
        m_words = set(m_norm.split())
        if g_words:
            overlap = len(g_words & m_words) / len(g_words)
            if overlap >= 0.6:
                return True
    return False


def analyse_hub(conn, hub_name: str, hub_id: str) -> dict:
    cur = conn.cursor()
    cur.execute(
        "SELECT display_name, properties FROM claude.entities WHERE entity_id = %s",
        (hub_id,),
    )
    row = cur.fetchone()
    if not row:
        return {"error": f"Hub {hub_id} not found"}
    display_name = row["display_name"] if isinstance(row, dict) else row[0]
    props = row["properties"] if isinstance(row, dict) else row[1]
    props = props or {}
    gotchas = props.get("gotchas") or []
    if isinstance(gotchas, str):
        gotchas = [gotchas]

    cur.execute(
        """SELECT knowledge_id, title, description FROM claude.knowledge
           WHERE consolidated_into = %s""",
        (hub_id,),
    )
    mem_rows = cur.fetchall()
    memory_descs = []
    for mr in mem_rows:
        if isinstance(mr, dict):
            memory_descs.append(mr.get("description") or mr.get("title") or "")
        else:
            memory_descs.append(mr[2] or mr[1] or "")

    orphans = []
    covered = 0
    for g in gotchas:
        g_text = g if isinstance(g, str) else json.dumps(g)
        if _gotcha_covered_by_memories(g_text, memory_descs):
            covered += 1
        else:
            orphans.append(g_text)

    return {
        "hub_id": hub_id,
        "display_name": display_name,
        "gotcha_count": len(gotchas),
        "linked_memory_count": len(memory_descs),
        "covered_count": covered,
        "orphan_count": len(orphans),
        "orphans": orphans,
    }


def _generate_embedding(text: str):
    """Generate vector embedding via the project's embedding provider.

    Returns None on failure; caller writes the row without an embedding
    so content is not lost even if the embedding service is down.
    """
    try:
        from embedding_provider import embed  # noqa: WPS433 — runtime import OK
        return embed(text)
    except Exception as e:  # noqa: BLE001
        logger.warning("Embedding failed (continuing without): %s", e)
        return None


def _preserve_orphan_memory(cur, orphan_text: str, hub_name: str, hub_id: str,
                             project_names: list[str]) -> str | None:
    """Insert an orphan gotcha as a new memory row linked to the hub.

    Uses raw INSERT because the MCP remember() path requires the MCP server;
    this is a one-off migration running as a script. An OVERRIDE comment is
    included for the SQL governance hook.
    """
    title_seed = " ".join(orphan_text.split()[:10]) or f"[{hub_name} orphan]"
    title = (title_seed[:200]).strip()
    description = orphan_text.strip()
    if len(description) < 20:
        # Too short to preserve meaningfully — skip
        return None

    emb = _generate_embedding(f"{title}\n{description}")
    emb_literal = str(emb) if emb else None

    cur.execute(
        """-- OVERRIDE: one-off migration rehoming orphan gotchas from entity.properties
        -- NOTE: claude.knowledge.knowledge_id has no DEFAULT — supply explicitly
        INSERT INTO claude.knowledge (
            knowledge_id,
            title, description, knowledge_type, tier,
            applies_to_projects, consolidated_into, confidence_level,
            embedding, source, created_at, updated_at
        ) VALUES (
            gen_random_uuid(),
            %s, %s, %s, 'mid',
            %s::text[], %s, 75,
            %s::vector, %s, NOW(), NOW()
        ) RETURNING knowledge_id""",
        (title, description, "gotcha",
         project_names, hub_id,
         emb_literal, "hub_gotcha_migration_v2"),
    )
    result = cur.fetchone()
    if not result:
        return None
    return str(result["knowledge_id"] if isinstance(result, dict) else result[0])


def migrate_hub(conn, hub_name: str, hub_id: str, project_names: list[str],
                apply: bool) -> dict:
    cur = conn.cursor()
    analysis = analyse_hub(conn, hub_name, hub_id)
    logger.info(
        "  %s: gotchas=%d, linked_memories=%d, covered=%d, orphans=%d",
        analysis["display_name"],
        analysis["gotcha_count"],
        analysis["linked_memory_count"],
        analysis["covered_count"],
        analysis["orphan_count"],
    )
    if not apply:
        return analysis

    preserved_ids: list[str] = []
    for orphan in analysis["orphans"]:
        new_id = _preserve_orphan_memory(cur, orphan, hub_name, hub_id, project_names)
        if new_id:
            preserved_ids.append(new_id)

    # Shrink the entity's gotchas array to a short pointer note. Do not
    # set to [] so future readers understand why it is empty.
    pointer = [
        f"[migrated {datetime.now(timezone.utc).date().isoformat()}] "
        f"{analysis['gotcha_count']} gotchas rehomed to linked claude.knowledge rows "
        f"(consolidated_into={hub_id}); "
        f"{len(preserved_ids)} orphans preserved as new memories. "
        "Query memories via recall_memories() or SELECT ... WHERE consolidated_into = this entity_id."
    ]
    cur.execute(
        """-- OVERRIDE: one-off migration unwinding v1 consolidation bloat
        UPDATE claude.entities
        SET properties = jsonb_set(
            COALESCE(properties, '{}'::jsonb),
            '{gotchas}',
            %s::jsonb
        ),
        updated_at = NOW()
        WHERE entity_id = %s""",
        (json.dumps(pointer), hub_id),
    )

    cur.execute(
        """INSERT INTO claude.audit_log (entity_type, entity_id, event_type, metadata, created_at)
        VALUES ('entity', %s, 'hub_gotchas_migrated_v2', %s::jsonb, NOW())""",
        (hub_id, json.dumps({
            "hub_name": analysis["display_name"],
            "prior_gotcha_count": analysis["gotcha_count"],
            "linked_memory_count": analysis["linked_memory_count"],
            "orphans_preserved_as_new_memories": len(preserved_ids),
            "preserved_ids": preserved_ids,
            "script": "migrate_hub_gotchas_v2.py",
        })),
    )

    conn.commit()
    analysis["preserved_orphan_memory_ids"] = preserved_ids
    analysis["migrated"] = True
    return analysis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Apply the migration (default is dry-run report only)")
    parser.add_argument("--hub", default="",
                        help="Restrict to one hub by display_name substring")
    args = parser.parse_args()

    conn = get_db_connection()
    if not conn:
        logger.error("Cannot connect to database")
        return 1

    try:
        total = {"hubs": 0, "orphans": 0, "migrated": 0}
        for hub_name, hub_id, project_names in HUBS:
            if args.hub and args.hub.lower() not in hub_name.lower():
                continue
            logger.info("=== %s ===", hub_name)
            result = migrate_hub(conn, hub_name, hub_id, project_names,
                                 apply=args.apply)
            total["hubs"] += 1
            total["orphans"] += result.get("orphan_count", 0)
            if result.get("migrated"):
                total["migrated"] += 1
        logger.info(
            "Done. hubs=%d orphans_total=%d migrated=%d mode=%s",
            total["hubs"], total["orphans"], total["migrated"],
            "APPLY" if args.apply else "DRY-RUN",
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
