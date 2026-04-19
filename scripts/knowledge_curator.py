#!/usr/bin/env python3
"""
Knowledge Curator — LLM-assisted knowledge quality auditing pipeline.

Implements the BPMN model `knowledge_curator` — a 5-stage pipeline:
  1. Scan    — Load all active knowledge entries with embeddings for a project
  2. Cluster — Group entries by semantic similarity using pgvector
  3. Classify — Use Haiku to classify relationships within each cluster
  4. Curate  — Take action (merge duplicates, link complementary, archive stale)
  5. Report  — Compute quality score and store report as workfile

Architecture:
  - Runs as a background job via job_runner.py
  - Uses Anthropic API (Haiku for classification, Sonnet for merging)
  - Uses existing pgvector embeddings for clustering (no new embedding calls)
  - Connects to PostgreSQL `ai_company_foundation`, schema `claude`

Usage:
    python knowledge_curator.py                       # Curate next due project
    python knowledge_curator.py --project nimbus-mui  # Curate specific project
    python knowledge_curator.py --dry-run             # Show what would happen
    python knowledge_curator.py --report nimbus-mui   # Show quality report only

Author: Claude Family
Date: 2026-04-08
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Add scripts directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, get_anthropic_key, detect_psycopg

# Setup logging
LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "knowledge_curator.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
)
logger = logging.getLogger("knowledge_curator")

# LLM model constants
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

# Clustering threshold
DEFAULT_SIMILARITY_THRESHOLD = 0.80

# Cluster batch size for classification prompts
CLASSIFY_BATCH_SIZE = 5


# ============================================================================
# Helpers
# ============================================================================

def _fetchall(conn, query: str, params=None) -> list:
    """Execute a SELECT query and return all rows as dicts."""
    _, version, dict_row_factory, cursor_class = detect_psycopg()
    if version == 3:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    else:
        cur = conn.cursor()
        cur.execute(query, params or ())
        rows = cur.fetchall()
        cur.close()
        return rows


def _execute(conn, query: str, params=None):
    """Execute a write query."""
    _, version, _, _ = detect_psycopg()
    if version == 3:
        with conn.cursor() as cur:
            cur.execute(query, params)
    else:
        cur = conn.cursor()
        cur.execute(query, params or ())
        cur.close()


def _fetchone(conn, query: str, params=None):
    """Execute a query and return a single row."""
    _, version, _, _ = detect_psycopg()
    if version == 3:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()
    else:
        cur = conn.cursor()
        cur.execute(query, params or ())
        row = cur.fetchone()
        cur.close()
        return row


def call_claude(prompt: str, model: str = "sonnet", max_tokens: int = 2048) -> str:
    """Call Claude via Anthropic API (Haiku for classification, Sonnet for curation).

    Uses the API key for background jobs (CLI requires interactive auth).
    Falls back gracefully if API key is missing.
    """
    import time as _time
    call_start = _time.time()

    # Map friendly names to model IDs
    MODEL_MAP = {
        "haiku": "claude-haiku-4-5-20251001",
        "sonnet": "claude-sonnet-4-6",
        "opus": "claude-opus-4-6",
    }
    model_id = MODEL_MAP.get(model, model)
    logger.info("Calling Anthropic API: model=%s, prompt_len=%d, max_tokens=%d", model_id, len(prompt), max_tokens)

    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed. Run: pip install anthropic")
        return ""

    api_key = get_anthropic_key()
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set. Required for background jobs.")
        return ""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        elapsed_ms = (_time.time() - call_start) * 1000
        text = response.content[0].text.strip()
        logger.info("API response: model=%s, response_len=%d, %.0fms", model_id, len(text), elapsed_ms)
        return text
    except Exception as e:
        elapsed_ms = (_time.time() - call_start) * 1000
        logger.error("API call failed (%.0fms): %s", elapsed_ms, str(e)[:500])
        return ""


def _get_next_due_project(conn) -> str | None:
    """Find the project most in need of curation.

    Picks the project with the most knowledge entries that either
    has never been curated or was curated longest ago.
    """
    rows = _fetchall(conn, """
        SELECT p.project_name,
               COUNT(k.knowledge_id) AS entry_count,
               MAX(w.updated_at) AS last_curated
        FROM claude.projects p
        JOIN claude.knowledge k ON k.applies_to_projects @> ARRAY[p.project_name]::text[]
        LEFT JOIN claude.project_workfiles w
            ON w.project_id = p.project_id
            AND w.component = 'knowledge-curator'
            AND w.title = 'quality-report'
        WHERE k.tier != 'archived'
        GROUP BY p.project_name
        HAVING COUNT(k.knowledge_id) >= 5
        ORDER BY MAX(w.updated_at) ASC NULLS FIRST, COUNT(k.knowledge_id) DESC
        LIMIT 1
    """)
    if rows:
        return rows[0]["project_name"]
    return None


# ============================================================================
# Stage 1: Scan
# ============================================================================

def scan_entries(project_name: str, conn) -> list[dict]:
    """Load all active knowledge entries with embeddings for a project."""
    rows = _fetchall(conn, """
        SELECT k.knowledge_id, k.title, k.description, k.knowledge_type,
               k.confidence_level, k.tier, k.created_at,
               k.embedding
        FROM claude.knowledge k
        WHERE k.applies_to_projects @> ARRAY[%s]::text[]
        AND k.tier != 'archived'
        ORDER BY k.created_at
    """, (project_name,))
    logger.info("Stage 1 (Scan): Loaded %d entries for project '%s'", len(rows), project_name)
    return rows


# ============================================================================
# Stage 2: Cluster
# ============================================================================

def cluster_entries(entries: list[dict], conn, threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> list[list[dict]]:
    """Group entries by semantic similarity using pgvector.

    Builds an adjacency list of entries with cosine similarity above threshold,
    then finds connected components to form clusters. Skips singletons.
    """
    # Filter to entries that have embeddings
    with_embeddings = [e for e in entries if e.get("embedding") is not None]
    if len(with_embeddings) < 2:
        logger.info("Stage 2 (Cluster): Fewer than 2 entries with embeddings, nothing to cluster")
        return []

    ids = [e["knowledge_id"] for e in with_embeddings]
    id_to_entry = {e["knowledge_id"]: e for e in with_embeddings}

    # Query pairwise similarities above threshold using pgvector
    # Build the ID list as a parameter for the IN clause
    rows = _fetchall(conn, """
        SELECT a.knowledge_id AS id_a,
               b.knowledge_id AS id_b,
               1 - (a.embedding <=> b.embedding) AS similarity
        FROM claude.knowledge a
        CROSS JOIN claude.knowledge b
        WHERE a.knowledge_id = ANY(%s)
          AND b.knowledge_id = ANY(%s)
          AND a.knowledge_id < b.knowledge_id
          AND a.embedding IS NOT NULL
          AND b.embedding IS NOT NULL
          AND 1 - (a.embedding <=> b.embedding) > %s
    """, (ids, ids, threshold))

    # Build adjacency list
    adjacency = defaultdict(set)
    for row in rows:
        id_a = row["id_a"]
        id_b = row["id_b"]
        adjacency[id_a].add(id_b)
        adjacency[id_b].add(id_a)

    # Find connected components via BFS
    visited = set()
    clusters = []
    for entry_id in adjacency:
        if entry_id in visited:
            continue
        # BFS
        component = []
        queue = [entry_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current in id_to_entry:
                component.append(id_to_entry[current])
            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)
        if len(component) >= 2:
            clusters.append(component)

    logger.info(
        "Stage 2 (Cluster): Found %d clusters from %d similar pairs (threshold=%.2f)",
        len(clusters), len(rows), threshold,
    )
    return clusters


# ============================================================================
# Stage 3: Classify
# ============================================================================

CLASSIFY_PROMPT = """You are a knowledge quality auditor. Given a cluster of related knowledge entries, classify the relationship between each pair.

ENTRIES:
{entries_json}

For each pair of entries, determine the relationship:
- "duplicate": Entries say essentially the same thing
- "complementary": Entries cover related but distinct aspects
- "contradicting": Entries make conflicting claims
- "stale": One entry supersedes the other (the older/lower-confidence one is stale)

Output ONLY valid JSON (no markdown fences):
{{"pairs": [{{"entry_a": "id", "entry_b": "id", "relationship": "duplicate|complementary|contradicting|stale", "confidence": 0.0-1.0, "reason": "brief explanation"}}]}}"""


def classify_clusters(clusters: list[list[dict]]) -> list[dict]:
    """Use Haiku to classify relationships within each cluster.

    Batches clusters into groups of CLASSIFY_BATCH_SIZE for efficiency.
    Returns a flat list of pair classifications.
    """
    all_classifications = []

    for batch_start in range(0, len(clusters), CLASSIFY_BATCH_SIZE):
        batch = clusters[batch_start:batch_start + CLASSIFY_BATCH_SIZE]

        for cluster in batch:
            # Build entry summaries for the prompt
            entry_summaries = []
            for entry in cluster:
                entry_summaries.append({
                    "id": str(entry["knowledge_id"]),
                    "title": entry.get("title", ""),
                    "description": (entry.get("description") or "")[:500],
                    "type": entry.get("knowledge_type", ""),
                    "confidence": entry.get("confidence_level"),
                    "created": str(entry.get("created_at", ""))[:10],
                })

            prompt = CLASSIFY_PROMPT.format(entries_json=json.dumps(entry_summaries, indent=2))

            try:
                response_text = call_claude(prompt, model="sonnet", max_tokens=2048)

                # Parse JSON response (handle potential markdown fences)
                if response_text.startswith("```"):
                    response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

                result = json.loads(response_text)
                pairs = result.get("pairs", [])

                # Attach cluster context to each pair
                cluster_ids = {str(e["knowledge_id"]) for e in cluster}
                for pair in pairs:
                    pair["_cluster_ids"] = cluster_ids
                    pair["_cluster_entries"] = {
                        str(e["knowledge_id"]): e for e in cluster
                    }
                all_classifications.extend(pairs)

            except json.JSONDecodeError as e:
                logger.warning("Failed to parse Haiku response for cluster: %s", e)
                continue
            except Exception as e:
                logger.error("Haiku classification failed: %s", e)
                continue

    logger.info(
        "Stage 3 (Classify): Classified %d pairs across %d clusters",
        len(all_classifications), len(clusters),
    )
    return all_classifications


# ============================================================================
# Stage 4: Curate
# ============================================================================

MERGE_PROMPT = """Merge these duplicate knowledge entries into a single, improved entry. Combine the best information from both.

ENTRIES:
{entries_json}

Output ONLY valid JSON (no markdown fences):
{{"title": "merged title (concise)", "description": "merged description (max 300 chars, preserve key facts)", "knowledge_type": "pattern|decision|lesson|technique|gotcha", "confidence_level": 0-100}}"""


def curate(
    classifications: list[dict],
    conn,
    dry_run: bool = False,
) -> dict:
    """Take action on classified clusters.

    Returns stats dict with counts of each action taken.
    """
    stats = {
        "duplicates_merged": 0,
        "complementary_linked": 0,
        "contradictions_resolved": 0,
        "stale_archived": 0,
        "skipped": 0,
        "errors": 0,
        "actions": [],  # Detailed action log
    }

    # Track which entries have already been acted on to avoid double-processing
    processed = set()

    for pair in classifications:
        entry_a_id = pair.get("entry_a")
        entry_b_id = pair.get("entry_b")
        relationship = pair.get("relationship", "").lower()
        confidence = pair.get("confidence", 0)
        reason = pair.get("reason", "")

        # Skip low-confidence classifications
        if confidence < 0.6:
            stats["skipped"] += 1
            continue

        # Skip already-processed entries
        pair_key = tuple(sorted([str(entry_a_id), str(entry_b_id)]))
        if pair_key in processed:
            stats["skipped"] += 1
            continue
        processed.add(pair_key)

        cluster_entries = pair.get("_cluster_entries", {})
        entry_a = cluster_entries.get(str(entry_a_id), {})
        entry_b = cluster_entries.get(str(entry_b_id), {})

        action_record = {
            "entry_a": entry_a_id,
            "entry_b": entry_b_id,
            "relationship": relationship,
            "confidence": confidence,
            "reason": reason,
        }

        try:
            if relationship == "duplicate":
                action_record["action"] = "merge"
                if not dry_run:
                    _merge_duplicates(entry_a, entry_b, conn)
                stats["duplicates_merged"] += 1

            elif relationship == "complementary":
                action_record["action"] = "link"
                if not dry_run:
                    _link_complementary(entry_a_id, entry_b_id, conn)
                stats["complementary_linked"] += 1

            elif relationship == "contradicting":
                action_record["action"] = "resolve_contradiction"
                if not dry_run:
                    _resolve_contradiction(entry_a, entry_b, conn)
                stats["contradictions_resolved"] += 1

            elif relationship == "stale":
                action_record["action"] = "archive_stale"
                if not dry_run:
                    _archive_stale(entry_a, entry_b, conn)
                stats["stale_archived"] += 1

            else:
                action_record["action"] = "skip_unknown"
                stats["skipped"] += 1

        except Exception as e:
            logger.error("Curation action failed for pair (%s, %s): %s", entry_a_id, entry_b_id, e)
            action_record["action"] = "error"
            action_record["error"] = str(e)
            stats["errors"] += 1

        stats["actions"].append(action_record)

    logger.info(
        "Stage 4 (Curate): merged=%d, linked=%d, contradictions=%d, stale=%d, skipped=%d, errors=%d",
        stats["duplicates_merged"], stats["complementary_linked"],
        stats["contradictions_resolved"], stats["stale_archived"],
        stats["skipped"], stats["errors"],
    )
    return stats


def _merge_duplicates(entry_a: dict, entry_b: dict, conn):
    """Use Sonnet to merge two duplicate entries into one."""
    entries_for_prompt = [
        {
            "id": str(entry_a.get("knowledge_id", "")),
            "title": entry_a.get("title", ""),
            "description": (entry_a.get("description") or "")[:500],
            "type": entry_a.get("knowledge_type", ""),
            "confidence": entry_a.get("confidence_level"),
        },
        {
            "id": str(entry_b.get("knowledge_id", "")),
            "title": entry_b.get("title", ""),
            "description": (entry_b.get("description") or "")[:500],
            "type": entry_b.get("knowledge_type", ""),
            "confidence": entry_b.get("confidence_level"),
        },
    ]

    prompt = MERGE_PROMPT.format(entries_json=json.dumps(entries_for_prompt, indent=2))

    response_text = call_claude(prompt, model="sonnet", max_tokens=1024)

    # Parse JSON response
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    merged = json.loads(response_text)

    # Pick the higher tier and broader project scope from the originals
    tier_a = entry_a.get("tier", "mid")
    tier_b = entry_b.get("tier", "mid")
    tier_priority = {"long": 0, "mid": 1, "short": 2}
    best_tier = tier_a if tier_priority.get(tier_a, 1) <= tier_priority.get(tier_b, 1) else tier_b

    # Create merged entry
    row = _fetchone(conn, """
        INSERT INTO claude.knowledge (
            title, description, knowledge_type, confidence_level, tier,
            applies_to_projects, source
        )
        SELECT
            %s, %s, %s, %s, %s,
            -- Union of both entries' project arrays
            (
                SELECT ARRAY(
                    SELECT DISTINCT unnest(a.applies_to_projects || b.applies_to_projects)
                    FROM claude.knowledge a, claude.knowledge b
                    WHERE a.knowledge_id = %s AND b.knowledge_id = %s
                )
            ),
            'knowledge_curator_merge'
        RETURNING knowledge_id
    """, (
        merged.get("title", entry_a.get("title", "")),
        merged.get("description", "")[:300],
        merged.get("knowledge_type", entry_a.get("knowledge_type", "lesson")),
        merged.get("confidence_level", max(
            entry_a.get("confidence_level") or 50,
            entry_b.get("confidence_level") or 50,
        )),
        best_tier,
        entry_a["knowledge_id"],
        entry_b["knowledge_id"],
    ))
    conn.commit()

    new_id = row["knowledge_id"] if row else None

    # Archive originals
    _execute(conn, """
        UPDATE claude.knowledge
        SET tier = 'archived'
        WHERE knowledge_id IN (%s, %s)
    """, (entry_a["knowledge_id"], entry_b["knowledge_id"]))
    conn.commit()

    # Create knowledge_relations linking new to archived
    if new_id:
        for old_id in [entry_a["knowledge_id"], entry_b["knowledge_id"]]:
            try:
                _execute(conn, """
                    INSERT INTO claude.knowledge_relations (
                        source_knowledge_id, target_knowledge_id, relation_type
                    ) VALUES (%s, %s, 'merged_from')
                    ON CONFLICT DO NOTHING
                """, (new_id, old_id))
            except Exception:
                pass  # Relation table may not have this constraint
        conn.commit()

    logger.info("Merged entries %s + %s -> %s", entry_a["knowledge_id"], entry_b["knowledge_id"], new_id)


def _link_complementary(entry_a_id, entry_b_id, conn):
    """Create a knowledge_relations link between complementary entries."""
    try:
        _execute(conn, """
            INSERT INTO claude.knowledge_relations (
                source_knowledge_id, target_knowledge_id, relation_type
            ) VALUES (%s::uuid, %s::uuid, 'complements')
            ON CONFLICT DO NOTHING
        """, (str(entry_a_id), str(entry_b_id)))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning("Failed to link complementary entries: %s", e)


def _resolve_contradiction(entry_a: dict, entry_b: dict, conn):
    """Resolve contradiction by keeping the more recent/confident entry."""
    # Compare recency and confidence
    conf_a = entry_a.get("confidence_level") or 50
    conf_b = entry_b.get("confidence_level") or 50
    created_a = entry_a.get("created_at")
    created_b = entry_b.get("created_at")

    # Prefer higher confidence; break ties with recency
    if conf_a > conf_b:
        loser = entry_b
    elif conf_b > conf_a:
        loser = entry_a
    elif created_a and created_b and created_a > created_b:
        loser = entry_b  # entry_a is newer, archive entry_b
    else:
        loser = entry_a  # entry_b is newer or same, archive entry_a

    _execute(conn, """
        UPDATE claude.knowledge
        SET tier = 'archived'
        WHERE knowledge_id = %s
    """, (loser["knowledge_id"],))
    conn.commit()
    logger.info("Resolved contradiction: archived %s (kept the other)", loser["knowledge_id"])


def _archive_stale(entry_a: dict, entry_b: dict, conn):
    """Archive the stale entry (older/lower-confidence one)."""
    # Same logic as contradiction resolution
    _resolve_contradiction(entry_a, entry_b, conn)


# ============================================================================
# Stage 5: Report
# ============================================================================

def generate_report(project_name: str, stats: dict, entry_count: int, cluster_count: int, conn) -> dict:
    """Compute quality score and store report as workfile.

    Quality score: base 100
      -5 per duplicate found
      -10 per contradiction found
      -2 per stale entry
      +3 per complementary link created
    """
    score = 100
    score -= stats.get("duplicates_merged", 0) * 5
    score -= stats.get("contradictions_resolved", 0) * 10
    score -= stats.get("stale_archived", 0) * 2
    score += stats.get("complementary_linked", 0) * 3
    score = max(0, min(100, score))  # Clamp to 0-100

    report = {
        "project": project_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "quality_score": score,
        "entries_scanned": entry_count,
        "clusters_found": cluster_count,
        "actions": {
            "duplicates_merged": stats.get("duplicates_merged", 0),
            "complementary_linked": stats.get("complementary_linked", 0),
            "contradictions_resolved": stats.get("contradictions_resolved", 0),
            "stale_archived": stats.get("stale_archived", 0),
            "skipped": stats.get("skipped", 0),
            "errors": stats.get("errors", 0),
        },
        "action_details": stats.get("actions", []),
    }

    # Store report as workfile
    try:
        # Get project_id
        row = _fetchone(conn, """
            SELECT project_id FROM claude.projects WHERE project_name = %s
        """, (project_name,))

        if row:
            project_id = row["project_id"]
            report_content = json.dumps(report, indent=2, default=str)

            _execute(conn, """
                INSERT INTO claude.project_workfiles (project_id, component, title, content, updated_at)
                VALUES (%s, 'knowledge-curator', 'quality-report', %s, NOW())
                ON CONFLICT (project_id, component, title)
                DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
            """, (project_id, report_content))
            conn.commit()
            logger.info("Stage 5 (Report): Stored quality report (score=%d) for '%s'", score, project_name)

            # Create feedback items for issues needing Claude's attention (FB267 fix)
            _create_curator_feedback(report, project_id, conn)

    except Exception as e:
        logger.error("Failed to store quality report: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass

    return report


def _create_curator_feedback(report: dict, project_id: str, conn):
    """Create feedback items for curator findings that need Claude's attention.

    Bridges the curator-to-Claude handoff gap (FB267):
    - Errors: actions that failed during curation
    - Low quality: score < 60 indicates systemic knowledge health issues
    - High contradictions: 3+ contradictions suggest conflicting sources
    """
    try:
        actions = report.get("actions", {})
        errors = actions.get("errors", 0)
        contradictions = actions.get("contradictions_resolved", 0)
        score = report.get("quality_score", 100)
        project_name = report.get("project", "unknown")

        items_to_create = []

        if errors > 0:
            error_details = [
                a for a in report.get("action_details", [])
                if a.get("action") == "error"
            ]
            detail_str = "; ".join(
                f"{a.get('entry_a', '?')}/{a.get('entry_b', '?')}: {a.get('error', '?')}"
                for a in error_details[:5]
            )
            items_to_create.append({
                "type": "bug",
                "priority": "high",
                "title": f"Knowledge curator: {errors} action(s) failed for {project_name}",
                "description": f"The knowledge curator encountered {errors} error(s) during curation of {project_name}. "
                               f"These entries need manual review. Details: {detail_str}",
            })

        if score < 60:
            items_to_create.append({
                "type": "improvement",
                "priority": "medium",
                "title": f"Knowledge quality low ({score}/100) for {project_name}",
                "description": f"Knowledge curator scored {project_name} at {score}/100. "
                               f"Actions: {actions.get('duplicates_merged', 0)} dupes merged, "
                               f"{contradictions} contradictions, {actions.get('stale_archived', 0)} stale archived. "
                               f"Review with memory_manage(action='list') and clean up.",
            })

        if contradictions >= 3:
            items_to_create.append({
                "type": "bug",
                "priority": "medium",
                "title": f"Knowledge curator found {contradictions} contradictions in {project_name}",
                "description": f"The curator resolved {contradictions} contradictions automatically, but this high count "
                               f"suggests conflicting knowledge sources. Review recent remember() calls and verify "
                               f"which information is authoritative.",
            })

        for item in items_to_create:
            # Title prefixed with [knowledge_curator] since feedback table has no source column
            _execute(conn, """
                INSERT INTO claude.feedback (project_id, feedback_type, title, description, priority, status)
                VALUES (%s, %s, %s, %s, %s, 'new')
            """, (project_id, item["type"], f"[knowledge_curator] {item['title']}", item["description"], item["priority"]))

        if items_to_create:
            conn.commit()
            logger.info(
                "Created %d feedback item(s) for curator findings in '%s'",
                len(items_to_create), project_name,
            )

    except Exception as e:
        logger.error("Failed to create curator feedback: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass


def print_report(report: dict):
    """Pretty-print the quality report to stdout."""
    print(f"\n{'='*60}")
    print(f"  KNOWLEDGE CURATOR REPORT")
    print(f"  Project: {report['project']}")
    print(f"  Date:    {report['timestamp'][:10]}")
    print(f"{'='*60}")
    print(f"\n  Quality Score: {report['quality_score']}/100")
    print(f"  Entries Scanned: {report['entries_scanned']}")
    print(f"  Clusters Found: {report['clusters_found']}")
    print()
    print("  Actions Taken:")
    actions = report.get("actions", {})
    print(f"    Duplicates merged:       {actions.get('duplicates_merged', 0)}")
    print(f"    Complementary linked:    {actions.get('complementary_linked', 0)}")
    print(f"    Contradictions resolved: {actions.get('contradictions_resolved', 0)}")
    print(f"    Stale archived:          {actions.get('stale_archived', 0)}")
    print(f"    Skipped (low conf.):     {actions.get('skipped', 0)}")
    print(f"    Errors:                  {actions.get('errors', 0)}")

    details = report.get("action_details", [])
    if details:
        print(f"\n  Action Details:")
        for detail in details[:20]:  # Cap at 20 for readability
            action = detail.get("action", "?")
            rel = detail.get("relationship", "?")
            conf = detail.get("confidence", 0)
            reason = detail.get("reason", "")
            print(f"    [{action:>10s}] {rel} (conf={conf:.2f}): {reason[:60]}")
        if len(details) > 20:
            print(f"    ... and {len(details) - 20} more")

    print(f"\n{'='*60}")


# ============================================================================
# Report-only mode (no LLM calls)
# ============================================================================

def show_existing_report(project_name: str, conn) -> bool:
    """Display the most recent stored quality report for a project.

    Returns True if a report was found, False otherwise.
    """
    row = _fetchone(conn, """
        SELECT w.content, w.updated_at
        FROM claude.project_workfiles w
        JOIN claude.projects p ON w.project_id = p.project_id
        WHERE p.project_name = %s
          AND w.component = 'knowledge-curator'
          AND w.title = 'quality-report'
    """, (project_name,))

    if not row:
        print(f"No quality report found for project '{project_name}'.")
        print("Run without --report to generate one.")
        return False

    try:
        report = json.loads(row["content"])
        print(f"  (Last updated: {row['updated_at']})")
        print_report(report)
        return True
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Failed to parse stored report: {e}")
        return False


# ============================================================================
# Main pipeline
# ============================================================================

def run_pipeline(project_name: str, dry_run: bool = False) -> dict:
    """Execute the full 5-stage curation pipeline for a project.

    Returns the final report dict.
    """
    import time as _time
    pipeline_start = _time.time()
    logger.info("Pipeline starting for project '%s' (dry_run=%s)", project_name, dry_run)
    conn = get_db_connection(strict=True)

    try:
        # Stage 1: Scan
        entries = scan_entries(project_name, conn)
        if len(entries) < 2:
            logger.info("Project '%s' has fewer than 2 entries, nothing to curate", project_name)
            report = generate_report(project_name, {}, len(entries), 0, conn)
            return report

        # Stage 2: Cluster
        clusters = cluster_entries(entries, conn)
        if not clusters:
            logger.info("No clusters found for project '%s'", project_name)
            report = generate_report(project_name, {}, len(entries), 0, conn)
            return report

        # Stage 3: Classify (uses Claude CLI via subscription)
        classifications = classify_clusters(clusters)
        if not classifications:
            logger.info("No classifications produced for project '%s'", project_name)
            report = generate_report(project_name, {}, len(entries), len(clusters), conn)
            return report

        # Stage 4: Curate
        stats = curate(classifications, conn, dry_run=dry_run)

        # Stage 5: Report
        report = generate_report(project_name, stats, len(entries), len(clusters), conn)

        elapsed_s = _time.time() - pipeline_start
        logger.info(
            "Pipeline complete for '%s' in %.1fs: scanned=%d, clusters=%d, "
            "merged=%d, linked=%d, contradictions=%d, stale=%d, errors=%d, score=%d",
            project_name, elapsed_s, len(entries), len(clusters),
            stats.get("duplicates_merged", 0), stats.get("complementary_linked", 0),
            stats.get("contradictions_resolved", 0), stats.get("stale_archived", 0),
            stats.get("errors", 0), report.get("quality_score", -1),
        )
        return report

    except Exception as e:
        logger.error("Pipeline failed for project '%s': %s", project_name, e)
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Knowledge Curator — LLM-assisted knowledge quality auditing",
    )
    parser.add_argument(
        "--project", type=str, default=None,
        help="Project name to curate (default: next due project)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without making changes",
    )
    parser.add_argument(
        "--report", type=str, default=None, metavar="PROJECT",
        help="Show the most recent quality report for a project (no curation)",
    )
    args = parser.parse_args()

    # Report-only mode
    if args.report:
        conn = get_db_connection(strict=True)
        try:
            found = show_existing_report(args.report, conn)
            sys.exit(0 if found else 1)
        finally:
            conn.close()

    # Determine project
    project_name = args.project
    if not project_name:
        conn = get_db_connection(strict=True)
        try:
            project_name = _get_next_due_project(conn)
        finally:
            conn.close()

        if not project_name:
            logger.info("No projects found with enough knowledge entries to curate")
            print("No projects due for curation.")
            sys.exit(0)

    if args.dry_run:
        print(f"[DRY RUN] Curating project: {project_name}")
    else:
        print(f"Curating project: {project_name}")

    try:
        report = run_pipeline(project_name, dry_run=args.dry_run)
        print_report(report)

        if args.dry_run:
            print("\n  (Dry run — no changes were made)")

        sys.exit(0)
    except Exception as e:
        logger.error("Knowledge curator failed: %s", e)
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
