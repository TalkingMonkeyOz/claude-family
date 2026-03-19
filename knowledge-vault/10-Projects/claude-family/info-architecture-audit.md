---
projects:
- claude-family
tags:
- architecture
- audit
- information-design
---

# Information Architecture Audit

Audit of all injection layers in the Claude Family system: what each contains, when it fires, how much context it costs, and where it links for deeper detail.

## Layer Map (Injection Order)

| # | Layer | Scope | Injection Trigger | Est. Tokens | Mutable By |
|---|-------|-------|-------------------|-------------|------------|
| 1 | Core Protocol | All projects, all prompts | UserPromptSubmit hook | ~350 | `update_protocol()` (DB-versioned) |
| 2 | Global CLAUDE.md | All projects, session load | Claude Code boot | ~700 | Manual edit `~/.claude/CLAUDE.md` |
| 3 | Standards (`@` include) | All projects, session load | `@` directive in Global CLAUDE.md | ~400 | Manual edit `~/.claude/standards/` |
| 4 | Project CLAUDE.md | This project, session load | Claude Code boot | ~900 | `update_claude_md()` / manual |
| 5 | Rules (`.claude/rules/`) | This project, session load | Claude Code boot (all rules auto-loaded) | ~700 (8 files) | DB-backed, `deploy_project()` |
| 6 | Instructions | Pattern-matched files | PreToolUse (Write/Edit on matching globs) | ~100-400 each | DB-backed or manual |
| 7 | MEMORY.md | This project, session load | Claude Code boot (auto-memory) | ~2500 | Auto-written by Claude |
| 8 | RAG (vault + knowledge) | On-demand per prompt | UserPromptSubmit hook (semantic match) | 0-1500 (budget-capped) |  Vault docs + `remember()` |
| 9 | Periodic Reminders | Interval-based | UserPromptSubmit hook (every N interactions) | ~50-100 | Hook config in `rag_query_hook.py` |
| 10 | PreCompact injection | Before context compaction | PreCompact hook | ~500-2000 | Hook logic |
| 11 | Skills | On-demand (Skill tool) | User or Claude invokes `/skill-name` | ~500-2000 each | DB-backed, `deploy_project()` |
| 12 | Memory retrieval | On-demand (tool call) | `recall_memories()` / `recall_entities()` | ~500-1000 (budget param) | DB content |

**Total always-on cost (layers 1-7):** ~5,550 tokens at session start.
**Total per-prompt overhead (layers 1, 8-9):** ~400-1,950 tokens.

## Layer-by-Layer Analysis

### 1. Core Protocol (v18, ~350 tokens)

**Contains:** 7 mandatory behavioral rules (DECOMPOSE, verify, STORAGE, DELEGATE, OFFLOAD, BPMN-FIRST, CHECK TOOLS). The "constitution" -- non-negotiable operating rules.

**Injected:** Every single UserPromptSubmit via `rag_query_hook.py`. Read from `scripts/core_protocol.txt` (deployed from DB). Hardcoded fallback if file missing.

**Links to:** Storage-rules (rule 3), skills system (rule 7), BPMN processes (rule 6).

**Issues:**
- v18 in DB vs v11 referenced in MEMORY.md -- MEMORY.md is stale
- Fallback `DEFAULT_CORE_PROTOCOL` in hook code diverges from DB version (8 rules vs 7, different wording) -- maintenance risk
- ~350 tokens on EVERY prompt is significant but justified by behavioral impact

### 2. Global CLAUDE.md (~700 tokens)

**Contains:** Identity, environment (Windows/paths), vault structure, DB connection, work tracking hierarchy, MCP tool index, session workflow, skills list, delegation rules, structured autonomy, BPMN rules, SOPs, code style, auto-apply instructions list.

**Injected:** Session boot by Claude Code platform. Loaded once, persists in context.

**Links to:** Wiki-links (`[[Family Rules]]`, `[[Purpose]]`, etc.) for RAG discovery. References storage-rules, database-rules (auto-loaded). Points to `@~/.claude/standards/core/markdown-documentation.md` for inclusion.

**Issues:**
- **Heavy duplication with Project CLAUDE.md**: Tool index appears in both. Work tracking appears in both. Skills table appears in both. Session workflow appears in both. Config management appears in both.
- The `@` include of standards adds ~400 tokens that ALL projects pay for
- Wiki-links are a good indirection pattern but only work if RAG hook fires

### 3. Standards (markdown-documentation.md, ~400 tokens)

**Contains:** Chunking rules, folder structure, file naming, storage routing table, critical info positioning (Lost in the Middle), hook-enforced line limits, YAML frontmatter spec, linking conventions, footer requirements.

**Injected:** Via `@` directive in Global CLAUDE.md -- loaded at session boot as part of global context.

**Issues:**
- The "Where to Store What" table duplicates storage-rules.md almost verbatim
- Hook-enforced limits are "reference only" here but enforced by `standards_validator.py` -- good separation
- ~400 tokens for every project, even non-documentation work

### 4. Project CLAUDE.md (~900 tokens)

**Contains:** Project identity, config management (critical section), architecture overview, project structure, coding standards, work tracking (with tool tables), config tools, SOPs, key procedures (duplicated section), skills system, auto-apply instructions, knowledge system, recent changes.

**Injected:** Session boot by Claude Code platform.

**Issues:**
- **"Key Procedures" section is duplicated** (lines 160-165 and 167-172 are identical)
- Heavy overlap with Global CLAUDE.md: tool index, skills table, work tracking, session workflow
- Config management section is project-specific and valuable -- good placement
- Recent changes section is useful but manually maintained -- could drift

### 5. Rules (8 files, ~700 tokens total)

**Contains:** `database-rules` (schema, data gateway), `storage-rules` (5-system routing), `commit-rules` (message format, branch naming), `testing-rules` (when/how to test), `working-memory-rules` (session facts), `no-loose-ends` (deferred work tracking), `build-tracking-rules` (stream hierarchy), `system-change-process` (BPMN-first for system files).

**Injected:** All loaded at session boot by Claude Code (auto-loaded from `.claude/rules/`).

**Issues:**
- `storage-rules` content is triplicated: here, in standards, and in Core Protocol rule 3
- `working-memory-rules` is a subset of storage-rules -- could merge
- `system-change-process` is the most specific rule (~200 tokens) -- only relevant when editing hooks/workflows
- Rules are the right layer for project-specific enforcement, but some are universal (storage, commits)

### 6. Instructions (11 files, ~100-400 tokens each, conditional)

**Contains:** Language/framework-specific coding standards. Glob-matched: `**/*.sql`, `**/*.cs`, `**/*.tsx`, `**/*.md`, etc. Two new additions: `coding-ethos.instructions.md` (broad match: ts,tsx,py,cs,rs,sql) and `react-component-architecture.instructions.md` (ts,tsx).

**Injected:** On file pattern match via `context_injector_hook.py` (PreToolUse on Write/Edit).

**Issues:**
- `coding-ethos` matches 6 extensions -- fires on almost every code edit (~150 tokens each time)
- Only injected on Write/Edit, not on Read -- good, prevents unnecessary cost
- Total pool is ~2,500 tokens but only relevant ones fire -- efficient design

### 7. MEMORY.md (~2,500 tokens)

**Contains:** Accumulated session knowledge: core protocol docs, cognitive memory system details, workfiles system, context preservation, CLAUDE.md routing pattern, architecture rules, v2 application layer, hybrid task persistence, session lifecycle, hook scripts table, 20+ common gotchas, MCP server list, failure capture system.

**Injected:** Session boot by Claude Code (auto-memory file, always loaded).

**Issues:**
- **Largest single always-on layer at ~2,500 tokens** -- significant context cost
- Contains stale information (e.g., "Core Protocol v11" when DB is at v18, "40+ tools" when it's 60+)
- Heavy overlap with Project CLAUDE.md: hook scripts table, MCP servers, architecture rules
- "Common Gotchas" section (~800 tokens) is extremely valuable but bloats the file
- No pruning mechanism -- only grows. Should periodically archive resolved gotchas

### 8. RAG (vault + knowledge, 0-1500 tokens per prompt)

**Contains:** Semantically relevant vault documents and knowledge entries, retrieved via Voyage AI embeddings.

**Injected:** UserPromptSubmit hook. Hard-capped at `MAX_CONTEXT_TOKENS = 3000` (shared with core protocol, so RAG gets ~2,650 max). In practice, RAG results are much smaller.

**Issues:**
- Budget cap is well-designed -- prevents runaway injection
- RAG only fires when semantic similarity exceeds threshold -- efficient
- No visibility into what was injected (silent by design) -- debugging is hard

### 9. Periodic Reminders (~50-100 tokens when triggered)

**Contains:** Rotating nudges for inbox, vault refresh, git check, tool awareness, budget check, storage system reminders.

**Injected:** Every N interactions (8-25 depending on type) via UserPromptSubmit hook.

**Issues:**
- Lightweight and well-spaced -- minimal cost
- Storage nudges rotate through 5 variants -- good reinforcement without repetition

### 10. PreCompact Injection (~500-2000 tokens)

**Contains:** Active todos, features, build tasks, session facts, session notes. Preserves working state across context compaction.

**Injected:** PreCompact hook, budget-capped at `MAX_PRECOMPACT_TOKENS = 2000`.

**Issues:**
- Critical for session continuity -- well-designed
- Budget cap prevents overwhelming post-compact context

## Cross-Cutting Issues

### 1. Content Duplication (HIGH priority)

The same information appears in multiple layers:

| Topic | Appears In | Recommendation |
|-------|-----------|----------------|
| Storage routing (5 systems) | Core Protocol, Global CLAUDE.md, Standards, Storage-rules, Working-memory-rules | Keep in storage-rules only. Others should reference it. |
| Tool index | Global CLAUDE.md, Project CLAUDE.md | Keep in Global only. Project CLAUDE.md references "see Global". |
| Skills table | Global CLAUDE.md, Project CLAUDE.md | Keep in Global only. |
| Session workflow | Global CLAUDE.md, Project CLAUDE.md, MEMORY.md | Keep in Project CLAUDE.md (project-specific hooks). Global says "auto via hooks". |
| Hook scripts | Project CLAUDE.md, MEMORY.md | Keep in MEMORY.md (operational detail). Remove from CLAUDE.md. |
| MCP servers | Project CLAUDE.md, MEMORY.md | Keep in one place. MEMORY.md has more detail. |
| Config management | Project CLAUDE.md (good placement) | Keep -- project-specific and critical. |

**Estimated savings from dedup:** ~800-1,200 tokens off always-on cost.

### 2. Layer Purpose Confusion (MEDIUM priority)

The boundary between Global CLAUDE.md and Project CLAUDE.md is unclear. Both contain tool indexes, skills tables, and workflow descriptions. The intended split should be:

- **Global**: Identity, environment, universal rules, tool discovery, delegation
- **Project**: Project identity, architecture, config management, project-specific workflows, recent changes

### 3. MEMORY.md Growth (MEDIUM priority)

MEMORY.md has no pruning mechanism. It currently contains gotchas from October 2025 that may no longer apply. Recommendation: archive resolved gotchas quarterly, keep only active operational knowledge.

### 4. Stale Cross-References (LOW priority)

- MEMORY.md says "Core Protocol v11" -- DB is at v18
- MEMORY.md says "40+ tools" -- now 60+
- Global CLAUDE.md says "9 files" for instructions -- now 11

## Recommended Architecture

```
Layer 1: Core Protocol (~350 tok)     ← Behavioral rules. Every prompt.
Layer 2: Global CLAUDE.md (~500 tok)  ← Identity + environment + tool discovery. Deduped.
Layer 3: Standards (~400 tok)         ← Doc standards. Via @include.
Layer 4: Project CLAUDE.md (~600 tok) ← Project-specific. Config, architecture, recent changes.
Layer 5: Rules (~500 tok)             ← Merge working-memory into storage. Remove duplication.
Layer 6: MEMORY.md (~1,800 tok)       ← Prune stale gotchas. Archive quarterly.
Layer 7: Instructions (conditional)   ← No change needed. Good design.
Layer 8: RAG (on-demand, capped)      ← No change needed.
Layer 9: Skills (on-demand)           ← No change needed.
```

**Target always-on cost:** ~4,150 tokens (down from ~5,550 = 25% reduction).

## Action Items

1. **Dedup Global vs Project CLAUDE.md** -- remove tool index and skills from Project, keep in Global
2. **Merge working-memory-rules into storage-rules** -- eliminate the redundant file
3. **Prune MEMORY.md** -- archive pre-2026-03 gotchas, update stale version numbers
4. **Fix Project CLAUDE.md duplicate section** -- "Key Procedures" appears twice
5. **Align Core Protocol fallback** -- sync `DEFAULT_CORE_PROTOCOL` in hook with DB v18
6. **Reduce storage routing duplication** -- Core Protocol rule 3 says "see storage-rules.md", standards and Global CLAUDE.md should do the same instead of repeating the table

---
**Version**: 1.0
**Created**: 2026-03-19
**Updated**: 2026-03-19
**Location**: knowledge-vault/10-Projects/claude-family/info-architecture-audit.md
