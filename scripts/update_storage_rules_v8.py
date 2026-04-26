#!/usr/bin/env python3
"""Update claude.rules storage-rules from v7 -> v8.

Adds three new sections at the end:
  - Memory-Update Discipline (Rule 7)
  - Non-Destructive Migration (MANDATORY)
  - Tool-Discovery Reflex (MANDATORY)

Updates both 'global' and 'project' scope rows. Bumps version to 8.
After running, run config_manage(action='deploy_project', components=['rules']).

Idempotent: re-running with v8 content is a no-op (same content).
Non-destructive: existing v7 content is preserved + extended.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_database_uri
import psycopg2


V8_ADDENDUM = """

## Memory-Update Discipline (Rule 7, NEW 2026-04-26)

**Every system change is recorded in memory before commit.** This replaces the vault paper trail (vault is sunset).

**When this applies**: any change to hooks, rules, schemas, BPMN models, MCP server code, deployed configs, architecture decisions, or anything in the System Change Process scope.

**What to do**:
1. Make the change
2. **Before commit**: `remember(content=..., memory_type='decision'|'pattern'|'gotcha')` describing what changed and why
3. Reference any FB# / F# / BT# / commit SHA so future Claude can trace
4. Commit

**Why**: vault used to record every architectural decision in markdown so a fresh session could read the change-log. Memory replaces that role. If the change isn't in memory, it's invisible to future Claude.

**Test**: would a different Claude instance starting fresh tomorrow understand what just changed and why? If no, you didn't remember enough.

## Non-Destructive Migration (MANDATORY, NEW 2026-04-26)

**Every change preserves existing state.** Burned by FB320 (deep-merge bug wiped workspace overrides). Not happening again.

**Schema migrations**: ADDITIVE only.
- `ADD COLUMN ... NULL` ✅
- `CREATE INDEX IF NOT EXISTS` ✅
- `DROP COLUMN` ❌ (use deprecation envelope, retire later)
- `ALTER COLUMN ... NOT NULL` without default ❌
- `RENAME COLUMN` ❌ (add new + dual-write + retire)

**Config deployments**: PRESERVE overrides.
- `generate_project_settings.py` keeps existing permissions (line 489-490)
- Workspace `hooks` overrides must merge, not replace
- Per-project secrets/env never get clobbered by global deploy

**Backfills**: IDEMPOTENT.
- `WHERE column IS NULL` guard so re-running doesn't overwrite populated rows
- Never `UPDATE … SET col = …` without filter — use the IS NULL discriminator
- Never bulk DELETE without explicit user confirmation

**Test**: can you run this change twice and get the same result? If no, it's not idempotent. Can a user with overrides run a deploy without losing them? If no, it's destructive.

## Tool-Discovery Reflex (MANDATORY, NEW 2026-04-26)

**Two questions before any action.** FB341 caught a regression where 8 of 12 SQL calls in one session were avoidable bypasses.

**Q1: Do I have a tool for this?**
- Check protocol injection (RELEVANT KNOWLEDGE, GOTCHAS, ENTITY CATALOG)
- Check `entity_read(query='...', entity_type='tool')`
- Check `recall_memories('how to do X')`
- Check the auto-loaded skills list
- Check `system_info()` for available MCP surfaces

**Q2: Do I know how to use it?**
- `entity_read('tool-name')` for usage signature
- `recall_memories('tool-name pattern')` for known gotchas
- If unclear, surface the gap (`store_session_fact` or file feedback)

**If the answer to either is "no"**: that's a discoverability gap. Either a tool is missing (file improvement feedback) or the discovery surface is failing (file design feedback). Don't silently fall back to raw SQL / direct file ops.

**Specific bypass to avoid** (per FB341):
- `mcp__postgres__execute_sql` against `claude.feedback`/`features`/`build_tasks` -> use `work_board()` / `get_ready_tasks()` / `work_status()` instead
- `mcp__postgres__execute_sql` against `claude.knowledge`/`entities` -> use `recall_memories()` / `entity_read()` / `memory_manage()`
- Reading `information_schema.columns` -> file FB345 (until `get_schema(table=…, mode='raw')` ships)

If you MUST use raw SQL (telemetry, mcp_usage, scheduled_jobs — currently no MCP wrapper), add an `-- OVERRIDE: <reason>` comment so the gap is visible to FB343/FB344.
"""


def main() -> int:
    conn = psycopg2.connect(get_database_uri())
    cur = conn.cursor()

    # Read current v7 (or higher) content for both scopes
    cur.execute("""
        SELECT scope, version, content
        FROM claude.rules
        WHERE name = 'storage-rules'
        ORDER BY scope
    """)
    rows = cur.fetchall()
    if not rows:
        print("ERROR: no storage-rules rows found", file=sys.stderr)
        return 1

    print(f"Found {len(rows)} storage-rules rows: {[(r[0], r[1]) for r in rows]}")

    for scope, current_version, current_content in rows:
        if "Memory-Update Discipline (Rule 7" in current_content:
            print(f"  scope={scope} v{current_version}: addendum already present, skipping")
            continue
        new_content = current_content.rstrip() + V8_ADDENDUM
        cur.execute("""
            UPDATE claude.rules
            SET content = %s,
                version = 8,
                updated_at = NOW()
            WHERE name = 'storage-rules'
              AND scope = %s
        """, (new_content, scope))
        print(f"  scope={scope}: updated {current_version} -> 8 ({len(new_content)} chars)")

    conn.commit()
    cur.close()
    conn.close()
    print("OK — v8 written. Now run: config_manage(action='deploy_project', components=['rules'])")
    return 0


if __name__ == "__main__":
    sys.exit(main())
