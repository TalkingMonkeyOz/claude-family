"""F232.P3 Track B — Free heuristic seed of 10 hot CF symbols into hal.intent_overlay.

Calls hal's `src.overlay.seeder.seed_file` with explicit records (bypasses extraction).
No LLM calls — purpose comes from docstring first sentence; concerns come from text-pattern rules.
"""
from __future__ import annotations
import json, os, sys
from types import SimpleNamespace

# Wire DATABASE_URI for hal's src.core.db before importing
sys.path.insert(0, 'C:/Projects/claude-family/scripts')
from config import get_database_uri  # noqa: E402
os.environ['DATABASE_URI'] = get_database_uri()

sys.path.insert(0, 'C:/Projects/project-hal')
from src.overlay.seeder import seed_file  # noqa: E402
from src.overlay.extractor import ExtractedIntent  # noqa: E402
from src.core.db import execute_query  # noqa: E402

SERVER_V2 = r"C:\Projects\claude-family\mcp-servers\project-tools\server_v2.py"

# Heuristic-derived intent records.
# purpose = first sentence of docstring (split on period or blank line).
# relationships = inferred from body verbs / shadow tools called.
# concerns = pattern-match against body source (auth/messaging/work-tracking/knowledge/embedding).
RECORDS = [
    {
        "symbol_name": "send_message",
        "qualified_name": "send_message",
        "kind": "function",
        "file_path": SERVER_V2,
        "line_number": 8364,
        "end_line": 8517,
        "intent": {
            "purpose": "Send a message to another Claude instance or project.",
            "relationships": [
                ["writes", "claude.messages"],
                ["reads", "claude.workspaces"],
                ["reads", "claude.sessions"],
            ],
            "invariants": [],
            "concerns": ["messaging", "work-tracking"],
        },
    },
    {
        "symbol_name": "inbox",
        "qualified_name": "inbox",
        "kind": "function",
        "file_path": SERVER_V2,
        "line_number": 13153,
        "end_line": 13206,
        "intent": {
            "purpose": "Check, search, and manage incoming messages from other Claude instances.",
            "relationships": [
                ["calls", "bulk_acknowledge"],
                ["calls", "acknowledge"],
                ["calls", "get_message_history"],
                ["calls", "get_unactioned_messages"],
                ["calls", "check_inbox"],
            ],
            "invariants": [],
            "concerns": ["messaging"],
        },
    },
    {
        "symbol_name": "reply_to",
        "qualified_name": "reply_to",
        "kind": "function",
        "file_path": SERVER_V2,
        "line_number": 8672,
        "end_line": 8772,
        "intent": {
            "purpose": "Reply to a specific message; routes to the sender's PROJECT (not session) and sets threading.",
            "relationships": [
                ["calls", "send_message"],
                ["reads", "claude.messages"],
                ["writes", "claude.messages"],
                ["reads", "claude.sessions"],
            ],
            "invariants": [
                "Auto-marks the original message as 'read' on reply (only if currently 'pending').",
            ],
            "concerns": ["messaging"],
        },
    },
    {
        "symbol_name": "work_create",
        "qualified_name": "work_create",
        "kind": "function",
        "file_path": SERVER_V2,
        "line_number": 12489,
        "end_line": 12553,
        "intent": {
            "purpose": "Create any work item: feature, feedback, or task.",
            "relationships": [
                ["calls", "create_feature"],
                ["calls", "create_feedback"],
                ["calls", "create_linked_task"],
                ["calls", "add_build_task"],
            ],
            "invariants": [
                "type='task' must be paired with a feature_code, verification, and files_affected.",
            ],
            "concerns": ["work-tracking"],
        },
    },
    {
        "symbol_name": "work_status",
        "qualified_name": "work_status",
        "kind": "function",
        "file_path": SERVER_V2,
        "line_number": 12557,
        "end_line": 12611,
        "intent": {
            "purpose": "Change status of any work item (start, complete, advance, promote, resolve, add_dep).",
            "relationships": [
                ["calls", "start_work"],
                ["calls", "_complete_work_impl"],
                ["calls", "advance_status"],
                ["calls", "promote_feedback"],
                ["calls", "add_dependency"],
            ],
            "invariants": [],
            "concerns": ["work-tracking"],
        },
    },
    {
        "symbol_name": "work_board",
        "qualified_name": "work_board",
        "kind": "function",
        "file_path": SERVER_V2,
        "line_number": 12615,
        "end_line": 12635,
        "intent": {
            "purpose": "Read work tracking state: build board, ready tasks, or incomplete todos.",
            "relationships": [
                ["calls", "get_build_board"],
                ["calls", "get_ready_tasks"],
                ["calls", "get_incomplete_todos"],
            ],
            "invariants": [],
            "concerns": ["work-tracking"],
        },
    },
    {
        "symbol_name": "remember",
        "qualified_name": "remember",
        "kind": "function",
        "file_path": SERVER_V2,
        "line_number": 5982,
        "end_line": 6014,
        "intent": {
            "purpose": "Store a memory with automatic tier classification, dedup/merge, and relation linking.",
            "relationships": [
                ["calls", "tool_remember"],
                ["writes", "claude.knowledge"],
                ["writes", "claude.session_facts"],
            ],
            "invariants": [
                "Quality gate rejects content under 80 chars or junk patterns (task acks, agent handoffs).",
                "Auto-deduplicates: union-merges entries with similarity above 0.75.",
            ],
            "concerns": ["knowledge", "embedding"],
        },
    },
    {
        "symbol_name": "entity_store",
        "qualified_name": "entity_store",
        "kind": "function",
        "file_path": SERVER_V2,
        "line_number": 12888,
        "end_line": 12926,
        "intent": {
            "purpose": "Create or update entities in the reference library.",
            "relationships": [
                ["calls", "update_entity"],
                ["calls", "catalog"],
                ["writes", "claude.entities"],
            ],
            "invariants": [
                "Requires either entity_type+properties (create) or entity_id/entity_name+patch (update).",
            ],
            "concerns": ["knowledge"],
        },
    },
    {
        "symbol_name": "article_write",
        "qualified_name": "article_write",
        "kind": "function",
        "file_path": SERVER_V2,
        "line_number": 12991,
        "end_line": 13045,
        "intent": {
            "purpose": "Create or update knowledge articles, sections, and lifecycle.",
            "relationships": [
                ["calls", "manage_article"],
                ["calls", "write_article_section"],
                ["calls", "write_article"],
                ["writes", "claude.articles"],
                ["writes", "claude.article_sections"],
            ],
            "invariants": [],
            "concerns": ["knowledge", "embedding"],
        },
    },
    {
        "symbol_name": "workfile_store",
        "qualified_name": "workfile_store",
        "kind": "function",
        "file_path": SERVER_V2,
        "line_number": 12796,
        "end_line": 12843,
        "intent": {
            "purpose": "Store, archive, or delete workfiles in the filing cabinet.",
            "relationships": [
                ["calls", "archive_workfile"],
                ["calls", "delete_workfile"],
                ["calls", "stash"],
                ["writes", "claude.workfiles"],
            ],
            "invariants": [
                "Content over 500 lines flags chunking_required; auto_chunk=True splits on H2 headers.",
            ],
            "concerns": ["knowledge"],
        },
    },
]


def _to_dataclass(rec: dict) -> ExtractedIntent:
    """Convert dict record to ExtractedIntent dataclass instance."""
    return ExtractedIntent(
        symbol_name=rec["symbol_name"],
        qualified_name=rec["qualified_name"],
        kind=rec["kind"],
        file_path=rec["file_path"],
        line_number=rec["line_number"],
        end_line=rec["end_line"],
        intent=rec["intent"],
    )


def main():
    project_id_rows = execute_query(
        "SELECT project_id::text AS pid FROM claude.projects WHERE project_name = %s",
        ("claude-family",),
    )
    if not project_id_rows:
        print("ERROR: claude-family project not found in claude.projects")
        return 1
    project_id = project_id_rows[0]["pid"]
    print(f"project_id resolved: {project_id}")

    records = [_to_dataclass(r) for r in RECORDS]
    print(f"Calling seed_file with {len(records)} records...")
    stats = seed_file(project_id, records=records)
    print(f"Result: {json.dumps(stats, indent=2)}")

    # Diagnostic: which symbols failed to link?
    if stats.get("symbol_linked", 0) < len(records):
        print(f"\n[DIAGNOSTIC] {len(records) - stats['symbol_linked']} records did not resolve to a CKG symbol.")
        print("Per-symbol resolution check:")
        for r in RECORDS:
            rows = execute_query(
                """
                SELECT symbol_id::text AS sid, line_number
                FROM claude.code_symbols
                WHERE project_id = %s AND file_path = %s AND name = %s
                ORDER BY ABS(line_number - %s)
                LIMIT 1
                """,
                (project_id, r["file_path"], r["symbol_name"], r["line_number"]),
            )
            status = "LINKED" if rows else "MISSING"
            ckg_line = rows[0]["line_number"] if rows else "-"
            print(f"  [{status}] {r['symbol_name']:20s}  rec_line={r['line_number']:5d}  ckg_line={ckg_line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
