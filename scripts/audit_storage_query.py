"""
One-shot storage audit query script.
Queries all storage mechanisms and prints results as JSON.
"""
import sys
import json
sys.path.insert(0, r'C:\Projects\claude-family\scripts')

from config import get_db_connection

conn = get_db_connection()
conn.autocommit = True

def q(sql, label):
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        # convert non-serializable types
        for row in rows:
            for k, v in row.items():
                if hasattr(v, 'isoformat'):
                    row[k] = v.isoformat()
                elif v is None:
                    row[k] = None
                else:
                    row[k] = str(v) if not isinstance(v, (int, float, bool, str)) else v
        print(f"=== {label} ===")
        print(json.dumps(rows, indent=2))
    except Exception as e:
        print(f"=== {label} ERROR: {e} ===")

# 1. Session Facts
q("""
SELECT fact_type, count(*) as cnt
FROM claude.session_facts
GROUP BY fact_type ORDER BY cnt DESC
""", "session_facts_by_type")

q("""
SELECT count(*) as total_facts,
       count(DISTINCT session_id) as distinct_sessions,
       min(stored_at) as oldest,
       max(stored_at) as newest,
       round(count(*)::numeric / nullif(count(DISTINCT session_id),0), 1) as avg_per_session
FROM claude.session_facts
""", "session_facts_summary")

# 2. Knowledge tiers
q("""
SELECT tier, count(*) as cnt,
       round(avg(confidence_level)) as avg_confidence,
       count(CASE WHEN embedding IS NOT NULL THEN 1 END) as has_embedding,
       count(CASE WHEN access_count > 0 THEN 1 END) as ever_accessed,
       max(access_count) as max_access_count,
       round(avg(access_count),1) as avg_access_count
FROM claude.knowledge
GROUP BY tier ORDER BY tier
""", "knowledge_by_tier")

q("""
SELECT knowledge_type, count(*) as cnt
FROM claude.knowledge
GROUP BY knowledge_type ORDER BY cnt DESC
""", "knowledge_by_type")

q("""
SELECT category, count(*) as cnt
FROM claude.knowledge
WHERE category IS NOT NULL
GROUP BY category ORDER BY cnt DESC
LIMIT 15
""", "knowledge_top_categories")

q("""
SELECT count(*) as total,
       min(created_at) as oldest,
       max(created_at) as newest,
       count(CASE WHEN source_project IS NOT NULL THEN 1 END) as has_project
FROM claude.knowledge
""", "knowledge_overall")

# 3. Knowledge Relations
q("""
SELECT relation_type, count(*) as cnt, round(avg(strength)::numeric, 2) as avg_strength
FROM claude.knowledge_relations
GROUP BY relation_type ORDER BY cnt DESC
""", "knowledge_relations")

q("""
SELECT count(*) as total FROM claude.knowledge_relations
""", "knowledge_relations_total")

# 4. Project Workfiles
q("""
SELECT component, count(*) as cnt,
       max(updated_at) as last_updated,
       sum(CASE WHEN is_pinned THEN 1 ELSE 0 END) as pinned,
       round(avg(access_count)) as avg_access,
       count(CASE WHEN embedding IS NOT NULL THEN 1 END) as has_embedding
FROM claude.project_workfiles
GROUP BY component ORDER BY cnt DESC
""", "workfiles_by_component")

q("""
SELECT count(*) as total,
       min(created_at) as oldest,
       max(created_at) as newest
FROM claude.project_workfiles
""", "workfiles_summary")

# 5. Vault Embeddings
q("""
SELECT count(*) as total_embeddings,
       count(DISTINCT document_id) as unique_docs,
       min(created_at) as oldest,
       max(created_at) as newest
FROM claude.vault_embeddings
""", "vault_embeddings_summary")

q("""
SELECT count(*) as total_docs,
       min(created_at) as oldest,
       max(created_at) as newest
FROM claude.documents
""", "vault_documents_summary")

# 6. Todos
q("""
SELECT status, count(*) as cnt,
       min(created_at) as oldest,
       max(created_at) as newest
FROM claude.todos
GROUP BY status ORDER BY cnt DESC
""", "todos_by_status")

q("""
SELECT count(*) as total FROM claude.todos
""", "todos_total")

# 7. Activities (WCC)
q("""
SELECT count(*) as total,
       count(CASE WHEN is_active THEN 1 END) as active_count,
       round(avg(access_count)) as avg_access,
       max(access_count) as max_access,
       min(created_at) as oldest,
       max(created_at) as newest
FROM claude.activities
""", "activities_summary")

q("""
SELECT name, access_count, is_active, last_accessed
FROM claude.activities
ORDER BY access_count DESC
LIMIT 10
""", "activities_top")

# 8. Messages
q("""
SELECT status, message_type, count(*) as cnt
FROM claude.messages
GROUP BY status, message_type ORDER BY cnt DESC
""", "messages_by_status_type")

q("""
SELECT count(*) as total,
       min(created_at) as oldest,
       max(created_at) as newest
FROM claude.messages
""", "messages_summary")

# 9. Audit Log
q("""
SELECT entity_type, count(*) as cnt,
       min(created_at) as oldest,
       max(created_at) as newest
FROM claude.audit_log
GROUP BY entity_type ORDER BY cnt DESC
""", "audit_log_by_entity")

q("""
SELECT count(*) as total FROM claude.audit_log
""", "audit_log_total")

# 10. Sessions
q("""
SELECT count(*) as total,
       count(CASE WHEN summary IS NOT NULL THEN 1 END) as has_summary,
       count(CASE WHEN end_time IS NOT NULL THEN 1 END) as properly_closed,
       min(session_start) as oldest,
       max(session_start) as newest
FROM claude.sessions
""", "sessions_summary")

# 11. Schema registry (bonus)
q("""
SELECT count(*) as total FROM claude.schema_registry
""", "schema_registry_total")

# 12. Protocol versions
q("""
SELECT version_number, is_active, created_at
FROM claude.protocol_versions
ORDER BY version_number DESC
LIMIT 5
""", "protocol_versions")

# 13. Features
q("""
SELECT status, count(*) as cnt
FROM claude.features
GROUP BY status ORDER BY cnt DESC
""", "features_by_status")

# 14. Feedback
q("""
SELECT status, feedback_type, count(*) as cnt
FROM claude.feedback
GROUP BY status, feedback_type ORDER BY cnt DESC
LIMIT 15
""", "feedback_summary")

# 15. Build tasks
q("""
SELECT status, count(*) as cnt
FROM claude.build_tasks
GROUP BY status ORDER BY cnt DESC
""", "build_tasks_by_status")

# 16. MCP usage log
q("""
SELECT count(*) as total,
       count(DISTINCT tool_name) as distinct_tools,
       min(called_at) as oldest,
       max(called_at) as newest
FROM claude.mcp_usage_log
""", "mcp_usage_summary")

q("""
SELECT tool_name, count(*) as cnt
FROM claude.mcp_usage_log
GROUP BY tool_name ORDER BY cnt DESC
LIMIT 15
""", "mcp_usage_top_tools")

conn.close()
print("=== DONE ===")
