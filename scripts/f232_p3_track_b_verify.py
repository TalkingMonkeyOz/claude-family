"""F232.P3 Track B verification — A: direct overlay query; B: writetime hook end-to-end."""
import os, sys, json
sys.path.insert(0, 'C:/Projects/claude-family/scripts')
from config import get_database_uri, get_db_connection  # noqa: E402
os.environ['DATABASE_URI'] = get_database_uri()
sys.path.insert(0, 'C:/Projects/project-hal')

print("=" * 70)
print("Verification A — overlay_get_full_context for send_message")
print("=" * 70)
from src.core.server import overlay_get_full_context  # noqa: E402
SERVER_V2 = r"C:\Projects\claude-family\mcp-servers\project-tools\server_v2.py"
result_a = overlay_get_full_context(
    project='claude-family',
    qualified_name='send_message',
    file_path=SERVER_V2,
)
# Strip embedding vector for printability
if isinstance(result_a, dict):
    overlay = result_a.get("overlay") or {}
    if isinstance(overlay, dict):
        overlay.pop("purpose_embedding", None)
print(json.dumps(result_a, indent=2, default=str)[:3000])
print()

print("=" * 70)
print("Verification B — writetime hook on server_v2.py")
print("=" * 70)
os.environ['F232_AGGREGATOR_MODE'] = 'live'
os.environ['CLAUDE_PROJECT_NAME'] = 'claude-family'
from coding_intelligence_writetime_hook import run  # noqa: E402

conn = get_db_connection()
result_b = run(
    {'tool_name': 'Edit', 'tool_input': {'file_path': 'mcp-servers/project-tools/server_v2.py'}},
    conn=conn,
)

resp = result_b.get('_response', {})
ctx = resp.get('additionalContext', '<NONE>')
print(f"outcome           : {result_b.get('outcome')}")
print(f"memories_surfaced : {result_b.get('memories_surfaced')}")
print(f"overlay_calls     : {result_b.get('overlay_calls')}")
print(f"overlay_results   : {len(result_b.get('overlay_results', []))} symbols")
print(f"injection_chars   : {result_b.get('injection_chars')}")
print(f"latency_ms        : {result_b.get('latency_ms')}")
print(f"fallback_reason   : {result_b.get('fallback_reason')}")
print()
print("--- additionalContext ---")
print(ctx)
print("--- end ---")
