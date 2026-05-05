"""F232.P3 Track B v2 — AST-driven heuristic seed of remaining server_v2.py MCP tools.

Programmatic version of f232_p3_track_b_seed.py. Walks the server_v2.py AST,
extracts docstring + body for each top-level function in TARGETS, builds an
ExtractedIntent record from heuristics, calls hal's seed_file in batches.

Heuristics (no LLM):
  purpose       = first sentence of docstring (period-or-newline-bounded)
  relationships = body grep for write/read/call patterns + claude.* / hal.* tables
  concerns      = body keyword match against the spec's concerns vocab
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, "C:/Projects/claude-family/scripts")
from config import get_database_uri  # noqa: E402

os.environ["DATABASE_URI"] = get_database_uri()

sys.path.insert(0, "C:/Projects/project-hal")
from src.core.db import execute_query  # noqa: E402
from src.overlay.extractor import ExtractedIntent  # noqa: E402
from src.overlay.seeder import seed_file  # noqa: E402

SERVER_V2 = r"C:\Projects\claude-family\mcp-servers\project-tools\server_v2.py"

# CKG + coding + knowledge + workfile + entity + article + memory + session +
# BPMN + protocol + config + work-tracking + activity + reminder + secret +
# messaging tools that hal hasn't already covered (per overlay query 2026-05-05).
TARGETS: List[str] = [
    # CKG / code intelligence
    "index_codebase", "find_symbol", "get_context", "check_collision",
    "get_module_map", "find_similar", "get_dependency_graph",
    "code_search", "code_context",
    # Knowledge / memory
    "store_knowledge", "recall_knowledge", "graph_search", "decay_knowledge",
    "consolidate_memories", "list_memories", "update_memory", "archive_memory",
    "merge_memories", "link_knowledge", "get_related_knowledge",
    "mark_knowledge_applied", "memory_manage",
    # Session
    "recall_session_fact", "list_session_facts", "recall_previous_session_facts",
    "store_session_notes", "get_session_notes", "session_manage",
    "save_checkpoint", "recover_session",
    # Articles / entities / workfiles / catalog
    "write_article", "write_article_section", "recall_articles", "read_article",
    "manage_article", "article_read",
    "link_resources", "get_linked_resources", "recall_entities", "explore_entities",
    "update_entity", "register_identity", "register_project",
    "archive_workfile", "delete_workfile", "list_workfiles", "search_workfiles",
    "stash", "unstash", "assemble_context", "catalog",
    # BPMN / protocol
    "sync_bpmn_processes", "search_bpmn_processes", "bpmn_search",
    "get_active_protocol", "get_protocol_history", "update_protocol",
    "standing_orders", "protocol",
    # Config / deploy
    "update_claude_md", "profile_read", "profile_update",
    "skill_read", "skill_update", "rule_read", "rule_update",
    "deploy_claude_md", "deploy_project", "regenerate_settings",
    "update_config", "config_manage", "system_info", "system_maintenance",
    # Work tracking
    "advance_status", "start_work", "complete_work", "get_build_board",
    "add_dependency", "get_work_context", "create_linked_task",
    "get_incomplete_todos", "get_ready_tasks", "update_work_status",
    "create_feedback", "create_feature", "add_build_task",
    "promote_feedback", "resolve_feedback",
    # Messaging
    "channel_status", "list_recipients", "check_inbox", "broadcast",
    "get_active_sessions", "bulk_acknowledge", "get_unactioned_messages",
    "get_message_history", "send_msg",
    # Activities / scheduling
    "create_activity", "list_activities", "update_activity",
    "create_reminder", "list_reminders", "snooze_reminder",
    "job_template", "job_cancel",
    # Books / conversations
    "store_book", "store_book_reference", "recall_book_reference",
    "extract_insights", "search_conversations", "extract_conversation",
    "book_store", "book_read",
    # Secrets
    "set_secret", "get_secret", "list_secrets", "delete_secret",
    "load_project_secrets",
    # Misc dispatchers
    "link",
]


# ---------------------------------------------------------------------------
# Heuristic extractors
# ---------------------------------------------------------------------------


_FIRST_SENTENCE = re.compile(r"^(.+?)(?:\.\s|\n\n|\n[A-Z])", re.S)


def first_sentence(docstring: str) -> str:
    if not docstring:
        return ""
    m = _FIRST_SENTENCE.match(docstring.strip())
    if m:
        return m.group(1).strip().rstrip(".") + "."
    return docstring.strip().splitlines()[0].rstrip(".") + "."


# Concern keyword vocabulary — body match anywhere triggers the concern tag.
CONCERN_RULES: List[Tuple[str, List[str]]] = [
    ("messaging", [
        r"\bclaude\.messages\b",
        r"\bsend_message\b",
        r"\bbroadcast\b",
        r"\binbox\b",
        r"\bconversation\b",
    ]),
    ("knowledge", [
        r"\bclaude\.knowledge\b",
        r"\bremember\(",
        r"\brecall_memories\b",
        r"\bembedding",
        r"\barticle",
        r"\bmemory_manage\b",
    ]),
    ("entity-catalog", [
        r"\bclaude\.entities\b",
        r"\bentity_store\b",
        r"\bentity_read\b",
        r"\bdomain_concept\b",
    ]),
    ("workfile", [
        r"\bclaude\.workfiles?\b",
        r"\bworkfile_store\b",
        r"\bworkfile_read\b",
        r"\bstash\b",
        r"\bunstash\b",
    ]),
    ("work-tracking", [
        r"\bclaude\.feedback\b",
        r"\bclaude\.features\b",
        r"\bclaude\.build_tasks\b",
        r"\bclaude\.todos\b",
        r"\bwork_create\b",
        r"\bwork_status\b",
        r"\bwork_board\b",
        r"\bcreate_feedback\b",
        r"\bcreate_feature\b",
    ]),
    ("auth", [
        r"\bclaude\.secrets\b",
        r"\bcredential",
        r"\bsecret\(",
        r"\bset_secret\b",
        r"\bget_secret\b",
    ]),
    ("session", [
        r"\bclaude\.sessions\b",
        r"\bsession_facts\b",
        r"\bstart_session\b",
        r"\bend_session\b",
    ]),
    ("ckg", [
        r"\bclaude\.code_symbols\b",
        r"\bckg",
        r"\bindex_codebase\b",
        r"\bfind_symbol\b",
        r"\bcode_context\b",
    ]),
    ("bpmn", [
        r"\bbpmn",
        r"\bclaude\.bpmn",
        r"\bsync_bpmn_processes\b",
    ]),
    ("config", [
        r"\bsettings\.local\.json\b",
        r"\bclaude\.profiles\b",
        r"\bclaude\.skills\b",
        r"\bclaude\.rules\b",
        r"\bdeploy_project\b",
        r"\bconfig_templates\b",
    ]),
    ("scheduling", [
        r"\bclaude\.scheduled_jobs\b",
        r"\bclaude\.task_queue\b",
        r"\bjob_enqueue\b",
        r"\bjob_schedule\b",
        r"\bcreate_reminder\b",
    ]),
    ("protocol", [
        r"\bclaude\.protocol_versions\b",
        r"\bget_active_protocol\b",
    ]),
]


def detect_concerns(body_src: str) -> List[str]:
    hits: List[str] = []
    for tag, patterns in CONCERN_RULES:
        if any(re.search(p, body_src, re.I) for p in patterns):
            hits.append(tag)
    if not hits:
        hits = ["general"]
    return hits


_TABLE_WRITE = re.compile(
    r"\b(INSERT INTO|UPDATE|DELETE FROM|UPSERT INTO)\s+([\w\.]+)", re.I
)
_TABLE_READ = re.compile(r"\bFROM\s+([\w\.]+)", re.I)
_FN_CALL = re.compile(r"\b([a-z_][a-z0-9_]+)\s*\(")
# Tools we ignore for the relationship graph (too noisy or std-lib).
_BORING_CALLS = {
    "len", "str", "int", "float", "bool", "list", "dict", "tuple", "set",
    "print", "isinstance", "hasattr", "getattr", "setattr", "type",
    "range", "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "any", "all", "min", "max", "sum", "open", "format", "json", "re",
    "datetime", "now", "today", "execute", "fetchone", "fetchall",
    "cursor", "commit", "rollback", "close", "join", "split", "strip",
    "lower", "upper", "replace", "startswith", "endswith", "append",
    "extend", "get", "items", "keys", "values", "pop", "insert",
    "Optional", "List", "Dict", "Tuple", "Any", "Callable",
}


def detect_relationships(body_src: str, target_funcs: set) -> List[List[str]]:
    rels: List[List[str]] = []
    seen: set = set()

    for kind_kw, table in _TABLE_WRITE.findall(body_src):
        key = ("writes", table.lower())
        if key not in seen:
            rels.append(["writes", table])
            seen.add(key)
    for table in _TABLE_READ.findall(body_src):
        # SQL FROM clause includes joined tables. Filter common SQL keywords
        # like WHERE / GROUP BY accidentally matching.
        if table.upper() in {"WHERE", "GROUP", "ORDER", "LIMIT", "DUAL"}:
            continue
        key = ("reads", table.lower())
        if key not in seen:
            rels.append(["reads", table])
            seen.add(key)
    for fn in _FN_CALL.findall(body_src):
        if fn in _BORING_CALLS or fn in {"_", "self", "cls"}:
            continue
        if fn in target_funcs:
            key = ("calls", fn)
            if key not in seen:
                rels.append(["calls", fn])
                seen.add(key)
    # Cap relationships to keep payload sane.
    return rels[:12]


# ---------------------------------------------------------------------------
# AST walk
# ---------------------------------------------------------------------------


def collect_records(file_path: str, targets: List[str]) -> List[ExtractedIntent]:
    src = open(file_path, encoding="utf-8").read()
    tree = ast.parse(src, filename=file_path)
    target_set = set(targets)
    # All function names in the file, for "calls" relationship matching.
    all_fn_names: set = {
        n.name for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    records: List[ExtractedIntent] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in target_set:
            continue
        docstring = ast.get_docstring(node) or ""
        purpose = first_sentence(docstring)
        if not purpose:
            purpose = f"MCP tool {node.name} (purpose inferred at seed time)."
        body_src = ast.get_source_segment(src, node) or ""
        concerns = detect_concerns(body_src)
        relationships = detect_relationships(body_src, all_fn_names)
        end_line = getattr(node, "end_lineno", node.lineno)
        records.append(
            ExtractedIntent(
                symbol_name=node.name,
                qualified_name=node.name,
                kind="function",
                file_path=file_path,
                line_number=node.lineno,
                end_line=end_line,
                intent={
                    "purpose": purpose[:500],  # cap for embedding sanity
                    "relationships": relationships,
                    "invariants": [],
                    "concerns": concerns,
                },
            )
        )
    return records


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main() -> int:
    project_id_rows = execute_query(
        "SELECT project_id::text AS pid FROM claude.projects WHERE project_name = %s",
        ("claude-family",),
    )
    if not project_id_rows:
        print("ERROR: claude-family project not found in claude.projects")
        return 1
    project_id = project_id_rows[0]["pid"]
    print(f"project_id resolved: {project_id}")

    records = collect_records(SERVER_V2, TARGETS)
    print(f"AST collected {len(records)} records (out of {len(TARGETS)} targets)")

    # Spec sanity — flag any targets we couldn't extract.
    found_names = {r.symbol_name for r in records}
    missing = [t for t in TARGETS if t not in found_names]
    if missing:
        print(f"WARN: {len(missing)} targets not found in AST: {missing[:8]}{'...' if len(missing) > 8 else ''}")

    # Batch in groups of 20 — keeps each seed_file call bounded.
    BATCH = 20
    total_inserted = 0
    total_updated = 0
    total_linked = 0
    total_embedded = 0
    for i in range(0, len(records), BATCH):
        batch = records[i:i + BATCH]
        print(f"Seeding batch {i // BATCH + 1}: {len(batch)} records ({batch[0].symbol_name} … {batch[-1].symbol_name})")
        stats = seed_file(project_id, records=batch)
        total_inserted += stats.get("inserted", 0)
        total_updated += stats.get("updated", 0)
        total_linked += stats.get("symbol_linked", 0)
        total_embedded += stats.get("embedded", 0)
        print(f"  -> {json.dumps({k: v for k, v in stats.items() if not isinstance(v, list)})}")

    print(json.dumps({
        "total_records": len(records),
        "inserted": total_inserted,
        "updated": total_updated,
        "symbol_linked": total_linked,
        "embedded": total_embedded,
        "missing_targets": missing,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
