#!/usr/bin/env python3
"""
Benchmark RAG retrieval quality across all knowledge stores.

Runs test queries against each RAG source independently and reports
hit rates, similarity scores, and coverage gaps. Designed to measure
whether entity catalog + workfile search improve retrieval quality.

Usage:
    python scripts/benchmark_rag.py
    python scripts/benchmark_rag.py --json          # JSON output
    python scripts/benchmark_rag.py --min-sim 0.3   # Lower similarity threshold
"""

import sys
import os
import json
import time
import argparse
import logging
from typing import Optional
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, setup_hook_logging
from rag_utils import generate_embedding

logger = setup_hook_logging("benchmark_rag")

# ---------------------------------------------------------------------------
# Test queries with expected sources
# ---------------------------------------------------------------------------
# Each entry: (query, set of store names expected to have results)
# Stores: knowledge, vault, entities, workfiles, nimbus

TEST_QUERIES = [
    ("How does UserSDK work?",
     {"knowledge", "entities", "workfiles"}),
    ("What is the session lifecycle?",
     {"vault", "knowledge"}),
    ("How to configure scheduled jobs?",
     {"vault", "entities"}),
    ("What gotchas exist for psycopg3?",
     {"knowledge"}),
    ("What OData entities does Nimbus have?",
     {"entities"}),
    ("How does the RAG hook inject context?",
     {"vault", "knowledge"}),
    ("What is the BPMN-first rule?",
     {"vault", "knowledge"}),
    ("How do I use the entity catalog?",
     {"vault", "knowledge", "entities"}),
    ("What are the storage rules for Claude Family?",
     {"vault", "knowledge"}),
    ("How does memory consolidation work?",
     {"vault", "knowledge"}),
    ("What is the Work Context Container?",
     {"knowledge", "workfiles"}),
    ("How to create a new project?",
     {"vault", "knowledge"}),
    ("What patterns exist for error handling in hooks?",
     {"knowledge", "vault"}),
    ("How does the config management self-healing work?",
     {"vault", "knowledge"}),
]

# ---------------------------------------------------------------------------
# Query functions — thin wrappers that return (hit_count, top_similarity)
# ---------------------------------------------------------------------------

def _query_store(conn, sql: str, params: tuple) -> tuple[int, float]:
    """Run a similarity query and return (hit_count, top_similarity)."""
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        if not rows:
            return (0, 0.0)
        # Extract similarity from last column
        sims = []
        for r in rows:
            sim = r["similarity"] if isinstance(r, dict) else r[-1]
            sims.append(float(sim))
        return (len(rows), max(sims) if sims else 0.0)
    except Exception as e:
        logger.warning(f"Store query failed: {e}")
        return (0, 0.0)


def query_knowledge_store(conn, embedding, min_sim: float) -> tuple[int, float]:
    return _query_store(conn, """
        SELECT title, 1 - (embedding <=> %s::vector) as similarity
        FROM claude.knowledge
        WHERE embedding IS NOT NULL
          AND 1 - (embedding <=> %s::vector) >= %s
        ORDER BY embedding <=> %s::vector
        LIMIT 5
    """, (embedding, embedding, min_sim, embedding))


def query_vault_store(conn, embedding, min_sim: float) -> tuple[int, float]:
    return _query_store(conn, """
        SELECT doc_path, 1 - (embedding <=> %s::vector) as similarity
        FROM claude.vault_embeddings
        WHERE embedding IS NOT NULL
          AND 1 - (embedding <=> %s::vector) >= %s
        ORDER BY embedding <=> %s::vector
        LIMIT 5
    """, (embedding, embedding, min_sim, embedding))


def query_entity_store(conn, embedding, min_sim: float) -> tuple[int, float]:
    return _query_store(conn, """
        SELECT e.display_name, 1 - (e.embedding <=> %s::vector) as similarity
        FROM claude.entities e
        WHERE e.embedding IS NOT NULL
          AND e.is_archived = false
          AND 1 - (e.embedding <=> %s::vector) >= %s
        ORDER BY e.embedding <=> %s::vector
        LIMIT 5
    """, (embedding, embedding, min_sim, embedding))


def query_workfile_store(conn, embedding, min_sim: float) -> tuple[int, float]:
    return _query_store(conn, """
        SELECT w.component, w.title,
               1 - (w.embedding <=> %s::vector) as similarity
        FROM claude.project_workfiles w
        WHERE w.embedding IS NOT NULL
          AND w.is_active = true
          AND 1 - (w.embedding <=> %s::vector) >= %s
        ORDER BY w.embedding <=> %s::vector
        LIMIT 5
    """, (embedding, embedding, min_sim, embedding))


def query_nimbus_store(conn, query_text: str) -> tuple[int, float]:
    """Nimbus uses keyword search, not embeddings. Returns (hits, 1.0 if hit)."""
    keywords = [w.lower() for w in query_text.split() if len(w) > 3]
    if not keywords:
        return (0, 0.0)
    try:
        cur = conn.cursor()
        like_clauses = " OR ".join(["content ILIKE %s"] * len(keywords))
        params = [f"%{kw}%" for kw in keywords[:5]]
        cur.execute(f"""
            SELECT COUNT(*) as cnt
            FROM claude.nimbus_context
            WHERE {like_clauses}
        """, params)
        row = cur.fetchone()
        cnt = row["cnt"] if isinstance(row, dict) else row[0]
        return (int(cnt), 1.0 if cnt > 0 else 0.0)
    except Exception:
        return (0, 0.0)


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------

STORES = ["knowledge", "vault", "entities", "workfiles", "nimbus"]
STORE_QUERIES = {
    "knowledge": query_knowledge_store,
    "vault": query_vault_store,
    "entities": query_entity_store,
    "workfiles": query_workfile_store,
}


def run_benchmark(min_sim: float = 0.35) -> dict:
    """Run all test queries against all stores. Returns structured results."""
    conn = get_db_connection(strict=True)
    results = []
    store_totals = {s: {"hits": 0, "exclusive_hits": 0} for s in STORES}

    for query, expected in TEST_QUERIES:
        t0 = time.time()
        embedding = generate_embedding(query)
        if not embedding:
            logger.warning(f"Failed to generate embedding for: {query}")
            continue

        row = {"query": query, "expected": sorted(expected), "stores": {}}

        for store in STORES:
            if store == "nimbus":
                hits, top_sim = query_nimbus_store(conn, query)
            else:
                hits, top_sim = STORE_QUERIES[store](conn, embedding, min_sim)

            row["stores"][store] = {"hits": hits, "top_sim": round(top_sim, 3)}
            if hits > 0:
                store_totals[store]["hits"] += 1

        # Find stores that exclusively found results (no other store had hits)
        hit_stores = {s for s in STORES if row["stores"][s]["hits"] > 0}
        for s in hit_stores:
            others = hit_stores - {s}
            if not others:
                store_totals[s]["exclusive_hits"] += 1

        row["hit_stores"] = sorted(hit_stores)
        row["expected_match"] = hit_stores >= expected
        row["elapsed_ms"] = round((time.time() - t0) * 1000)
        results.append(row)

    conn.close()

    # New-source coverage: queries where entities or workfiles found results
    new_source_hits = sum(
        1 for r in results
        if r["stores"]["entities"]["hits"] > 0 or r["stores"]["workfiles"]["hits"] > 0
    )

    return {
        "total_queries": len(results),
        "min_similarity": min_sim,
        "per_query": results,
        "store_summary": store_totals,
        "new_source_coverage": new_source_hits,
        "new_source_pct": round(100 * new_source_hits / max(len(results), 1)),
    }


def print_report(data: dict):
    """Print human-readable report to stdout."""
    total = data["total_queries"]
    print(f"\n{'='*70}")
    print(f"  RAG Benchmark — {total} queries, min_similarity={data['min_similarity']}")
    print(f"{'='*70}\n")

    # Per-query results
    for r in data["per_query"]:
        match_icon = "PASS" if r["expected_match"] else "MISS"
        print(f"  [{match_icon}] {r['query']}")
        print(f"         Expected: {', '.join(r['expected'])}")
        print(f"         Got:      {', '.join(r['hit_stores']) or '(none)'}")
        for s in STORES:
            info = r["stores"][s]
            if info["hits"] > 0:
                print(f"           {s:12s}: {info['hits']} hits, top_sim={info['top_sim']}")
        print(f"         ({r['elapsed_ms']}ms)")
        print()

    # Store summary
    print(f"  {'-'*50}")
    print(f"  Store Hit Rates (out of {total} queries):")
    print(f"  {'-'*50}")
    for s in STORES:
        info = data["store_summary"][s]
        pct = round(100 * info["hits"] / max(total, 1))
        excl = info["exclusive_hits"]
        excl_str = f", {excl} exclusive" if excl > 0 else ""
        print(f"    {s:12s}: {info['hits']:2d}/{total} ({pct:3d}%){excl_str}")

    # New source coverage
    print(f"\n  {'-'*50}")
    print(f"  New Source Coverage (entities + workfiles):")
    print(f"    Queries with hits: {data['new_source_coverage']}/{total} ({data['new_source_pct']}%)")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Benchmark RAG retrieval quality")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of report")
    parser.add_argument("--min-sim", type=float, default=0.35, help="Minimum similarity threshold")
    args = parser.parse_args()

    print("Running RAG benchmark...")
    data = run_benchmark(min_sim=args.min_sim)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_report(data)


if __name__ == "__main__":
    main()
