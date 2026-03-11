#!/usr/bin/env python3
"""
Work Context Container (WCC) Assembly Module

Provides activity detection and context assembly for the RAG hook.
Imported by rag_query_hook.py to keep hook code clean.

Activity detection: Scans each prompt for known activity names/aliases,
matching against claude.activities with trigram fuzzy matching.

Context assembly: When activity changes, queries 6 sources in parallel
with budget allocation, caches result for subsequent prompts.

State: Cached in ~/.claude/state/wcc_state.json between prompts.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger('rag_query.wcc')

# State file for WCC cache
STATE_DIR = Path.home() / ".claude" / "state"
WCC_STATE_FILE = STATE_DIR / "wcc_state.json"
WCC_CACHE_TTL_SECONDS = 300  # 5 minutes

# Budget allocation for 6 sources (percentages of total budget)
SOURCE_BUDGETS = {
    "workfiles": 0.25,
    "knowledge": 0.25,
    "features": 0.15,
    "session_facts": 0.10,
    "vault_rag": 0.15,
    "skills_bpmn": 0.10,
}

# Minimum similarity for activity matching
MIN_ACTIVITY_SIMILARITY = 0.6
# Minimum word overlap for name-based matching
MIN_WORD_MATCH = 2


# =========================================================================
# STATE MANAGEMENT
# =========================================================================

def load_wcc_state() -> Dict[str, Any]:
    """Load WCC state from file."""
    default_state = {
        "current_activity": None,
        "current_activity_id": None,
        "cached_wcc": None,
        "cached_at": None,
        "cache_invalidated": False,
    }
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if WCC_STATE_FILE.exists():
            with open(WCC_STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                return {**default_state, **state}
    except (json.JSONDecodeError, IOError):
        pass
    return default_state


def save_wcc_state(state: Dict[str, Any]):
    """Save WCC state to file."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(WCC_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except IOError:
        pass


def invalidate_wcc_cache():
    """Invalidate WCC cache (called when stash() or remember() fires)."""
    try:
        state = load_wcc_state()
        state["cache_invalidated"] = True
        save_wcc_state(state)
    except Exception:
        pass


def _is_cache_valid(state: Dict[str, Any]) -> bool:
    """Check if WCC cache is still valid (not expired, not invalidated)."""
    if state.get("cache_invalidated"):
        return False
    if not state.get("cached_wcc") or not state.get("cached_at"):
        return False
    try:
        cached_at = datetime.fromisoformat(state["cached_at"])
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        return age < WCC_CACHE_TTL_SECONDS
    except (ValueError, TypeError):
        return False


# =========================================================================
# ACTIVITY DETECTION
# =========================================================================

def detect_activity(
    prompt: str,
    project_name: str,
    conn,
    session_id: Optional[str] = None,
) -> Tuple[Optional[str], bool, Optional[str]]:
    """Detect which activity the user is working on from their prompt.

    Detection priority:
    1. Manual override via session_fact("current_activity")
    2. Exact name/alias match against claude.activities
    3. Trigram fuzzy match (similarity > 0.6)
    4. Fallback: match against workfile component names

    Args:
        prompt: User's current prompt text
        project_name: Current project name
        conn: Database connection (psycopg)
        session_id: Current session ID (for session_fact lookup)

    Returns:
        (activity_name, changed: bool, activity_id)
        - activity_name: detected activity or None
        - changed: True if different from cached activity
        - activity_id: UUID of matched activity or None
    """
    wcc_state = load_wcc_state()
    previous_activity = wcc_state.get("current_activity")

    # Priority 1: Manual override via session_fact
    manual_activity = _check_manual_override(conn, project_name, session_id)
    if manual_activity:
        changed = manual_activity != previous_activity
        activity_id = _lookup_activity_id(conn, project_name, manual_activity)
        return manual_activity, changed, activity_id

    # Priority 2+3: Match against activities table (exact + fuzzy)
    matched_name, matched_id = _match_activity_from_db(conn, project_name, prompt)
    if matched_name:
        changed = matched_name != previous_activity
        return matched_name, changed, matched_id

    # Priority 4: Fallback to workfile component names
    component_match = _match_workfile_component(conn, project_name, prompt)
    if component_match:
        changed = component_match != previous_activity
        # Auto-create activity from component match
        activity_id = _ensure_activity_exists(conn, project_name, component_match)
        return component_match, changed, activity_id

    # No activity detected — keep previous if any
    return previous_activity, False, wcc_state.get("current_activity_id")


def _check_manual_override(
    conn, project_name: str, session_id: Optional[str]
) -> Optional[str]:
    """Check if user has manually set current_activity via session_fact."""
    if not session_id:
        return None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT fact_value FROM claude.session_facts
            WHERE fact_key = 'current_activity'
              AND session_id = %s::uuid
            ORDER BY stored_at DESC LIMIT 1
        """, (session_id,))
        row = cur.fetchone()
        cur.close()
        if row:
            val = row['fact_value'] if isinstance(row, dict) else row[0]
            return val
    except Exception as e:
        logger.warning(f"Manual activity override check failed: {e}")
    return None


def _match_activity_from_db(
    conn, project_name: str, prompt: str
) -> Tuple[Optional[str], Optional[str]]:
    """Match prompt against activities table using name/alias + trigram.

    Returns (activity_name, activity_id) or (None, None).
    """
    try:
        cur = conn.cursor()
        # Get project_id
        cur.execute(
            "SELECT project_id FROM claude.projects WHERE project_name = %s",
            (project_name,)
        )
        proj = cur.fetchone()
        if not proj:
            cur.close()
            return None, None
        project_id = proj['project_id'] if isinstance(proj, dict) else proj[0]

        # Normalize prompt for matching
        prompt_lower = prompt.lower().strip()
        prompt_words = set(re.findall(r'\b\w{3,}\b', prompt_lower))

        # Get all active activities for this project
        cur.execute("""
            SELECT activity_id::text, name, aliases
            FROM claude.activities
            WHERE project_id = %s::uuid AND is_active = TRUE
        """, (project_id,))
        activities = cur.fetchall()
        cur.close()

        if not activities:
            return None, None

        best_match = None
        best_score = 0

        for row in activities:
            if isinstance(row, dict):
                act_id, name, aliases = row['activity_id'], row['name'], row.get('aliases', [])
            else:
                act_id, name, aliases = row[0], row[1], row[2] or []

            # Exact name match (case-insensitive)
            if name.lower() in prompt_lower:
                return name, act_id

            # Alias match
            for alias in (aliases or []):
                if alias.lower() in prompt_lower:
                    return name, act_id

            # Word overlap scoring
            name_words = set(re.findall(r'\b\w{3,}\b', name.lower()))
            overlap = len(prompt_words & name_words)
            if overlap >= MIN_WORD_MATCH and overlap > best_score:
                best_score = overlap
                best_match = (name, act_id)

        if best_match:
            return best_match

    except Exception as e:
        logger.warning(f"Activity DB match failed: {e}")

    return None, None


def _match_workfile_component(
    conn, project_name: str, prompt: str
) -> Optional[str]:
    """Fallback: match prompt against workfile component names."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT pw.component
            FROM claude.project_workfiles pw
            JOIN claude.projects p ON pw.project_id = p.project_id
            WHERE p.project_name = %s AND pw.is_active = TRUE
        """, (project_name,))
        rows = cur.fetchall()
        cur.close()

        prompt_lower = prompt.lower()
        for row in rows:
            comp = row['component'] if isinstance(row, dict) else row[0]
            if comp.lower() in prompt_lower:
                return comp
    except Exception as e:
        logger.warning(f"Workfile component match failed: {e}")
    return None


def _lookup_activity_id(
    conn, project_name: str, activity_name: str
) -> Optional[str]:
    """Look up activity_id by name."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.activity_id::text
            FROM claude.activities a
            JOIN claude.projects p ON a.project_id = p.project_id
            WHERE p.project_name = %s AND a.name = %s AND a.is_active = TRUE
        """, (project_name, activity_name))
        row = cur.fetchone()
        cur.close()
        if row:
            return row['activity_id'] if isinstance(row, dict) else row[0]
    except Exception:
        pass
    return None


def _ensure_activity_exists(
    conn, project_name: str, activity_name: str
) -> Optional[str]:
    """Create activity if it doesn't exist (auto-create from component match)."""
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.activities (project_id, name)
            SELECT p.project_id, %s
            FROM claude.projects p
            WHERE p.project_name = %s
            ON CONFLICT (project_id, name) DO UPDATE SET last_accessed_at = NOW()
            RETURNING activity_id::text
        """, (activity_name, project_name))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row:
            return row['activity_id'] if isinstance(row, dict) else row[0]
    except Exception as e:
        logger.warning(f"Activity auto-create failed: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    return None


# =========================================================================
# CONTEXT ASSEMBLY
# =========================================================================

def assemble_wcc(
    activity_name: str,
    activity_id: Optional[str],
    project_name: str,
    conn,
    session_id: Optional[str] = None,
    total_budget: int = 1500,
    generate_embedding_fn=None,
) -> Optional[str]:
    """Assemble Work Context Container from 6 sources.

    Queries all sources with proportional budget allocation, ranks by
    relevance, and returns formatted context string.

    Args:
        activity_name: Name of the detected activity
        activity_id: UUID of the activity (may be None)
        project_name: Current project name
        conn: Database connection
        session_id: Current session ID
        total_budget: Total token budget for assembled context
        generate_embedding_fn: Optional embedding function for similarity search

    Returns:
        Formatted context string or None if assembly fails
    """
    if not activity_name:
        return None

    start_time = time.time()
    sections = []

    # Update activity access stats
    if activity_id:
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE claude.activities
                SET last_accessed_at = NOW(), access_count = access_count + 1
                WHERE activity_id = %s::uuid
            """, (activity_id,))
            conn.commit()
            cur.close()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    # Get project_id
    project_id = _get_project_id(conn, project_name)
    if not project_id:
        return None

    # Query all 6 sources (sequential for simplicity in hook context)
    # Each source returns (label, content, token_estimate)

    # Source 1: Workfiles (25%)
    workfile_budget = int(total_budget * SOURCE_BUDGETS["workfiles"])
    workfiles_section = _query_workfiles(
        conn, project_id, activity_name, workfile_budget
    )
    if workfiles_section:
        sections.append(workfiles_section)

    # Source 2: Knowledge mid/long tier (25%)
    knowledge_budget = int(total_budget * SOURCE_BUDGETS["knowledge"])
    knowledge_section = _query_knowledge(
        conn, project_name, activity_name, knowledge_budget,
        generate_embedding_fn
    )
    if knowledge_section:
        sections.append(knowledge_section)

    # Source 3: Features/Tasks (15%)
    features_budget = int(total_budget * SOURCE_BUDGETS["features"])
    features_section = _query_features_tasks(
        conn, project_id, activity_name, features_budget
    )
    if features_section:
        sections.append(features_section)

    # Source 4: Session Facts (10%)
    facts_budget = int(total_budget * SOURCE_BUDGETS["session_facts"])
    facts_section = _query_session_facts(
        conn, project_name, session_id, activity_name, facts_budget
    )
    if facts_section:
        sections.append(facts_section)

    # Source 5: Vault RAG (15%) — only if embedding available
    vault_budget = int(total_budget * SOURCE_BUDGETS["vault_rag"])
    vault_section = _query_vault_for_activity(
        conn, activity_name, project_name, vault_budget,
        generate_embedding_fn
    )
    if vault_section:
        sections.append(vault_section)

    # Source 6: Skills/BPMN (10%)
    bpmn_budget = int(total_budget * SOURCE_BUDGETS["skills_bpmn"])
    bpmn_section = _query_skills_bpmn(
        conn, activity_name, bpmn_budget
    )
    if bpmn_section:
        sections.append(bpmn_section)

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(
        f"WCC assembly for '{activity_name}': {len(sections)} sources, "
        f"{elapsed_ms:.0f}ms"
    )

    if not sections:
        return None

    # Format as WCC block
    header = f"## Work Context: {activity_name}"
    body = "\n".join(sections)
    return f"{header}\n{body}"


def _get_project_id(conn, project_name: str) -> Optional[str]:
    """Get project_id from project_name."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT project_id::text FROM claude.projects WHERE project_name = %s",
            (project_name,)
        )
        row = cur.fetchone()
        cur.close()
        if row:
            return row['project_id'] if isinstance(row, dict) else row[0]
    except Exception:
        pass
    return None


def _truncate_to_budget(text: str, token_budget: int) -> str:
    """Truncate text to fit within approximate token budget (4 chars = 1 token)."""
    max_chars = token_budget * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit('\n', 1)[0] + "\n..."


# =========================================================================
# SOURCE QUERIES
# =========================================================================

def _query_workfiles(
    conn, project_id: str, activity_name: str, budget: int
) -> Optional[str]:
    """Query workfiles matching activity by component name or alias."""
    try:
        cur = conn.cursor()
        # Get aliases for the activity
        cur.execute("""
            SELECT aliases FROM claude.activities
            WHERE project_id = %s::uuid AND name = %s
        """, (project_id, activity_name))
        row = cur.fetchone()
        aliases = []
        if row:
            aliases = (row['aliases'] if isinstance(row, dict) else row[0]) or []

        # Query workfiles matching component name or aliases
        all_names = [activity_name] + aliases
        cur.execute("""
            SELECT title, content, workfile_type, updated_at
            FROM claude.project_workfiles
            WHERE project_id = %s::uuid
              AND component = ANY(%s)
              AND is_active = TRUE
            ORDER BY is_pinned DESC, updated_at DESC
            LIMIT 5
        """, (project_id, all_names))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return None

        parts = []
        for r in rows:
            if isinstance(r, dict):
                title, content = r['title'], r['content']
            else:
                title, content = r[0], r[1]
            # Truncate individual workfile content
            preview = content[:200] if content else ""
            parts.append(f"- **{title}**: {preview}")

        section = "### Workfiles\n" + "\n".join(parts)
        return _truncate_to_budget(section, budget)

    except Exception as e:
        logger.warning(f"WCC workfiles query failed: {e}")
        return None


def _query_knowledge(
    conn, project_name: str, activity_name: str, budget: int,
    generate_embedding_fn=None,
) -> Optional[str]:
    """Query mid/long tier knowledge related to activity."""
    try:
        cur = conn.cursor()

        # Try embedding-based search if available
        if generate_embedding_fn:
            embedding = generate_embedding_fn(activity_name)
            if embedding:
                cur.execute("""
                    SELECT title, description, knowledge_type,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM claude.knowledge
                    WHERE embedding IS NOT NULL
                      AND tier IN ('mid', 'long')
                      AND is_active = TRUE
                    ORDER BY embedding <=> %s::vector
                    LIMIT 5
                """, (embedding, embedding))
                rows = cur.fetchall()
                cur.close()

                if rows:
                    parts = []
                    for r in rows:
                        if isinstance(r, dict):
                            title, desc = r['title'], r['description']
                            sim = r['similarity']
                        else:
                            title, desc, _, sim = r[0], r[1], r[2], r[3]
                        if sim and sim >= 0.35:
                            preview = (desc or "")[:150]
                            parts.append(f"- [{r.get('knowledge_type', '') if isinstance(r, dict) else ''}] **{title}**: {preview}")
                    if parts:
                        section = "### Knowledge\n" + "\n".join(parts[:3])
                        return _truncate_to_budget(section, budget)

        # Fallback: keyword match
        cur = conn.cursor()
        cur.execute("""
            SELECT title, description, knowledge_type
            FROM claude.knowledge
            WHERE tier IN ('mid', 'long')
              AND is_active = TRUE
              AND (title ILIKE %s OR description ILIKE %s)
            ORDER BY confidence_level DESC
            LIMIT 3
        """, (f'%{activity_name}%', f'%{activity_name}%'))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return None

        parts = []
        for r in rows:
            if isinstance(r, dict):
                title, desc = r['title'], r['description']
            else:
                title, desc = r[0], r[1]
            preview = (desc or "")[:150]
            parts.append(f"- **{title}**: {preview}")

        section = "### Knowledge\n" + "\n".join(parts)
        return _truncate_to_budget(section, budget)

    except Exception as e:
        logger.warning(f"WCC knowledge query failed: {e}")
        return None


def _query_features_tasks(
    conn, project_id: str, activity_name: str, budget: int
) -> Optional[str]:
    """Query features/tasks matching activity name."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT f.short_code, f.feature_name, f.status,
                   (SELECT COUNT(*) FROM claude.build_tasks bt
                    WHERE bt.feature_id = f.feature_id AND bt.status = 'completed') AS done,
                   (SELECT COUNT(*) FROM claude.build_tasks bt
                    WHERE bt.feature_id = f.feature_id) AS total
            FROM claude.features f
            WHERE f.project_id = %s::uuid
              AND f.status IN ('planned', 'in_progress')
              AND (f.feature_name ILIKE %s OR f.description ILIKE %s)
            ORDER BY f.priority, f.created_at DESC
            LIMIT 3
        """, (project_id, f'%{activity_name}%', f'%{activity_name}%'))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return None

        parts = []
        for r in rows:
            if isinstance(r, dict):
                code, name, status = r['short_code'], r['feature_name'], r['status']
                done, total = r['done'], r['total']
            else:
                code, name, status, done, total = r[0], r[1], r[2], r[3], r[4]
            parts.append(f"- {code} {name} [{status}] ({done}/{total} tasks)")

        section = "### Features\n" + "\n".join(parts)
        return _truncate_to_budget(section, budget)

    except Exception as e:
        logger.warning(f"WCC features query failed: {e}")
        return None


def _query_session_facts(
    conn, project_name: str, session_id: Optional[str],
    activity_name: str, budget: int
) -> Optional[str]:
    """Query session facts with key pattern matching activity."""
    if not session_id:
        return None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT fact_key, fact_value, fact_type
            FROM claude.session_facts
            WHERE session_id = %s::uuid
              AND is_sensitive = FALSE
              AND (fact_key ILIKE %s OR fact_value ILIKE %s)
            ORDER BY stored_at DESC
            LIMIT 5
        """, (session_id, f'%{activity_name}%', f'%{activity_name}%'))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return None

        parts = []
        for r in rows:
            if isinstance(r, dict):
                key, val = r['fact_key'], r['fact_value']
            else:
                key, val = r[0], r[1]
            preview = (val or "")[:100]
            parts.append(f"- `{key}`: {preview}")

        section = "### Session Facts\n" + "\n".join(parts)
        return _truncate_to_budget(section, budget)

    except Exception as e:
        logger.warning(f"WCC session facts query failed: {e}")
        return None


def _query_vault_for_activity(
    conn, activity_name: str, project_name: str, budget: int,
    generate_embedding_fn=None,
) -> Optional[str]:
    """Query vault embeddings for activity-related documentation."""
    if not generate_embedding_fn:
        return None
    try:
        embedding = generate_embedding_fn(f"{activity_name} {project_name}")
        if not embedding:
            return None

        cur = conn.cursor()
        cur.execute("""
            SELECT title, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM claude.vault_embeddings
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT 3
        """, (embedding, embedding))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return None

        parts = []
        for r in rows:
            if isinstance(r, dict):
                title, content, sim = r['title'], r['content'], r['similarity']
            else:
                title, content, sim = r[0], r[1], r[2]
            if sim and sim >= 0.4:
                preview = (content or "")[:150]
                parts.append(f"- **{title}**: {preview}")

        if not parts:
            return None

        section = "### Vault Docs\n" + "\n".join(parts)
        return _truncate_to_budget(section, budget)

    except Exception as e:
        logger.warning(f"WCC vault query failed: {e}")
        return None


def _query_skills_bpmn(
    conn, activity_name: str, budget: int
) -> Optional[str]:
    """Query skills and BPMN processes matching activity."""
    try:
        cur = conn.cursor()
        # Search BPMN processes
        cur.execute("""
            SELECT process_id, process_name, level, description
            FROM claude.bpmn_processes
            WHERE process_name ILIKE %s OR description ILIKE %s
            LIMIT 3
        """, (f'%{activity_name}%', f'%{activity_name}%'))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return None

        parts = []
        for r in rows:
            if isinstance(r, dict):
                pid, pname = r['process_id'], r['process_name']
                level = r.get('level', '')
            else:
                pid, pname, level = r[0], r[1], r[2]
            parts.append(f"- [{level}] {pname} (`{pid}`)")

        section = "### Related Processes\n" + "\n".join(parts)
        return _truncate_to_budget(section, budget)

    except Exception as e:
        logger.warning(f"WCC BPMN query failed: {e}")
        return None


# =========================================================================
# PUBLIC API (called from rag_query_hook.py)
# =========================================================================

def get_wcc_context(
    prompt: str,
    project_name: str,
    conn,
    session_id: Optional[str] = None,
    total_budget: int = 1500,
    generate_embedding_fn=None,
) -> Tuple[Optional[str], Optional[str]]:
    """Main entry point: detect activity + return assembled WCC or cached.

    Args:
        prompt: User's current prompt
        project_name: Current project name
        conn: Database connection
        session_id: Current session ID
        total_budget: Token budget for WCC block
        generate_embedding_fn: Embedding function from rag_query_hook

    Returns:
        (wcc_context_string, activity_name)
        - wcc_context_string: Formatted WCC block for injection, or None
        - activity_name: Detected activity name, or None
    """
    try:
        # Detect activity
        activity_name, changed, activity_id = detect_activity(
            prompt, project_name, conn, session_id
        )

        if not activity_name:
            return None, None

        # Load state
        state = load_wcc_state()

        # Return cached if valid and activity unchanged
        if not changed and _is_cache_valid(state):
            logger.info(f"WCC cache hit for '{activity_name}'")
            return state.get("cached_wcc"), activity_name

        # Assemble fresh WCC
        logger.info(f"WCC assembling for '{activity_name}' (changed={changed})")
        wcc_text = assemble_wcc(
            activity_name=activity_name,
            activity_id=activity_id,
            project_name=project_name,
            conn=conn,
            session_id=session_id,
            total_budget=total_budget,
            generate_embedding_fn=generate_embedding_fn,
        )

        # Cache result
        state["current_activity"] = activity_name
        state["current_activity_id"] = activity_id
        state["cached_wcc"] = wcc_text
        state["cached_at"] = datetime.now(timezone.utc).isoformat()
        state["cache_invalidated"] = False
        save_wcc_state(state)

        return wcc_text, activity_name

    except Exception as e:
        logger.warning(f"WCC get_wcc_context failed: {e}")
        return None, None
