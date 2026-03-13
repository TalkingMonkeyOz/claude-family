#!/usr/bin/env python3
"""
Metis Data Model Research - Schema Investigation
Queries 7 knowledge/memory tables for METIS Knowledge Engine assessment.
Writes findings to docs/metis-data-model-research-schemas.md
"""

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from config import get_db_connection

OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "metis-data-model-research-schemas.md"

TABLES = [
    "knowledge",
    "knowledge_relations",
    "knowledge_retrieval_log",
    "session_facts",
    "vault_embeddings",
    "documents",
    "project_workfiles",
]


def q(conn, sql, params=None):
    """Run a query and return list of dicts."""
    with conn.cursor() as cur:
        cur.execute(sql, params or [])
        try:
            return cur.fetchall()
        except Exception:
            return []


def run_query_safe(conn, sql, label=""):
    """Run query, return rows or error string."""
    try:
        rows = q(conn, sql)
        return rows, None
    except Exception as e:
        return [], str(e)


def fmt_rows(rows, max_rows=50):
    """Format rows as a markdown table."""
    if not rows:
        return "_No rows returned._\n"
    keys = list(rows[0].keys())
    lines = []
    lines.append("| " + " | ".join(str(k) for k in keys) + " |")
    lines.append("| " + " | ".join("---" for _ in keys) + " |")
    for row in rows[:max_rows]:
        cells = []
        for k in keys:
            v = row[k]
            if v is None:
                cells.append("NULL")
            else:
                s = str(v)
                # Truncate very long values
                if len(s) > 80:
                    s = s[:77] + "..."
                cells.append(s.replace("|", "\\|").replace("\n", " "))
        lines.append("| " + " | ".join(cells) + " |")
    if len(rows) > max_rows:
        lines.append(f"_... {len(rows) - max_rows} more rows truncated_")
    return "\n".join(lines) + "\n"


def get_columns(conn, table):
    sql = """
        SELECT
            c.column_name,
            c.data_type,
            c.udt_name,
            c.character_maximum_length,
            c.numeric_precision,
            c.is_nullable,
            c.column_default,
            pg_catalog.col_description(
                (quote_ident('claude') || '.' || quote_ident(%s))::regclass::oid,
                c.ordinal_position
            ) AS description
        FROM information_schema.columns c
        WHERE c.table_schema = 'claude' AND c.table_name = %s
        ORDER BY c.ordinal_position
    """
    return q(conn, sql, [table, table])


def get_row_count(conn, table):
    rows = q(conn, f"SELECT count(*) AS cnt FROM claude.{table}")
    return rows[0]["cnt"] if rows else "ERROR"


def get_indexes(conn, table):
    sql = """
        SELECT
            i.relname AS index_name,
            ix.indisunique AS is_unique,
            ix.indisprimary AS is_primary,
            am.amname AS index_type,
            array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) AS columns
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_am am ON i.relam = am.oid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'claude' AND t.relname = %s
        GROUP BY i.relname, ix.indisunique, ix.indisprimary, am.amname
        ORDER BY ix.indisprimary DESC, ix.indisunique DESC, i.relname
    """
    return q(conn, sql, [table])


def get_fks(conn, table):
    sql = """
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS referenced_table,
            ccu.column_name AS referenced_column,
            rc.delete_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints rc
            ON rc.constraint_name = tc.constraint_name AND rc.constraint_schema = tc.constraint_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'claude'
            AND tc.table_name = %s
        ORDER BY kcu.column_name
    """
    return q(conn, sql, [table])


def get_check_constraints(conn, table):
    sql = """
        SELECT
            cc.constraint_name,
            cc.check_clause
        FROM information_schema.check_constraints cc
        JOIN information_schema.table_constraints tc
            ON cc.constraint_name = tc.constraint_name AND cc.constraint_schema = tc.constraint_schema
        WHERE tc.table_schema = 'claude' AND tc.table_name = %s
        ORDER BY cc.constraint_name
    """
    return q(conn, sql, [table])


def get_pg_stats(conn):
    sql = """
        SELECT relname, seq_scan, idx_scan, n_live_tup, last_autoanalyze
        FROM pg_stat_user_tables
        WHERE schemaname = 'claude'
          AND relname IN ('knowledge','knowledge_relations','knowledge_retrieval_log',
                          'session_facts','vault_embeddings','documents','project_workfiles')
        ORDER BY relname
    """
    return q(conn, sql)


def main():
    print(f"Connecting to database...")
    conn = get_db_connection(strict=True)
    print(f"Connected.")

    sections = []

    # ========================================================================
    # HEADER
    # ========================================================================
    sections.append(f"""---
projects:
- claude-family
- project-metis
tags:
- research
- data-model
- knowledge-engine
synced: false
---

# Metis Data Model Research: Knowledge Schema Tables

**Purpose**: Detailed schema analysis of 7 knowledge/memory tables for the METIS Knowledge Engine data model assessment.

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Database**: `ai_company_foundation`, schema `claude`
**Tables covered**: knowledge, knowledge_relations, knowledge_retrieval_log, session_facts, vault_embeddings, documents, project_workfiles

---

## Table of Contents

1. [claude.knowledge](#1-claudeknowledge)
2. [claude.knowledge_relations](#2-claudeknowledge_relations)
3. [claude.knowledge_retrieval_log](#3-claudeknowledge_retrieval_log)
4. [claude.session_facts](#4-claudesession_facts)
5. [claude.vault_embeddings](#5-claudevault_embeddings)
6. [claude.documents](#6-claudedocuments)
7. [claude.project_workfiles](#7-claudeproject_workfiles)
8. [Usage and Health Stats](#8-usage-and-health-stats)
9. [Cross-Table Analysis](#9-cross-table-analysis)

---
""")

    # ========================================================================
    # PER-TABLE SECTIONS
    # ========================================================================

    table_meta = {}
    for table in TABLES:
        print(f"\nResearching: claude.{table}")
        cols = get_columns(conn, table)
        row_count = get_row_count(conn, table)
        indexes = get_indexes(conn, table)
        fks = get_fks(conn, table)
        checks = get_check_constraints(conn, table)

        table_meta[table] = {
            "row_count": row_count,
            "cols": cols,
            "indexes": indexes,
        }

        print(f"  rows={row_count}, cols={len(cols)}, indexes={len(indexes)}, fks={len(fks)}")

        anchor = table.replace("_", "_")
        section_num = TABLES.index(table) + 1

        out = f"## {section_num}. `claude.{table}`\n\n"
        out += f"**Row count**: {row_count}\n\n"

        # --- Columns ---
        out += "### Columns\n\n"
        if cols:
            out += "| # | Column | Data Type | Nullable | Default | Description |\n"
            out += "| --- | --- | --- | --- | --- | --- |\n"
            for i, c in enumerate(cols, 1):
                dt = c["data_type"]
                udt = c["udt_name"]
                # Show full type for arrays and user-defined
                if dt == "ARRAY":
                    dtype_str = f"{udt}[]"
                elif dt == "USER-DEFINED":
                    dtype_str = udt
                elif dt == "character varying":
                    ml = c["character_maximum_length"]
                    dtype_str = f"varchar({ml})" if ml else "varchar"
                elif dt == "numeric":
                    p = c["numeric_precision"]
                    dtype_str = f"numeric({p})" if p else "numeric"
                else:
                    dtype_str = dt
                nullable = c["is_nullable"]
                default = str(c["column_default"] or "")
                if len(default) > 40:
                    default = default[:37] + "..."
                desc = str(c["description"] or "")
                out += f"| {i} | `{c['column_name']}` | `{dtype_str}` | {nullable} | `{default}` | {desc} |\n"
        else:
            out += "_No columns found — table may not exist._\n"
        out += "\n"

        # --- Indexes ---
        out += "### Indexes\n\n"
        if indexes:
            out += "| Index Name | Type | Primary | Unique | Columns |\n"
            out += "| --- | --- | --- | --- | --- |\n"
            for idx in indexes:
                cols_str = ", ".join(idx["columns"]) if idx["columns"] else ""
                out += f"| `{idx['index_name']}` | {idx['index_type']} | {idx['is_primary']} | {idx['is_unique']} | `{cols_str}` |\n"
        else:
            out += "_No indexes found._\n"
        out += "\n"

        # --- Foreign Keys ---
        out += "### Foreign Keys\n\n"
        if fks:
            out += "| Constraint | Column | References | On Delete |\n"
            out += "| --- | --- | --- | --- |\n"
            for fk in fks:
                out += f"| `{fk['constraint_name']}` | `{fk['column_name']}` | `claude.{fk['referenced_table']}.{fk['referenced_column']}` | {fk['delete_rule']} |\n"
        else:
            out += "_No foreign keys._\n"
        out += "\n"

        # --- Check Constraints ---
        out += "### Check Constraints\n\n"
        if checks:
            out += "| Constraint | Clause |\n"
            out += "| --- | --- |\n"
            for ch in checks:
                clause = str(ch["check_clause"]).replace("|", "\\|")
                out += f"| `{ch['constraint_name']}` | `{clause}` |\n"
        else:
            out += "_No check constraints._\n"
        out += "\n"

        sections.append(out)

    # ========================================================================
    # TABLE-SPECIFIC USAGE QUERIES
    # ========================================================================

    print("\nRunning usage queries...")

    # knowledge tier/type breakdown
    knowledge_breakdown_rows, err = run_query_safe(conn, """
        SELECT tier, knowledge_type, count(*), avg(confidence_level)::int AS avg_confidence
        FROM claude.knowledge
        GROUP BY tier, knowledge_type
        ORDER BY count(*) DESC
    """)
    # knowledge sample distinct types/tiers
    knowledge_tiers, _ = run_query_safe(conn, "SELECT DISTINCT tier FROM claude.knowledge ORDER BY tier")
    knowledge_types, _ = run_query_safe(conn, "SELECT DISTINCT knowledge_type FROM claude.knowledge ORDER BY knowledge_type")

    # session_facts
    session_facts_breakdown, err2 = run_query_safe(conn, """
        SELECT fact_type, count(*) FROM claude.session_facts GROUP BY fact_type ORDER BY count(*) DESC
    """)
    session_facts_types, _ = run_query_safe(conn, "SELECT DISTINCT fact_type FROM claude.session_facts ORDER BY fact_type")

    # vault_embeddings
    vault_agg, _ = run_query_safe(conn, """
        SELECT count(*) AS total_chunks,
               count(DISTINCT document_id) AS distinct_documents,
               avg(token_count)::int AS avg_tokens,
               min(token_count) AS min_tokens,
               max(token_count) AS max_tokens
        FROM claude.vault_embeddings
    """)
    vault_sources, _ = run_query_safe(conn, """
        SELECT doc_source, count(*) FROM claude.vault_embeddings GROUP BY doc_source ORDER BY count(*) DESC
    """)

    # project_workfiles
    workfiles_components, _ = run_query_safe(conn, """
        SELECT component, count(*), max(access_count) AS max_access
        FROM claude.project_workfiles
        GROUP BY component ORDER BY count(*) DESC
    """)

    # knowledge_relations
    relations_breakdown, _ = run_query_safe(conn, """
        SELECT relation_type, count(*), avg(strength)::numeric(3,2) AS avg_strength
        FROM claude.knowledge_relations
        GROUP BY relation_type ORDER BY count(*) DESC
    """)

    # knowledge_retrieval_log
    retrieval_log_range, _ = run_query_safe(conn, """
        SELECT count(*) AS total_logs,
               min(created_at) AS earliest,
               max(created_at) AS latest
        FROM claude.knowledge_retrieval_log
    """)
    retrieval_by_tier, _ = run_query_safe(conn, """
        SELECT tiers_queried, count(*) FROM claude.knowledge_retrieval_log GROUP BY tiers_queried ORDER BY count(*) DESC LIMIT 10
    """)
    retrieval_by_type, _ = run_query_safe(conn, """
        SELECT query_type, count(*), avg(results_count)::int AS avg_results
        FROM claude.knowledge_retrieval_log GROUP BY query_type ORDER BY count(*) DESC
    """)

    # documents
    docs_breakdown, _ = run_query_safe(conn, """
        SELECT doc_type, status, count(*) FROM claude.documents GROUP BY doc_type, status ORDER BY count(*) DESC
    """)

    # pg_stat
    pg_stats = get_pg_stats(conn)

    # ========================================================================
    # USAGE SECTION
    # ========================================================================

    usage_section = """## 8. Usage and Health Stats

### PostgreSQL Table Statistics

"""
    usage_section += fmt_rows(pg_stats)

    usage_section += """
---

### `claude.knowledge` — Tier / Type Breakdown

"""
    usage_section += fmt_rows(knowledge_breakdown_rows)
    usage_section += "\n**Distinct tiers**: " + ", ".join(str(r["tier"]) for r in knowledge_tiers) + "\n"
    usage_section += "\n**Distinct knowledge_type values**: " + ", ".join(str(r["knowledge_type"]) for r in knowledge_types) + "\n"

    usage_section += """
---

### `claude.session_facts` — Fact Type Breakdown

"""
    usage_section += fmt_rows(session_facts_breakdown)
    usage_section += "\n**Distinct fact_type values**: " + ", ".join(str(r["fact_type"]) for r in session_facts_types) + "\n"

    usage_section += """
---

### `claude.vault_embeddings` — Aggregate Stats

"""
    usage_section += fmt_rows(vault_agg)
    usage_section += "\n**By doc_source**:\n\n"
    usage_section += fmt_rows(vault_sources)

    usage_section += """
---

### `claude.project_workfiles` — By Component

"""
    usage_section += fmt_rows(workfiles_components)

    usage_section += """
---

### `claude.knowledge_relations` — By Relation Type

"""
    usage_section += fmt_rows(relations_breakdown)

    usage_section += """
---

### `claude.knowledge_retrieval_log` — Date Range and Volume

"""
    usage_section += fmt_rows(retrieval_log_range)
    usage_section += "\n**By query_type**:\n\n"
    usage_section += fmt_rows(retrieval_by_type)
    usage_section += "\n**By tiers_queried (top 10)**:\n\n"
    usage_section += fmt_rows(retrieval_by_tier)

    usage_section += """
---

### `claude.documents` — By doc_type and status

"""
    usage_section += fmt_rows(docs_breakdown)

    sections.append(usage_section)

    # ========================================================================
    # CROSS-TABLE ANALYSIS
    # ========================================================================

    print("\nRunning cross-table FK linkage queries...")

    # knowledge FK targets
    knowledge_fk_check, _ = run_query_safe(conn, """
        SELECT
            COUNT(*) AS total_knowledge,
            COUNT(session_id) AS has_session_id,
            COUNT(project_id) AS has_project_id
        FROM claude.knowledge
    """)

    # vault_embeddings -> documents linkage
    ve_doc_link, _ = run_query_safe(conn, """
        SELECT
            COUNT(*) AS total_ve,
            COUNT(document_id) AS with_document_id,
            COUNT(DISTINCT document_id) AS distinct_doc_ids
        FROM claude.vault_embeddings
    """)

    # knowledge_relations source/target overlap
    relations_overlap, _ = run_query_safe(conn, """
        SELECT
            COUNT(*) AS total_relations,
            COUNT(DISTINCT source_id) AS distinct_sources,
            COUNT(DISTINCT target_id) AS distinct_targets
        FROM claude.knowledge_relations
    """)

    # knowledge entries with at least 1 relation
    k_with_relations, _ = run_query_safe(conn, """
        SELECT
            COUNT(DISTINCT k.id) AS knowledge_entries_with_any_relation
        FROM claude.knowledge k
        WHERE EXISTS (
            SELECT 1 FROM claude.knowledge_relations r
            WHERE r.source_id = k.id OR r.target_id = k.id
        )
    """)

    # session_facts -> sessions link
    sf_session_link, _ = run_query_safe(conn, """
        SELECT
            COUNT(*) AS total_facts,
            COUNT(session_id) AS has_session_id,
            COUNT(DISTINCT session_id) AS distinct_sessions
        FROM claude.session_facts
    """)

    # project_workfiles project distribution
    workfiles_proj, _ = run_query_safe(conn, """
        SELECT
            COUNT(*) AS total_workfiles,
            COUNT(DISTINCT project_id) AS distinct_projects,
            COUNT(*) FILTER (WHERE is_pinned) AS pinned,
            COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_embedding
        FROM claude.project_workfiles
    """)

    # knowledge with/without embeddings
    k_embedding_coverage, _ = run_query_safe(conn, """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_embedding,
            COUNT(*) FILTER (WHERE embedding IS NULL) AS without_embedding
        FROM claude.knowledge
    """)

    # vault_embeddings with/without embeddings
    ve_embedding_coverage, _ = run_query_safe(conn, """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_embedding,
            COUNT(*) FILTER (WHERE embedding IS NULL) AS without_embedding
        FROM claude.vault_embeddings
    """)

    cross_section = """## 9. Cross-Table Analysis

### Linkage: `claude.knowledge` Session + Project Coverage

"""
    cross_section += fmt_rows(knowledge_fk_check)

    cross_section += """
### Embedding Coverage: `claude.knowledge`

"""
    cross_section += fmt_rows(k_embedding_coverage)

    cross_section += """
### Embedding Coverage: `claude.vault_embeddings`

"""
    cross_section += fmt_rows(ve_embedding_coverage)

    cross_section += """
### Linkage: `claude.vault_embeddings` -> `claude.documents`

"""
    cross_section += fmt_rows(ve_doc_link)

    cross_section += """
### Graph Density: `claude.knowledge_relations`

"""
    cross_section += fmt_rows(relations_overlap)
    cross_section += "\n"
    cross_section += fmt_rows(k_with_relations)

    cross_section += """
### Linkage: `claude.session_facts` -> Sessions

"""
    cross_section += fmt_rows(sf_session_link)

    cross_section += """
### `claude.project_workfiles` Coverage

"""
    cross_section += fmt_rows(workfiles_proj)

    sections.append(cross_section)

    # ========================================================================
    # FOOTER
    # ========================================================================
    sections.append("""---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: C:\\Projects\\claude-family\\docs\\metis-data-model-research-schemas.md
""")

    # ========================================================================
    # WRITE FILE
    # ========================================================================
    content = "\n".join(sections)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"\nWrote {len(content):,} chars to {OUTPUT_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
