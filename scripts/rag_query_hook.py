#!/usr/bin/env python3
"""
RAG Query Hook for UserPromptSubmit

Automatically queries Voyage AI embeddings on every user prompt to inject
relevant vault knowledge into Claude's context.

FEATURES:
1. CORE PROTOCOL INJECTION - Always injects input processing protocol (~110 tokens)
2. KNOWLEDGE RECALL - Queries claude.knowledge for learned patterns/gotchas
3. VAULT RAG - Queries vault embeddings for documentation
4. SELF-LEARNING - Captures implicit feedback signals

This is SILENT - no visible output to user, just additionalContext injection.

Output Format:
{
    "additionalContext": "...",  # Injected into Claude's context
    "systemMessage": "",
    "environment": {}
}
"""

# =============================================================================
# CORE PROTOCOL - Injected on EVERY prompt (no semantic search required)
# =============================================================================
# Source of truth: claude.protocol_versions table (is_active=true)
# Deployed to: scripts/core_protocol.txt via deploy_project() or update_protocol()
# Fallback: hardcoded DEFAULT_CORE_PROTOCOL below (in case file is missing)

DEFAULT_CORE_PROTOCOL = """
STOP STOP STOP!!! do point 1 before anything ANYTHING else!!!!
1. DECOMPOSE: Read ALL of the user's message. Count every distinct request, question, and directive. Create a task (TaskCreate) for EACH ONE before acting on ANY of them. Include thinking/design tasks, not just code. NO TOOL CALLS until all tasks exist.
   TRAP: Do NOT latch onto the first interesting request and start working. You WILL forget the rest. Count first, task-create all, then start.
   SCOPE: Prefix every task with [S] (session) or [P] (persistent). Default [S] if unsure.
2. Verify before claiming - read files, query DB, do research. Never guess.
3. STORAGE: 5 systems, use the right one. See `storage-rules.md` (auto-loaded). `/skill-load-memory-storage` for detailed guide.
   - **Notepad** (store_session_fact) — credentials, decisions, findings. This session only.
   - **Memory** (remember) — patterns, gotchas, decisions for FUTURE sessions. Min 80 chars. NOT for task acks, progress, handoffs.
   - **Filing Cabinet** (stash) — component working papers across sessions. unstash() to reload.
   - **Reference Library** (catalog/recall_entities) — structured data (APIs, schemas, entities).
   - **Vault** — long-form docs, SOPs, research. Auto-searched via RAG.
4. DELEGATE: 3+ files = spawn agent. Agents MUST write results to session notes or files, return only 1-line summaries. Never let agent output flood your context. save_checkpoint() after each task.
5. OFFLOAD: After completing a task group, store_session_notes(findings, "progress") before moving on. Keep main context lean. Don't carry raw research/exploration forward.
6. BPMN-FIRST: For process/system changes - model in BPMN first, write tests, then code.
7. CHECK TOOLS: project-tools has 60+ tools. recall_memories() before complex tasks. Don't build what already exists.
"""


def _load_core_protocol():
    """Load CORE_PROTOCOL from deployed file, fall back to hardcoded default."""
    protocol_file = os.path.join(os.path.dirname(__file__), "core_protocol.txt")
    try:
        with open(protocol_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return content
    except (FileNotFoundError, IOError):
        pass
    return DEFAULT_CORE_PROTOCOL.strip()


# Loaded once per hook invocation (effectively per prompt)
CORE_PROTOCOL = None  # Lazy-loaded in _get_core_protocol()


def _get_core_protocol():
    global CORE_PROTOCOL
    if CORE_PROTOCOL is None:
        CORE_PROTOCOL = _load_core_protocol()
    return CORE_PROTOCOL

import json
import os
import sys
import time
import logging
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# =============================================================================
# CONTEXT BUDGET - Aggregate token ceiling for all injected blocks
# =============================================================================
# Without a ceiling, all 10+ blocks can fire simultaneously and approach
# 5,000-8,000 tokens per prompt, compounding with the core protocol.
# This constant is the hard cap for the combined additionalContext output.
# Individual block logic is unchanged — only the final assembly is guarded.
MAX_CONTEXT_TOKENS = 3000

# Setup file-based logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('rag_query')

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg

psycopg_mod, PSYCOPG_VERSION, _, _ = detect_psycopg()
DB_AVAILABLE = psycopg_mod is not None

# WCC (Work Context Container) assembly — imported lazily
_wcc_module = None  # Cached module reference

from rag_utils import generate_embedding, extract_query_from_prompt, expand_query_with_vocabulary, is_command, needs_rag, detect_explicit_negative
from rag_feedback import process_implicit_feedback
from rag_queries import (query_knowledge, query_knowledge_graph, query_critical_session_facts,
                         query_nimbus_context, needs_schema_search, query_schema_context,
                         query_vault_rag, query_skill_suggestions,
                         query_entity_catalog, query_workfiles)
from rag_context import (load_reminder_state, save_reminder_state, get_periodic_reminders,
                         _check_context_health, _check_recent_checkpoint,
                         detect_session_keywords, detect_config_keywords, get_session_context,
                         CONFIG_WARNING)


def _get_wcc_module():
    """Lazy-load wcc_assembly module."""
    global _wcc_module
    if _wcc_module is None:
        try:
            import wcc_assembly
            _wcc_module = wcc_assembly
        except ImportError:
            logger.warning("wcc_assembly module not found — WCC disabled")
    return _wcc_module


def _load_design_map(project_name: str) -> Optional[str]:
    """Load compressed design map if one exists for this project.

    Checks for a design-map.md file in the vault under the project's folder.
    Returns formatted context string or None if no map exists.
    Lightweight: pure file read, no DB or embedding queries.
    """
    vault_root = Path("C:/Projects/claude-family/knowledge-vault")

    # Check common locations for design map
    candidates = [
        vault_root / "10-Projects" / project_name / "design-map.md",
        vault_root / "10-Projects" / f"Project-{project_name.capitalize()}" / "design-map.md",
    ]

    for map_path in candidates:
        if map_path.exists():
            try:
                content = map_path.read_text(encoding="utf-8").strip()
                if not content or len(content) < 50:
                    continue
                # Strip YAML frontmatter if present
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end > 0:
                        content = content[end + 3:].strip()
                logger.info(f"Design map loaded: {map_path} ({len(content)} chars)")
                return f"[DESIGN MAP]\n{content}\n"
            except Exception as e:
                logger.warning(f"Failed to read design map {map_path}: {e}")
                continue

    return None


def _apply_context_budget(
    blocks: List[Tuple[int, str]],
    max_tokens: int = MAX_CONTEXT_TOKENS,
) -> str:
    """Apply a token budget to a prioritised list of context blocks.

    Budget system:
    - Blocks are passed as (priority, text) tuples. Lower priority number = higher importance.
    - Priority 0 blocks are ALWAYS included and never trimmed (core protocol, session facts,
      context health warnings).
    - Remaining blocks are included in ascending priority order until the budget is exhausted.
    - Token estimation uses the cheap heuristic: len(text) / 4.
    - Fail-open: if this function raises, the caller includes everything (current behaviour).

    Args:
        blocks: List of (priority, text) tuples. Text may be None or empty.
        max_tokens: Approximate token ceiling for the combined output.

    Returns:
        Combined context string, trimmed to fit within the budget.
    """
    # Separate pinned (priority 0) from trimmable blocks
    pinned = [text for (pri, text) in blocks if pri == 0 and text]
    trimmable = [(pri, text) for (pri, text) in blocks if pri > 0 and text]

    # Pinned blocks always go in; count their tokens
    result_parts = list(pinned)
    used_tokens = sum(len(t) // 4 for t in result_parts)

    # Add trimmable blocks in ascending priority order until budget exhausted
    included_count = len(result_parts)  # pinned blocks already included
    trimmed_count = 0
    for _pri, text in sorted(trimmable, key=lambda x: x[0]):
        block_tokens = len(text) // 4
        if used_tokens + block_tokens <= max_tokens:
            result_parts.append(text)
            used_tokens += block_tokens
            included_count += 1
        else:
            trimmed_count += 1
            logger.info(
                f"Context budget reached ({used_tokens} tokens used, limit={max_tokens}): "
                f"dropping block starting with: {text[:60]!r}"
            )

    logger.info(
        f"Context budget assembly: {included_count} blocks included ({len(pinned)} pinned + "
        f"{included_count - len(pinned)} trimmable), {trimmed_count} trimmed, "
        f"~{used_tokens} tokens used of {max_tokens} budget"
    )

    return "\n".join(result_parts)


def main():
    """Main hook entry point.

    Injects context into Claude's prompt based on what's needed:
    - ALWAYS: Core principles (~80 tokens) + session facts (~100 tokens)
    - CONDITIONAL: Session context (on session keywords), config warning (on config keywords)
    - ON-DEMAND: RAG + knowledge (only for questions/exploration, not actions)
    - RE-ENABLED: Skill suggestions (FB138 fix - was disabled, now injected for non-action prompts)
    - REMOVED: Periodic reminders (use hooks instead)
    """
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        # Extract user prompt from hook input
        # UserPromptSubmit hook provides the prompt in the hook_input
        user_prompt = hook_input.get('prompt', '')

        if not user_prompt:
            result = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": ""
                }
            }
            print(json.dumps(result))
            return

        # Skip ALL injection for short imperative commands (commit, yes, push)
        if is_command(user_prompt):
            logger.info(f"Skipping injection for command: {user_prompt[:50]}")
            result = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": _get_core_protocol()
                }
            }
            print(json.dumps(result))
            return

        # Get project context
        cwd = os.getcwd()
        project_name = os.path.basename(cwd)
        session_id = hook_input.get('session_id') or os.environ.get('CLAUDE_SESSION_ID')

        # TASK DISCIPLINE: Reset task map only when session changes.
        # FB141 fix: Previously reset on EVERY prompt, which wiped tasks created
        # earlier in the same turn (before Claude responded). Now only resets if
        # the session_id in the map doesn't match current session.
        try:
            task_map_path = Path(tempfile.gettempdir()) / f"claude_task_map_{project_name}.json"
            if task_map_path.exists():
                import json as _json
                try:
                    map_data = _json.loads(task_map_path.read_text(encoding='utf-8'))
                    map_session = map_data.get('_session_id', '')
                    current_sid = session_id or ''
                    # Only reset if session actually changed (not just new prompt)
                    if map_session and current_sid and map_session != current_sid:
                        task_map_path.unlink()
                        logger.info(f"Reset stale task map (old session: {map_session[:8]}, new: {current_sid[:8]})")
                    else:
                        logger.debug(f"Kept task map (same session: {map_session[:8] if map_session else 'none'})")
                except (json.JSONDecodeError, KeyError):
                    # Corrupt map file - delete it
                    task_map_path.unlink()
                    logger.info("Reset corrupt task map")
        except Exception as e:
            logger.warning(f"Failed to check task map: {e}")

        main_start = time.time()

        logger.info(f"RAG query hook invoked for project: {project_name}")
        logger.info(f"Query text (first 100 chars): {user_prompt[:100]}")

        # SELF-LEARNING: Check for implicit feedback signals BEFORE querying
        # This detects phrases like "that didn't work" or query rephrasing
        if DB_AVAILABLE and session_id:
            try:
                feedback_conn = get_db_connection()
                if feedback_conn:
                    process_implicit_feedback(feedback_conn, user_prompt, session_id)
                    feedback_conn.close()
            except Exception as e:
                logger.warning(f"Implicit feedback processing failed: {e}")

        # CRITICAL SESSION FACTS: Always inject (lightweight, no embedding)
        # These are credentials, endpoints, decisions - always visible to Claude
        critical_facts = query_critical_session_facts(
            project_name=project_name,
            session_id=session_id,
            limit=5
        )

        # SESSION CONTEXT: Removed (2026-02-10) - now served by get_work_context MCP tool
        # Use: ToolSearch("get_work_context") → get_work_context(scope="project")
        session_context = None

        # CONFIG WARNING: Detect if user is asking about config files
        # These files are database-generated and should not be manually edited
        config_warning = None
        if detect_config_keywords(user_prompt):
            logger.info("Config keywords detected - injecting config management warning")
            config_warning = CONFIG_WARNING

        # DESIGN MAP: Inject compressed design map if project has one
        # Lightweight file read (~500 tokens), gives instant design orientation
        # Kept serial — pure local file read, thread overhead > time saved
        design_map_context = None
        try:
            design_map_context = _load_design_map(project_name)
        except Exception as e:
            logger.warning(f"Design map loading failed: {e}")

        # WCC (WORK CONTEXT CONTAINER): Activity-based context assembly
        # Detects activity switch, assembles from 6 sources, caches between prompts.
        # When WCC is active, it REPLACES per-source knowledge/RAG/nimbus queries.
        wcc_context = None
        wcc_activity = None
        wcc_active = False
        if DB_AVAILABLE:
            try:
                wcc_mod = _get_wcc_module()
                if wcc_mod:
                    wcc_conn = get_db_connection()
                    if wcc_conn:
                        try:
                            wcc_context, wcc_activity = wcc_mod.get_wcc_context(
                                prompt=user_prompt,
                                project_name=project_name,
                                conn=wcc_conn,
                                session_id=session_id,
                                total_budget=1500,
                                generate_embedding_fn=generate_embedding,
                            )
                            wcc_active = wcc_context is not None
                            if wcc_active:
                                logger.info(f"WCC active for activity: {wcc_activity}")
                        finally:
                            wcc_conn.close()
            except Exception as e:
                logger.warning(f"WCC assembly failed (non-fatal): {e}")

        # CONDITIONAL: Only query RAG/knowledge for questions and exploration
        # Action prompts ("implement X", "fix Y") don't benefit from documentation retrieval
        # When WCC is active, skip per-source queries (WCC already assembled them)
        knowledge_context = None
        rag_context = None
        nimbus_context = None
        schema_context = None
        entity_context = None
        workfile_context = None

        # SKILL SUGGESTIONS: Re-enabled (FB138 fix)
        # Initialised here; populated in the parallel block (needs_rag path) or
        # the serial fallback below (non-RAG / WCC-active paths).
        skill_context = None

        if wcc_active:
            logger.info(f"WCC active — skipping per-source RAG/knowledge queries")
            # Skill suggestions still run serially when WCC is active
            if DB_AVAILABLE:
                try:
                    skill_context = query_skill_suggestions(
                        user_prompt=user_prompt,
                        project_name=project_name,
                        top_k=2,
                        min_similarity=0.55,
                    )
                except Exception as e:
                    logger.warning(f"Skill suggestion query failed: {e}")
        elif needs_rag(user_prompt):
            logger.info(f"RAG enabled for prompt: {user_prompt[:50]}")

            parallel_start = time.time()
            with ThreadPoolExecutor(max_workers=7) as executor:
                futures = {}

                # Submit all independent queries in parallel
                futures['knowledge'] = executor.submit(
                    query_knowledge_graph,
                    user_prompt=user_prompt,
                    project_name=project_name,
                    session_id=session_id,
                    max_initial_hits=3,
                    max_hops=2,
                    min_similarity=0.35,
                    token_budget=400,
                )
                futures['vault'] = executor.submit(
                    query_vault_rag,
                    user_prompt=user_prompt,
                    project_name=project_name,
                    session_id=session_id,
                    top_k=3,
                    min_similarity=0.45,
                )
                futures['nimbus'] = executor.submit(
                    query_nimbus_context,
                    user_prompt=user_prompt,
                    project_name=project_name,
                    top_k=3,
                )
                futures['skill'] = executor.submit(
                    query_skill_suggestions,
                    user_prompt=user_prompt,
                    project_name=project_name,
                    top_k=2,
                    min_similarity=0.55,
                )
                if needs_schema_search(user_prompt):
                    futures['schema'] = executor.submit(
                        query_schema_context,
                        user_prompt=user_prompt,
                        top_k=3,
                        min_similarity=0.40,
                    )
                futures['entities'] = executor.submit(
                    query_entity_catalog,
                    user_prompt=user_prompt,
                    project_name=project_name,
                    top_k=3,
                    min_similarity=0.45,
                )
                futures['workfiles'] = executor.submit(
                    query_workfiles,
                    user_prompt=user_prompt,
                    project_name=project_name,
                    top_k=2,
                    min_similarity=0.45,
                )

                # Collect results with timeout
                sources_with_results = []
                sources_empty = []
                for key, future in futures.items():
                    try:
                        result = future.result(timeout=8)
                        if key == 'knowledge':
                            knowledge_context = result
                        elif key == 'vault':
                            rag_context = result
                        elif key == 'nimbus':
                            nimbus_context = result
                        elif key == 'skill':
                            skill_context = result
                        elif key == 'schema':
                            schema_context = result
                        elif key == 'entities':
                            entity_context = result
                        elif key == 'workfiles':
                            workfile_context = result

                        if result:
                            sources_with_results.append(key)
                        else:
                            sources_empty.append(key)
                    except Exception as e:
                        logger.warning(f"Parallel query '{key}' failed: {e}")
                        sources_empty.append(key)

            parallel_ms = (time.time() - parallel_start) * 1000
            logger.info(
                f"Parallel RAG queries completed in {parallel_ms:.0f}ms: "
                f"{len(sources_with_results)}/{len(futures)} sources returned results "
                f"(active={sources_with_results}, empty={sources_empty})"
            )
        else:
            logger.info(f"RAG skipped for action prompt: {user_prompt[:50]}")
            # Skill suggestions still run for non-RAG prompts
            if DB_AVAILABLE:
                try:
                    skill_context = query_skill_suggestions(
                        user_prompt=user_prompt,
                        project_name=project_name,
                        top_k=2,
                        min_similarity=0.55,
                    )
                except Exception as e:
                    logger.warning(f"Skill suggestion query failed: {e}")

        # CONTEXT HEALTH: Check context window fullness (graduated urgency)
        # Uses StatusLine sensor data or prompt count fallback
        context_health_msg = None
        try:
            reminder_state = load_reminder_state()
            reminder_state["interaction_count"] = reminder_state.get("interaction_count", 0) + 1
            save_reminder_state(reminder_state)
            interaction_count = reminder_state["interaction_count"]

            ctx_level, ctx_remaining, ctx_msg = _check_context_health(interaction_count)
            if ctx_msg:
                context_health_msg = ctx_msg
                logger.info(f"Context health: level={ctx_level}, remaining={ctx_remaining}%")
        except Exception as e:
            logger.warning(f"Context health check failed: {e}")

        # PROCESS FAILURES: Surface pending auto-filed failures for self-improvement
        failure_context = None
        try:
            from failure_capture import get_pending_failures, format_pending_failures
            pending_failures = get_pending_failures(project_name, max_age_hours=48)
            failure_context = format_pending_failures(pending_failures)
        except Exception:
            pass  # Don't let failure surfacing break the hook

        # Assemble all context blocks as (priority, text) tuples, then apply
        # the aggregate token budget via _apply_context_budget().
        #
        # Priority 0 = pinned (always included, never trimmed):
        #   - Core protocol (task discipline — must always be seen)
        #   - Session facts (credentials/decisions — must always be visible)
        #   - Context health warnings (urgent directives — must always be seen)
        #
        # Priority 1-10 = trimmable (dropped lowest-priority-first when over budget):
        #   1. Process failures  (self-improvement loop — high urgency)
        #   2. WCC context       (activity-scoped assembled context — replaces 3-9 when active)
        #   3. Config warning    (conditional, but important when triggered)
        #   4. Knowledge graph   (high-value learned patterns)
        #   5. Entity catalog    (structured reference data — APIs, schemas, domain concepts)
        #   6. Vault RAG         (documentation retrieval)
        #   7. Workfiles         (component working context from prior sessions)
        #   8. Skill suggestions (discovery aid)
        #   9. Schema context    (table/column context)
        #  10. Design map        (project orientation)
        #  11. Nimbus context    (project-specific, narrow audience)
        #
        # When WCC is active, blocks 4-11 are None (WCC already contains their data).
        #
        # Fail-open: if _apply_context_budget() errors, the except block below
        # falls back to joining all non-None parts (previous behaviour).
        budget_blocks: List[Tuple[int, str]] = [
            (0, _get_core_protocol()),
            (0, critical_facts or ""),
            (0, context_health_msg or ""),
            (1, failure_context or ""),
            (2, wcc_context or ""),
            (3, config_warning or ""),
            (4, knowledge_context or ""),
            (5, entity_context or ""),
            (6, rag_context or ""),
            (7, workfile_context or ""),
            (8, skill_context or ""),
            (9, schema_context or ""),
            (10, design_map_context or ""),
            (11, nimbus_context or ""),
        ]

        try:
            combined_context = _apply_context_budget(budget_blocks, MAX_CONTEXT_TOKENS)
        except Exception as budget_err:
            logger.warning(f"Context budget guard failed, including all blocks: {budget_err}")
            # Fail-open: include everything (original behaviour)
            combined_context = "\n".join(
                text for (_pri, text) in budget_blocks if text
            )

        total_ms = (time.time() - main_start) * 1000
        logger.info(f"RAG hook total execution: {total_ms:.0f}ms")

        # Build result (CORRECT format per Claude Code docs)
        result = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": combined_context
            }
        }

        # Output JSON to stdout (SILENT - no user-visible messages)
        print(json.dumps(result))

    except Exception as e:
        logger.error(f"RAG hook failed: {e}", exc_info=True)
        # Auto-file failure for process improvement loop
        try:
            from failure_capture import capture_failure
            capture_failure("rag_query_hook", str(e), "scripts/rag_query_hook.py")
        except Exception:
            pass
        # On error, return empty context (don't break the flow)
        result = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ""
            }
        }
        print(json.dumps(result))


if __name__ == "__main__":
    main()
