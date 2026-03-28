 ---
  **Interactive Design Session for Project METIS**

  You are running an interactive design session with 1M token context. This
  replaces the Claude Desktop project-session-manager workflow with fewer
  limitations.

  ---

  ## Phase 1: Orient (4 steps max)

  **Step 1: Start session (MANDATORY)**
  start_session(project="project-metis")
  Returns: project context, previous session state, active todos, features,
  pending messages, recent decisions.

  **Step 2: Recall relevant context**
  recall_memories(query="METIS current state and recent design work",
  budget=1000)
  Use `query_type='task_specific'` if you know the focus,
  `query_type='exploration'` for broad orientation.

  **Step 3: Read the latest session handoff**
  Check `C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\ses
  sion-handoffs\` for the most recent file. Read ONLY that one.

  **Step 4: Confirm with the user**
  Summarise what you understand. Ask what they want to focus on today. Do NOT
  assume.

  ### Orient Anti-Patterns (still apply even with 1M context)
  - Do NOT `check_inbox(include_read=true)` — pulls all historical messages
  - Do NOT read multiple vault files "just in case"
  - Do NOT run web searches during orient — that's work phase

  ---

  ## Phase 2: Work (Interactive Brainstorm)

  ### The Core Pattern: One Topic At A Time

  This is a HARD RULE. For every design topic:

  1. **Present** — Introduce the topic, share what you know, propose options
  2. **Ask** — Ask the user a specific question. Wait for their answer
  3. **Capture** — When they decide, store it IMMEDIATELY:
     remember(content="", memory_type="decision", context="")
  4. **Move on** — Next topic

  Do NOT monologue a complete design and then ask for feedback. Present a piece,
   get input, capture, repeat.

  ### Incremental Saves (Still Important)

  Even with 1M context, decisions must be persisted to survive across sessions:

  | When this happens... | Do this immediately |
  |---------------------|-------------------|
  | A decision is made | `remember(content, memory_type="decision")` |
  | A key fact is established | `store_session_fact(key, value, type)` |
  | A section of design work is complete | Write the vault file NOW, not later |
  | You've finished a cluster of topics | `save_checkpoint(focus,
  progress_notes)` |
  | You learn something reusable | `remember(content, memory_type="learned")` |

  ### Tool Reference (Correct Names)

  | I need to... | Use this tool |
  |-------------|--------------|
  | Store a decision/learning/pattern for future sessions | `remember(content,
  memory_type, context)` |
  | Store a credential or key fact for this session |
  `store_session_fact(fact_key, fact_value, fact_type)` |
  | Recall a specific session fact by key | `recall_session_fact(key)` |
  | Search past knowledge | `recall_memories(query, budget)` |
  | Store structured reference data | `catalog(entity_type, properties)` |
  | Search cataloged entities | `recall_entities(query, entity_type)` |
  | Save component working notes | `stash(component, title, content)` |
  | Retrieve component working notes | `unstash(component)` |
  | Save progress checkpoint | `save_checkpoint(focus, progress_notes)` |
  | Start/finish tracked work | `start_work(task_code)` /
  `complete_work(task_code)` |
  | Get current work context | `get_work_context(scope)` |
  | Query the database (reads only) | `mcp__postgres__execute_sql` |
  | Search BPMN processes | `search_processes(query)` |

  ### Vault File Writing Rules

  When writing to the knowledge vault
  (`C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\`):

  - **One topic per file.** 5 sub-topics = 5 files + a README linking them
  - **~200 lines max per file.** If longer, split and link
  - **READMEs are indexes**, not encyclopedias — summaries + links to sub-files
  - **Wiki links liberally:** `[[folder/filename|Display Name]]`
  - **YAML frontmatter** on every file:
    ```yaml
    ---
    tags:
   - project/metis
   - scope/<area>
    created: YYYY-MM-DD
    updated: YYYY-MM-DD
    ---
  - Tell the user what you're writing before you write it

  DB vs Vault: What Goes Where

  ┌────────────────────────┬──────────────────────────┬────────────────────┐
  │        Content         │          Where           │        Why         │
  ├────────────────────────┼──────────────────────────┼────────────────────┤
  │ Status tracking        │ DB via remember(),       │ Queryable, small   │
  │ (features, decisions)  │ store_session_fact()     │ context cost       │
  ├────────────────────────┼──────────────────────────┼────────────────────┤
  │ Rich design content    │                          │ Human-readable,    │
  │ (architecture,         │ Vault (markdown files)   │ git-trackable      │
  │ brainstorms)           │                          │                    │
  ├────────────────────────┼──────────────────────────┼────────────────────┤
  │ Session state (facts,  │ DB via                   │ Key-value lookup   │
  │ checkpoints)           │ store_session_fact()     │                    │
  ├────────────────────────┼──────────────────────────┼────────────────────┤
  │ Cross-session          │ DB via remember()        │ Semantic search,   │
  │ knowledge              │                          │ auto-tiered        │
  ├────────────────────────┼──────────────────────────┼────────────────────┤
  │ Handoff for next       │ Vault                    │ Rich context       │
  │ session                │ (session-handoffs/)      │                    │
  └────────────────────────┴──────────────────────────┴────────────────────┘

  DB is source of truth for status. Vault is source of truth for content. If
  they diverge, DB wins.

  ---
  Phase 3: Hand Off (End of Session)

  When the user signals they're wrapping up:

  Step 1: End session (MANDATORY)
  end_session(summary="<what was accomplished>", next_steps=["<specific
  actions>"], tasks_completed=["<what got done>"], learnings=["<key insights>"])

  Step 2: Store key learnings
  remember(content="<learning>", memory_type="learned", context="<session
  context>")

  Step 3: Write session handoff (for substantial sessions)
  Write to knowledge-vault/10-Projects/Project-Metis/session-handoffs/YYYY-MM-DD
  -<description>.md
  Keep it SHORT: what was accomplished, decisions made, what's open, what next
  session should do first.

  Step 4: Verify checklist
  - All decisions stored via remember()?
  - Vault files updated for completed work?
  - Session ended with meaningful summary?
  - Handoff file written if session was substantial?

  ---
  1M Context Advantages (vs Desktop)

  - No aggressive rationing needed. You can read full vault files when needed
  - No checkpoint anxiety. Save for persistence, not survival
  - No multi-chat splitting. One session can cover an entire design area
  - Compaction is rare. But still save incrementally — decisions must survive
  across sessions
  - You'll be warned if context is getting large — save state then

  What Stays The Same

  - Interactive brainstorm pattern (one topic, one question, capture, move on)
  - Incremental vault writes (not batched to end)
  - Orient -> Work -> Hand Off lifecycle
  - DB for status, vault for content
  - remember() as primary persistence tool
  - User validates decisions — unvalidated content is draft, not decided

  ---
  13 Validated Decisions (Reference)

  These are CONSTRAINTS, not suggestions. All confirmed 2026-03-08:

  1. Build from zero (not Claude Family fork)
  2. Area-level features (F119-F128) as organising structure
  3. Augmentation Layer is core Phase 1
  4. Phase 2 is streams, not monolith
  5. Generic framing with nimbus as lead example
  6. Platform-agnostic infrastructure
  7. Separate DB per customer, no RLS
  8. Content-aware chunking per content type
  9. No keyword matching — embeddings only
  10. Single ranking pipeline with 6 signals
  11. Event-driven freshness, not time-based decay
  12. MVP = one stream working end-to-end
  13. Separate system blockers from customer blockers

  ---
