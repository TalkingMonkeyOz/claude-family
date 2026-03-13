#!/usr/bin/env python3
"""
Schema audit script - collects all data needed for metis-data-model-research-full-schema.md
Runs all SQL queries and writes results to the output file.
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add scripts dir to path for config import
sys.path.insert(0, str(Path(__file__).parent))
from config import get_db_connection

OUTPUT_PATH = Path(r"C:\Projects\claude-family\docs\metis-data-model-research-full-schema.md")

def run_query(conn, sql, label=None):
    """Run a query and return (columns, rows)."""
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return cols, rows
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return [], [{"error": str(e)}]

def fmt_table(cols, rows, max_col_width=40):
    """Format query results as a markdown table."""
    if not cols:
        if rows and isinstance(rows[0], dict) and "error" in rows[0]:
            return f"ERROR: {rows[0]['error']}\n"
        return "No results\n"

    if not rows:
        header_line = "| " + " | ".join(cols) + " |"
        sep_line    = "| " + " | ".join("-" * len(c) for c in cols) + " |"
        return header_line + "\n" + sep_line + "\n\n_0 rows_\n"

    # Convert rows to list of lists
    if rows and isinstance(rows[0], dict):
        data = [list(str(r.get(c, "") if r.get(c, "") is not None else "NULL") for c in cols) for r in rows]
    else:
        data = [list(str(v) if v is not None else "NULL" for v in r) for r in rows]

    # Truncate wide values
    data = [[v[:max_col_width] + "..." if len(v) > max_col_width else v for v in row] for row in data]

    # Column widths
    widths = [max(len(c), max((len(row[i]) for row in data), default=0)) for i, c in enumerate(cols)]

    lines = []
    header = "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)) + " |"
    sep    = "| " + " | ".join("-" * w for w in widths) + " |"
    lines.append(header)
    lines.append(sep)
    for row in data:
        lines.append("| " + " | ".join(v.ljust(widths[i]) for i, v in enumerate(row)) + " |")

    lines.append(f"\n_{len(data)} rows_\n")
    return "\n".join(lines) + "\n"

def main():
    conn = get_db_connection(strict=True)
    out = []

    def section(title, level=2):
        prefix = "#" * level
        out.append(f"\n{prefix} {title}\n")

    def subsection(title):
        section(title, 3)

    def run(label, sql):
        subsection(label)
        out.append(f"```sql\n{sql.strip()}\n```\n")
        cols, rows = run_query(conn, sql)
        out.append(fmt_table(cols, rows))

    # ===== HEADER =====
    out.append(f"""---
projects:
- claude-family
tags:
- schema-audit
- data-model
- metis
synced: false
---

# Claude Family - Full Schema Audit
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Database**: ai_company_foundation, schema: claude
**Purpose**: Dead weight detection, usage patterns, and data quality for Project Metis data model design.

---
""")

    # ===== SECTION 1: FULL TABLE INVENTORY =====
    section("1. Full Table Inventory")

    run("All tables in claude schema (alphabetical)", """
SELECT tablename
FROM pg_tables
WHERE schemaname='claude'
ORDER BY tablename;
""")

    run("Row counts, last analyze, last vacuum (sorted by row count desc)", """
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    last_autoanalyze,
    last_autovacuum,
    last_analyze,
    last_vacuum
FROM pg_stat_user_tables
WHERE schemaname='claude'
ORDER BY n_live_tup DESC;
""")

    # ===== SECTION 2: DEAD WEIGHT DETECTION =====
    section("2. Dead Weight Detection")

    run("Tables with 0 live rows", """
SELECT relname, n_live_tup, seq_scan, idx_scan
FROM pg_stat_user_tables
WHERE schemaname='claude' AND n_live_tup = 0
ORDER BY relname;
""")

    run("Tables with < 10 live rows (low usage)", """
SELECT relname, n_live_tup, seq_scan, idx_scan, seq_scan + COALESCE(idx_scan, 0) as total_scans
FROM pg_stat_user_tables
WHERE schemaname='claude' AND n_live_tup < 10
ORDER BY n_live_tup ASC, relname;
""")

    run("20 least-scanned tables (by total seq+idx scans)", """
SELECT relname, n_live_tup, seq_scan, COALESCE(idx_scan, 0) as idx_scan, seq_scan + COALESCE(idx_scan, 0) as total_scans
FROM pg_stat_user_tables
WHERE schemaname='claude'
ORDER BY total_scans ASC
LIMIT 20;
""")

    run("Tables with high dead tuple ratio (fragmentation)", """
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    CASE WHEN n_live_tup + n_dead_tup > 0
         THEN ROUND(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 1)
         ELSE 0 END as dead_pct
FROM pg_stat_user_tables
WHERE schemaname='claude' AND n_dead_tup > 0
ORDER BY dead_pct DESC;
""")

    # ===== SECTION 3: SELF-DOCUMENTING SCHEMA =====
    section("3. Self-Documenting Schema Check")

    run("column_registry overall coverage", """
SELECT count(*) as total_entries, count(DISTINCT table_name) as tables_covered
FROM claude.column_registry;
""")

    run("column_registry - columns tracked per table", """
SELECT table_name, count(*) as columns_tracked
FROM claude.column_registry
GROUP BY table_name
ORDER BY columns_tracked DESC;
""")

    run("column_registry - tables in pg_tables but NOT in column_registry", """
SELECT t.tablename as missing_from_registry
FROM pg_tables t
WHERE t.schemaname = 'claude'
  AND t.tablename NOT IN (SELECT DISTINCT table_name FROM claude.column_registry)
ORDER BY t.tablename;
""")

    run("Tables with pg_class descriptions (COMMENT ON TABLE)", """
SELECT c.relname, obj_description(c.oid) as table_comment
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'claude'
  AND c.relkind = 'r'
  AND obj_description(c.oid) IS NOT NULL
ORDER BY c.relname;
""")

    run("Tables WITHOUT pg_class descriptions", """
SELECT c.relname
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'claude'
  AND c.relkind = 'r'
  AND obj_description(c.oid) IS NULL
ORDER BY c.relname;
""")

    # ===== SECTION 4: BPMN PROCESS REGISTRY =====
    section("4. BPMN Process Registry Status")

    run("Overall BPMN process count", """
SELECT count(*) as total_processes, count(DISTINCT project_name) as distinct_projects
FROM claude.bpmn_processes;
""")

    run("BPMN processes by project", """
SELECT project_name, count(*) as process_count, max(synced_at) as last_sync
FROM claude.bpmn_processes
GROUP BY project_name
ORDER BY process_count DESC;
""")

    run("BPMN process list (all)", """
SELECT process_id, project_name, name, level, synced_at
FROM claude.bpmn_processes
ORDER BY project_name, level, name;
""")

    run("BPMN processes with embeddings vs without", """
SELECT
    COUNT(*) FILTER (WHERE embedding IS NOT NULL) as with_embedding,
    COUNT(*) FILTER (WHERE embedding IS NULL) as without_embedding,
    COUNT(*) as total
FROM claude.bpmn_processes;
""")

    # ===== SECTION 5: WORKFLOW TRANSITIONS =====
    section("5. Workflow Transitions (State Machine)")

    run("Transition counts by entity_type", """
SELECT entity_type, count(*) as transition_count
FROM claude.workflow_transitions
GROUP BY entity_type
ORDER BY entity_type;
""")

    run("All transitions (entity_type, from_status, to_status, conditions)", """
SELECT entity_type, from_status, to_status, condition, side_effects
FROM claude.workflow_transitions
ORDER BY entity_type, from_status, to_status;
""")

    # ===== SECTION 6: INDEX ANALYSIS =====
    section("6. Index Analysis")

    run("Top 30 most-used indexes (by idx_scan)", """
SELECT
    indexrelname,
    relname as table_name,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname='claude'
ORDER BY idx_scan DESC
LIMIT 30;
""")

    run("Unused indexes (idx_scan = 0)", """
SELECT
    indexrelname,
    relname as table_name,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname='claude' AND idx_scan = 0
ORDER BY relname, indexrelname;
""")

    run("Index sizes (all indexes, sorted by size)", """
SELECT
    indexrelname,
    relname as table_name,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    idx_scan
FROM pg_stat_user_indexes
WHERE schemaname='claude'
ORDER BY pg_relation_size(indexrelid) DESC;
""")

    # ===== SECTION 7: TABLE SIZE ANALYSIS =====
    section("7. Table Size Analysis")

    run("Table sizes (including indexes)", """
SELECT
    relname as table_name,
    pg_size_pretty(pg_total_relation_size(c.oid)) as total_size,
    pg_size_pretty(pg_relation_size(c.oid)) as table_size,
    pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid)) as index_size
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'claude' AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC;
""")

    # ===== SECTION 8: KEY TABLE CONTENTS (SPOT CHECK) =====
    section("8. Key Table Spot Checks")

    run("claude.projects - all projects", """
SELECT project_id, name, client_domain, status, project_type, created_at
FROM claude.projects
ORDER BY client_domain, name;
""")

    run("claude.features - active features (in_progress + planned)", """
SELECT feature_code, title, status, priority, created_at
FROM claude.features
WHERE status IN ('in_progress', 'planned')
ORDER BY status, priority, created_at;
""")

    run("claude.features - count by status", """
SELECT status, count(*) as cnt
FROM claude.features
GROUP BY status
ORDER BY cnt DESC;
""")

    run("claude.build_tasks - count by status", """
SELECT status, count(*) as cnt
FROM claude.build_tasks
GROUP BY status
ORDER BY cnt DESC;
""")

    run("claude.sessions - recent sessions (last 10)", """
SELECT session_id, project_name, started_at, ended_at, summary IS NOT NULL as has_summary
FROM claude.sessions
ORDER BY started_at DESC
LIMIT 10;
""")

    run("claude.knowledge - tier distribution", """
SELECT tier, memory_type, count(*) as cnt, AVG(confidence) as avg_confidence
FROM claude.knowledge
GROUP BY tier, memory_type
ORDER BY tier, memory_type;
""")

    run("claude.mcp_usage - top tools used (last 30 days)", """
SELECT tool_name, count(*) as usage_count, max(used_at) as last_used
FROM claude.mcp_usage
WHERE used_at > NOW() - INTERVAL '30 days'
GROUP BY tool_name
ORDER BY usage_count DESC
LIMIT 30;
""")

    run("claude.todos - count by status and source", """
SELECT status, source, count(*) as cnt
FROM claude.todos
GROUP BY status, source
ORDER BY cnt DESC;
""")

    run("claude.feedback - count by type and status", """
SELECT feedback_type, status, count(*) as cnt
FROM claude.feedback
GROUP BY feedback_type, status
ORDER BY feedback_type, status;
""")

    run("claude.project_workfiles - count and components", """
SELECT count(*) as total_workfiles, count(DISTINCT component) as distinct_components, count(DISTINCT project_id) as distinct_projects
FROM claude.project_workfiles;
""")

    run("claude.activities - all activities", """
SELECT activity_id, project_id, name, is_active, access_count, last_accessed_at
FROM claude.activities
ORDER BY access_count DESC;
""")

    run("claude.agent_sessions - count", """
SELECT count(*) as total FROM claude.agent_sessions;
""")

    run("claude.audit_log - recent entries (last 10)", """
SELECT entity_type, entity_id, from_status, to_status, changed_at
FROM claude.audit_log
ORDER BY changed_at DESC
LIMIT 10;
""")

    run("claude.messages - count by status and message_type", """
SELECT status, message_type, count(*) as cnt
FROM claude.messages
GROUP BY status, message_type
ORDER BY cnt DESC;
""")

    run("claude.protocol_versions - active protocol", """
SELECT version_id, version_label, is_active, created_at
FROM claude.protocol_versions
ORDER BY created_at DESC
LIMIT 5;
""")

    # ===== FOOTER =====
    out.append("""
---
**Version**: 1.0
**Created**: """ + datetime.now().strftime('%Y-%m-%d') + """
**Updated**: """ + datetime.now().strftime('%Y-%m-%d') + """
**Location**: C:\\Projects\\claude-family\\docs\\metis-data-model-research-full-schema.md
""")

    conn.close()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(out), encoding="utf-8")
    print(f"Written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
