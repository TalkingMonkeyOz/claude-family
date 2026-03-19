---
projects:
- claude-family
- project-metis
tags:
- research
- implementation-audit
- cognitive-memory
synced: false
---

# Implementation Audit: Cognitive Memory Tools

Back to: [index](impl-audit-index.md)

**Source files:**
- `mcp-servers/project-tools/server.py` — tool implementations
- `mcp-servers/project-tools/server_v2.py` — MCP wrapper (re-exports from server.py)

`server_v2.py:3218` imports all tool functions from `server.py`. The v2 file is the
active MCP server; server.py is the implementation library.

---

## remember() — server.py:1791

**Tier routing (lines 1807-1819):** Simple lookup against hardcoded type sets:

```
short: credential, config, endpoint
mid:   learned, fact, decision, note, data
long:  pattern, procedure, gotcha, preference
```

`tier_hint` overrides routing verbatim — passing `"medium"` silently routes to mid
(falls through to `else: tier = "mid"`). No validation.

**Short path (lines 1821-1849):** Delegates to `tool_store_session_fact`. The fact_key
is the first line of content, stripped of special chars, max 30 chars. A credential
starting with a URL produces a mangled key like `https_api_example_com`. Gap: fragile
key derivation for structured content.

**Dedup check (lines 1867-1907):** pgvector cosine similarity, threshold 0.85, same
tier only. On match, merges by taking the longer description and boosting confidence
by 5 points. Gap: cross-tier dedup does not happen — a nearly identical entry in
a different tier will not be detected.

**Contradiction detection (lines 1909-1926):** Finds entries with similarity > 0.75.
If new entry is tier=mid and any match has confidence >= 80, sets contradiction_flag.
The entry is still inserted — the flag is advisory only. Gap: only fires for new
mid-tier entries; a contradicting new long-tier entry is not flagged.

**Auto-linking (lines 1963-1984):** Finds entries with similarity 0.5-0.85 (below
merge threshold). Creates `relates_to` relations for up to 3 entries. All auto-links
use `relates_to` regardless of the contradiction flag — a contradiction still gets
`relates_to`, not `contradicts`.

**Works well:** Merge-or-create with embedding dedup is solid. Automatic `relates_to`
linking creates useful graph connections without Claude effort.

**Fragile:** Short-path key derivation; no cross-tier dedup; contradiction detection
is advisory and inconsistent.

---

## recall_memories() — server.py:1548

**Budget profiles (lines 1563-1569):**

```
task_specific: short=40%, mid=40%, long=20%
exploration:   short=10%, mid=30%, long=60%
default:       short=20%, mid=40%, long=40%
```

Applied to the `budget` parameter (default 1000 tokens).

**Short tier (lines 1583-1628):** No embedding — pure recency + type ordering
(decision > reference > note > config > endpoint > data). Fetches up to 20 rows.
Gap: no relevance signal. A credential stored hours ago appears before a decision
stored minutes ago if ordered by type. Budget allocation is fixed — if 0 short facts
exist, that 20% is wasted.

**Mid tier (lines 1630-1672):** pgvector similarity >= 0.4. Composite score:
```
score = sim*0.4 + recency*0.3 + access_freq*0.2 + conf*0.1
```
Recency decays over 90 days. Access frequency capped at 1.0 (10+ uses).

**Long tier (lines 1674-1753):** Same formula, lower similarity threshold (0.35),
recency decay over 180 days. After initial vector search, a 1-hop graph walk finds
related entries via `knowledge_relations` with strength >= 0.3. Graph-discovered
entries get a fixed score of 0.3 (line 1749). Gap: fixed score means graph entries
always rank below direct matches regardless of relevance. Depth-2 nodes are never
retrieved.

**Access tracking (lines 1755-1763):** Updates `last_accessed_at` and increments
`access_count` for returned mid/long entries. Short-tier facts do not get updates.

**Works well:** 3-tier retrieval in one call is genuinely useful. Composite scoring
is thoughtful. Graph walk adds connectivity value.

**Fragile:** Short tier has no relevance signal. Fixed budget splits waste allocation
when a tier has no matching entries. Graph entries get an arbitrary score of 0.3.

---

## consolidate_memories() — server.py:2008

**Phase 1 — SHORT → MID (lines 2034-2096):** Promotes session facts from closed
sessions (within 7 days) with type in `{decision, reference, note, data}` and
length >= 50 chars. Inserts into `claude.knowledge` as tier=mid, confidence=65.

Gap 1: `s.session_end IS NOT NULL` filter excludes the current session. A manual
call during a session promotes nothing.

Gap 2: `endpoint` type is excluded from promotion but is often worth keeping.

**Phase 2 — MID → LONG (lines 2098-2111):**
```sql
WHERE tier='mid' AND times_applied >= 3 AND confidence_level >= 80 AND access_count >= 5
```
Strict criteria — a fact accessed 4 times at confidence 79 never promotes.

**Duplicate implementation:** `session_startup_hook_enhanced.py:283-321` runs
the same SQL directly rather than calling `tool_consolidate_memories`. If thresholds
change in one place, they diverge.

**Phase 3 — DECAY + ARCHIVE (lines 2113-2136):** Edge decay applies `0.95^days`
formula. Gap: decay uses `created_at`, not `last_accessed_at`. An edge traversed
yesterday but created 30 days ago is heavily decayed.

Archive: `confidence < 30 AND not accessed in 90+ days`. Conservative and appropriate.
No process to un-archive entries that become relevant again.

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/impl-audit-cognitive-memory.md
