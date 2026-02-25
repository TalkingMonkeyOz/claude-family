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
STOP!
1. DECOMPOSE: Read all of the user input and break it down. Create a task (TaskCreate) for EVERY distinct directive BEFORE acting on ANY of them. Include thinking/design tasks, not just code. No tool calls until all tasks exist.
2. Verify before claiming - read files, query DB. Never guess.
3. NOTEPAD: Use store_session_fact() to save credentials, decisions, endpoints, findings, progress. These survive compaction. Use list_session_facts() to review. recall_session_fact() works across sessions. This is your memory.
4. BPMN-FIRST: For any process or system change - model it in BPMN first, write tests, then implement code. Never code without a model.
5. DELEGATE: Tasks touching 3+ files = spawn an agent (coder-sonnet for complex, coder-haiku for simple). Don't bloat the main context. save_checkpoint() after completing each task.
6. Check MCP tools first - project-tools has 40+ tools. They have descriptions, use them!
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
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# =============================================================================
# PERIODIC REMINDERS - Interval-based context injection
# =============================================================================
# Merged from stop_hook_enforcer.py - single injection point for all context.
# Reminders are injected at intervals to prevent context drift.

REMINDER_INTERVALS = {
    "inbox_check": 15,       # Every 15 interactions - check for messages
    "vault_refresh": 25,     # Every 25 interactions - refresh vault understanding
    "git_check": 10,         # Every 10 interactions - check uncommitted changes
    "tool_awareness": 8,     # Every 8 interactions - remind about MCP tools
    "budget_check": 12,      # Every 12 interactions - context budget awareness
}

# State file for tracking interaction count
STATE_DIR = Path.home() / ".claude" / "state"
STATE_FILE = STATE_DIR / "rag_hook_state.json"


def load_reminder_state() -> Dict[str, Any]:
    """Load reminder state from file."""
    default_state = {
        "interaction_count": 0,
        "last_inbox_check": 0,
        "last_vault_refresh": 0,
        "last_git_check": 0,
        "last_tool_awareness": 0,
        "session_start": datetime.now(timezone.utc).isoformat(),
    }
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                return {**default_state, **state}
    except (json.JSONDecodeError, IOError):
        pass
    return default_state


def save_reminder_state(state: Dict[str, Any]):
    """Save reminder state to file."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state["last_interaction"] = datetime.now(timezone.utc).isoformat()
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except IOError:
        pass  # Silent fail - don't break the hook


def get_periodic_reminders(state: Dict[str, Any]) -> Optional[str]:
    """Generate periodic reminders based on interaction count.

    Returns formatted reminder string or None if no reminders due.
    """
    count = state.get("interaction_count", 0)
    reminders = []

    # Check each interval
    if count > 0 and count % REMINDER_INTERVALS["inbox_check"] == 0:
        if count != state.get("last_inbox_check", 0):
            reminders.append("📬 **Inbox Check**: Use `mcp__orchestrator__check_inbox` to see pending messages")
            state["last_inbox_check"] = count

    if count > 0 and count % REMINDER_INTERVALS["vault_refresh"] == 0:
        if count != state.get("last_vault_refresh", 0):
            reminders.append("📚 **Vault Refresh**: Re-read CLAUDE.md if unsure about project conventions")
            state["last_vault_refresh"] = count

    if count > 0 and count % REMINDER_INTERVALS["git_check"] == 0:
        if count != state.get("last_git_check", 0):
            reminders.append("🔀 **Git Check**: Run `git status` to check for uncommitted changes")
            state["last_git_check"] = count

    if count > 0 and count % REMINDER_INTERVALS["tool_awareness"] == 0:
        if count != state.get("last_tool_awareness", 0):
            reminders.append("""🔧 **When to use MCP tools** (ToolSearch first):
  - **User reports bug/idea?** → `project-tools.create_feedback` (NOT raw SQL)
  - **Planning 3+ file feature?** → `project-tools.create_feature` + `add_build_task`
  - **Task too complex for me?** → `orchestrator.spawn_agent` (delegate to coder/analyst)
  - **Need deep reasoning?** → `sequential-thinking` for multi-step analysis
  - **Processing Excel/CSV?** → `python-repl` (keep data in REPL, not context)
  - **Learned something useful?** → `project-tools.store_knowledge` (persists for future)""")
            state["last_tool_awareness"] = count

    if count > 0 and count % REMINDER_INTERVALS["budget_check"] == 0:
        if count != state.get("last_budget_check", 0):
            reminders.append("""**CONTEXT BUDGET CHECK** (interaction #{count}):
  - Heavy tasks (BPMN, large files, multi-file refactor): ~800 tokens each
  - Medium tasks (single edit, test writing): ~400 tokens each
  - Light tasks (query, status, git): ~100 tokens each
  - **3+ heavy tasks remaining?** DELEGATE to agents (spawn_agent)
  - **Run save_checkpoint()** after each completed task to preserve progress
  - **Over budget?** Stop, save state, let next session continue""".format(count=count))
            state["last_budget_check"] = count

    if reminders:
        return "\n## Periodic Reminders (Interaction #{})\n{}".format(
            count,
            "\n".join(f"- {r}" for r in reminders)
        )
    return None

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

# Voyage AI is lazy-loaded in generate_embedding() to save ~100ms startup time
# Only imported when embeddings are actually needed
VOYAGE_AVAILABLE = None  # Will be set on first use
_voyageai_module = None  # Cached module reference


def generate_embedding(text: str) -> list:
    """Generate embedding using Voyage AI API.

    Lazy-loads voyageai module on first call to save ~100ms startup time
    when embeddings aren't needed (commands, simple questions).
    """
    global VOYAGE_AVAILABLE, _voyageai_module

    # Lazy load voyageai on first use
    if VOYAGE_AVAILABLE is None:
        try:
            import voyageai
            _voyageai_module = voyageai
            VOYAGE_AVAILABLE = True
            logger.info("Lazy-loaded voyageai module")
        except ImportError:
            VOYAGE_AVAILABLE = False
            logger.warning("voyageai not installed - embeddings unavailable")

    if not VOYAGE_AVAILABLE:
        return None

    try:
        api_key = os.environ.get('VOYAGE_API_KEY')
        if not api_key:
            logger.warning("VOYAGE_API_KEY not set - skipping RAG")
            return None

        client = _voyageai_module.Client(api_key=api_key)
        result = client.embed([text], model="voyage-3", input_type="query")
        return result.embeddings[0]
    except Exception as e:
        logger.warning(f"Failed to generate embedding: {e}")
        return None


def extract_query_from_prompt(user_prompt: str) -> str:
    """Extract meaningful query from user prompt.

    For now, just use the prompt as-is. Could add keyword extraction later.
    """
    # Truncate very long prompts (Voyage AI has token limits)
    max_length = 500
    if len(user_prompt) > max_length:
        return user_prompt[:max_length]
    return user_prompt


def expand_query_with_vocabulary(conn, query_text: str) -> str:
    """Expand query using learned vocabulary mappings.

    This improves RAG retrieval by translating user's vocabulary
    (e.g., "spin up") into canonical concepts (e.g., "create").

    Args:
        conn: Database connection
        query_text: Original query text

    Returns:
        Expanded query with canonical concepts appended
    """
    if not conn:
        return query_text

    try:
        cur = conn.cursor()

        # Find matching vocabulary mappings
        # Use ILIKE for case-insensitive matching
        cur.execute("""
            SELECT user_phrase, canonical_concept, context_keywords
            FROM claude.vocabulary_mappings
            WHERE active = true
              AND %s ILIKE '%%' || user_phrase || '%%'
            ORDER BY confidence DESC, times_seen DESC
            LIMIT 5
        """, (query_text,))

        mappings = cur.fetchall()

        if not mappings:
            logger.debug(f"No vocabulary mappings found for: {query_text[:50]}")
            return query_text

        # Build expansion terms
        expansion_terms = []
        matched_phrases = []

        for m in mappings:
            if isinstance(m, dict):
                phrase = m['user_phrase']
                concept = m['canonical_concept']
                keywords = m.get('context_keywords', []) or []
            else:
                phrase = m[0]
                concept = m[1]
                keywords = m[2] or []

            matched_phrases.append(phrase)
            expansion_terms.append(concept)
            if keywords:
                expansion_terms.extend(keywords[:3])  # Limit keywords per mapping

        if expansion_terms:
            # Deduplicate while preserving order
            seen = set()
            unique_terms = []
            for term in expansion_terms:
                if term.lower() not in seen:
                    seen.add(term.lower())
                    unique_terms.append(term)

            expanded = f"{query_text} {' '.join(unique_terms)}"
            logger.info(f"Vocabulary expansion: matched [{', '.join(matched_phrases)}] -> added [{', '.join(unique_terms)}]")
            return expanded

        return query_text

    except Exception as e:
        logger.warning(f"Vocabulary expansion failed: {e}")
        return query_text


# ============================================================================
# SELF-LEARNING: Implicit Feedback Detection
# ============================================================================

NEGATIVE_PHRASES = [
    "that didn't work",
    "that's not what i",
    "wrong doc",
    "not helpful",
    "ignore that",
    "that's irrelevant",
    "that's old",
    "that's outdated",
    "that's stale",
    "wrong file",
    "not what i asked",
    "that's not it",
]

# Session context keywords - trigger session handoff context injection
SESSION_KEYWORDS = [
    "where was i",
    "where were we",
    "what was i working on",
    "what were we working on",
    "what's next",
    "whats next",
    "next steps",
    "resume",
    "continue from",
    "last session",
    "previous session",
    "pick up where",
    "what todos",
    "my todos",
    "active todos",
    "pending tasks",
    "what should i do",
    "what should we do",
    "session context",
    "session resume",
    "/session-resume",
]

# Keywords that should trigger config management warning
# These patterns indicate Claude might be about to edit config files
CONFIG_KEYWORDS = [
    "settings.local.json",
    "settings.json",
    ".claude/settings",
    "hooks.json",
    "edit config",
    "change config",
    "modify config",
    "update config",
    "fix hooks",
    "change hooks",
    "add hook",
    "remove hook",
]

CONFIG_WARNING = """
⚠️ **CONFIG WARNING**: `.claude/settings.local.json` is **database-generated**.

**DO NOT manually edit** - changes will be overwritten on next SessionStart.

**To change permanently:**
1. Update database: `config_templates` (all projects) or `workspaces.startup_config` (one project)
2. Regenerate: `python scripts/generate_project_settings.py <project>` (from project dir)
3. Restart Claude Code

See: `knowledge-vault/40-Procedures/Config Management SOP.md`
"""

# Command patterns - skip RAG for imperative commands (not questions)
# These must match SHORT commands only - not long prompts that happen to start with these words
COMMAND_PATTERNS = [
    # Short git/dev commands (must be short - under 50 chars)
    r'^(commit|push|pull)\s*[a-zA-Z0-9\s\-]*$',
    # Simple affirmations - ONLY if the entire prompt is short (<=30 chars)
    # This avoids skipping "ok lets build the tool and also create a document"
    r'^(yes|no|ok|sure|fine|continue|proceed|go ahead|do it)[\s\.,!]*$',
    # Short action verbs - only if prompt is very short
    r'^(save|close|restart|refresh|reload)[\s\w]*$',
]

# Minimum prompt length to always process (chars) - longer prompts always get RAG
MIN_COMMAND_SKIP_LENGTH = 30

def is_command(prompt: str) -> bool:
    """Detect if prompt is a short imperative command.

    Returns True for commands like 'commit changes', 'yes do it', etc.
    These skip ALL injection (no core protocol, no RAG).
    """
    prompt_lower = prompt.lower().strip()

    if len(prompt_lower) > MIN_COMMAND_SKIP_LENGTH:
        return False

    if '?' in prompt or any(w in prompt_lower for w in ['how', 'what', 'where', 'why', 'when', 'which', 'can you', 'could you']):
        return False

    for pattern in COMMAND_PATTERNS:
        if re.match(pattern, prompt_lower):
            return True
    return False


# Patterns that indicate the prompt is a question or exploration (benefits from RAG)
QUESTION_INDICATORS = [
    '?',           # Direct questions
    'how do',      # How-to questions
    'how to',
    'what is',     # Definitional
    'what are',
    'where is',    # Location questions
    'where are',
    'why does',    # Reasoning questions
    'why is',
    'explain',     # Requests for explanation
    'describe',
    'what does',
    'show me',
    'tell me about',
    'help me understand',
    'documentation',
    'guide',
    'tutorial',
    'example of',
    'best practice',
    'pattern for',
    'how should',
]

# Patterns that indicate an action/instruction (skip RAG)
ACTION_INDICATORS = [
    'implement',   # Direct action requests
    'create',
    'build',
    'fix',
    'update',
    'change',
    'add',
    'remove',
    'delete',
    'move',
    'rename',
    'refactor',
    'deploy',
    'run',
    'test',
    'commit',
    'push',
    'merge',
    'let\'s',      # Collaborative action
    'go ahead',
    'do it',
    'start',
    'continue',
    'pick up',
    'yes',
    'no',
    'ok',
    'sure',
]


def needs_rag(prompt: str) -> bool:
    """Determine if a prompt benefits from RAG knowledge retrieval.

    Returns True for questions, exploration, "how do I" prompts.
    Returns False for action instructions, commands, corrections.

    This is the key gate that prevents ~70% of unnecessary RAG queries.
    """
    prompt_lower = prompt.lower().strip()

    # Very short prompts never need RAG
    if len(prompt_lower) < 15:
        return False

    # Explicit questions always get RAG
    for indicator in QUESTION_INDICATORS:
        if indicator in prompt_lower:
            return True

    # Check if prompt starts with an action verb
    first_word = prompt_lower.split()[0] if prompt_lower.split() else ''
    for indicator in ACTION_INDICATORS:
        if first_word == indicator or prompt_lower.startswith(indicator):
            return False

    # Slash commands don't need RAG (they load their own context)
    if prompt_lower.startswith('/'):
        return False

    # Default: if prompt is long enough, it might benefit from RAG
    # But raise the bar - only if it's >100 chars (substantial question)
    return len(prompt_lower) > 100


def detect_explicit_negative(user_prompt: str) -> Optional[Tuple[str, float]]:
    """Detect explicit negative feedback in user prompt.

    Returns: (signal_type, confidence) or None
    """
    prompt_lower = user_prompt.lower()
    for phrase in NEGATIVE_PHRASES:
        if phrase in prompt_lower:
            logger.info(f"Detected explicit negative: '{phrase}'")
            return ('explicit_negative', 0.9)
    return None


def get_recent_rag_queries(conn, session_id: str, limit: int = 3) -> List[dict]:
    """Get recent RAG queries from this session for rephrase detection."""
    if not session_id:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT log_id, query_text, docs_returned, top_similarity, created_at
            FROM claude.rag_usage_log
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (session_id, limit))

        results = cur.fetchall()
        if isinstance(results[0] if results else {}, dict):
            return results
        else:
            # Convert tuple to dict for psycopg2
            return [
                {'log_id': r[0], 'query_text': r[1], 'docs_returned': r[2],
                 'top_similarity': r[3], 'created_at': r[4]}
                for r in results
            ]
    except Exception as e:
        logger.warning(f"Failed to get recent queries: {e}")
        return []


def calculate_query_similarity(query1: str, query2: str) -> float:
    """Simple word overlap similarity between two queries.

    Returns: similarity score 0-1
    """
    words1 = set(re.findall(r'\w+', query1.lower()))
    words2 = set(re.findall(r'\w+', query2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def detect_query_rephrase(current_query: str, recent_queries: List[dict],
                          threshold: float = 0.30) -> Optional[Tuple[str, float, dict]]:
    """Detect if current query is a rephrase of a recent query.

    Returns: (signal_type, confidence, original_query_dict) or None
    """
    for prev in recent_queries:
        prev_text = prev.get('query_text', '')
        similarity = calculate_query_similarity(current_query, prev_text)
        logger.debug(f"Rephrase check: '{current_query[:30]}' vs '{prev_text[:30]}' = {similarity:.2f}")

        if similarity >= threshold:
            logger.info(f"Detected rephrase (similarity={similarity:.2f}): '{current_query[:50]}...'")
            # Use similarity as confidence (0.3-1.0 mapped to 0.5-0.9)
            confidence = min(0.9, 0.5 + (similarity * 0.5))
            return ('rephrase', confidence, prev)

    return None


def log_implicit_feedback(conn, signal_type: str, signal_confidence: float,
                          log_id: str = None, doc_path: str = None,
                          session_id: str = None):
    """Log implicit feedback signal to rag_feedback table."""
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.rag_feedback
            (log_id, signal_type, signal_confidence, doc_path, session_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (log_id, signal_type, signal_confidence, doc_path, session_id))
        conn.commit()
        logger.info(f"Logged implicit feedback: {signal_type} (confidence={signal_confidence})")
    except Exception as e:
        logger.warning(f"Failed to log implicit feedback: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def update_doc_quality(conn, doc_path: str, is_hit: bool):
    """Update doc quality tracking (miss counter).

    Docs with 3+ misses get flagged for review.
    """
    try:
        cur = conn.cursor()

        if is_hit:
            cur.execute("""
                INSERT INTO claude.rag_doc_quality (doc_path, hit_count, last_hit_at)
                VALUES (%s, 1, NOW())
                ON CONFLICT (doc_path) DO UPDATE SET
                    hit_count = claude.rag_doc_quality.hit_count + 1,
                    last_hit_at = NOW(),
                    quality_score = (claude.rag_doc_quality.hit_count + 1)::float /
                                   NULLIF(claude.rag_doc_quality.hit_count + 1 + claude.rag_doc_quality.miss_count, 0),
                    updated_at = NOW()
            """, (doc_path,))
        else:
            # Miss - increment counter and check for flagging
            cur.execute("""
                INSERT INTO claude.rag_doc_quality (doc_path, miss_count, last_miss_at)
                VALUES (%s, 1, NOW())
                ON CONFLICT (doc_path) DO UPDATE SET
                    miss_count = claude.rag_doc_quality.miss_count + 1,
                    last_miss_at = NOW(),
                    quality_score = claude.rag_doc_quality.hit_count::float /
                                   NULLIF(claude.rag_doc_quality.hit_count + claude.rag_doc_quality.miss_count + 1, 0),
                    flagged_for_review = CASE
                        WHEN claude.rag_doc_quality.miss_count + 1 >= 3 THEN true
                        ELSE claude.rag_doc_quality.flagged_for_review
                    END,
                    updated_at = NOW()
                RETURNING miss_count, flagged_for_review
            """, (doc_path,))

            result = cur.fetchone()
            if result:
                miss_count = result[0] if not isinstance(result, dict) else result['miss_count']
                flagged = result[1] if not isinstance(result, dict) else result['flagged_for_review']
                # Only warn on the exact transition to flagged (miss_count == 3), not on every subsequent miss
                if flagged and miss_count == 3:
                    logger.warning(f"Doc flagged for review after {miss_count} misses: {doc_path}")

        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to update doc quality: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def detect_session_keywords(user_prompt: str) -> bool:
    """Detect if user prompt contains session-related keywords.

    Returns True if prompt is asking about session context, todos, or resumption.
    """
    prompt_lower = user_prompt.lower()
    for keyword in SESSION_KEYWORDS:
        if keyword in prompt_lower:
            logger.info(f"Detected session keyword: '{keyword}'")
            return True
    return False


def detect_config_keywords(user_prompt: str) -> bool:
    """Detect if user prompt mentions config files that are database-generated.

    Returns True if prompt mentions settings.local.json, hooks, or config editing.
    This triggers a warning that these files should not be manually edited.
    """
    prompt_lower = user_prompt.lower()
    for keyword in CONFIG_KEYWORDS:
        if keyword in prompt_lower:
            logger.info(f"Detected config keyword: '{keyword}'")
            return True
    return False


def get_session_context(project_name: str) -> Optional[str]:
    """Deprecated: Session context now served by project-tools get_work_context MCP tool.

    Returns None - callers should use get_work_context(scope='project') instead.
    """
    logger.info("get_session_context called but deprecated - use get_work_context MCP tool")
    return None


def process_implicit_feedback(conn, user_prompt: str, session_id: str = None):
    """Process current prompt for implicit feedback signals.

    This checks for:
    1. Explicit negative phrases
    2. Query rephrasing (similar to recent query)
    """
    if not session_id:
        return

    # Check for explicit negative feedback
    negative = detect_explicit_negative(user_prompt)
    if negative:
        signal_type, confidence = negative

        # Get most recent query to associate feedback with
        recent = get_recent_rag_queries(conn, session_id, limit=1)
        if recent:
            prev = recent[0]
            log_id = prev.get('log_id')
            docs = prev.get('docs_returned', [])

            # Log feedback for each doc that was returned
            for doc_path in (docs or []):
                log_implicit_feedback(conn, signal_type, confidence,
                                      log_id=log_id, doc_path=doc_path,
                                      session_id=session_id)
                update_doc_quality(conn, doc_path, is_hit=False)
        return

    # Check for query rephrase
    recent = get_recent_rag_queries(conn, session_id, limit=3)
    if recent:
        rephrase = detect_query_rephrase(user_prompt, recent)
        if rephrase:
            signal_type, confidence, prev = rephrase
            log_id = prev.get('log_id')
            docs = prev.get('docs_returned', [])

            # Log feedback - rephrase indicates previous results weren't helpful
            for doc_path in (docs or []):
                log_implicit_feedback(conn, signal_type, confidence,
                                      log_id=log_id, doc_path=doc_path,
                                      session_id=session_id)
                update_doc_quality(conn, doc_path, is_hit=False)


def query_knowledge(user_prompt: str, project_name: str, session_id: str = None,
                    top_k: int = 3, min_similarity: float = 0.55) -> str:
    """Query knowledge table for relevant entries.

    Args:
        user_prompt: The user's question/prompt
        project_name: Current project name
        session_id: Current session ID (for logging)
        top_k: Number of results to return
        min_similarity: Minimum similarity score (0-1)

    Returns:
        Formatted context string or None if no results
    """
    if not DB_AVAILABLE:
        return None

    # Note: VOYAGE_AVAILABLE is checked inside generate_embedding() (lazy-loaded)

    try:
        start_time = time.time()

        # Extract query from user prompt
        query_text = extract_query_from_prompt(user_prompt)

        # Generate embedding for query (lazy-loads voyageai if needed)
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return None

        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()

        # Search knowledge table for similar entries
        # Filter by project if applies_to_projects is set, or include general knowledge
        # Note: applies_to_projects can be NULL, empty array [], or contain project names
        cur.execute("""
            SELECT
                knowledge_id::text,
                title,
                description,
                knowledge_type,
                knowledge_category,
                code_example,
                confidence_level,
                times_applied,
                1 - (embedding <=> %s::vector) as similarity_score,
                COALESCE(tier, 'mid') as tier
            FROM claude.knowledge
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> %s::vector) >= %s
              AND COALESCE(tier, 'mid') != 'archived'
              AND (
                  applies_to_projects IS NULL
                  OR cardinality(applies_to_projects) = 0
                  OR %s = ANY(applies_to_projects)
              )
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity, project_name, query_embedding, top_k))

        results = cur.fetchall()

        if not results:
            conn.close()
            return None

        # Update access tracking for returned knowledge
        for r in results:
            knowledge_id = r['knowledge_id'] if isinstance(r, dict) else r[0]
            cur.execute("""
                UPDATE claude.knowledge
                SET last_accessed_at = NOW(),
                    access_count = COALESCE(access_count, 0) + 1
                WHERE knowledge_id = %s::uuid
            """, (knowledge_id,))
        conn.commit()

        latency_ms = int((time.time() - start_time) * 1000)

        # Format results
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        context_lines.append(f"KNOWLEDGE RECALL ({len(results)} relevant entries, {latency_ms}ms)")
        context_lines.append("=" * 70)
        context_lines.append("")

        for r in results:
            if isinstance(r, dict):
                title = r['title']
                description = r['description']
                knowledge_type = r['knowledge_type']
                category = r['knowledge_category']
                code_example = r['code_example']
                confidence = r['confidence_level']
                times_applied = r['times_applied']
                similarity = round(r['similarity_score'], 3)
                tier = r.get('tier', 'mid')
            else:
                title = r[1]
                description = r[2]
                knowledge_type = r[3]
                category = r[4]
                code_example = r[5]
                confidence = r[6]
                times_applied = r[7]
                similarity = round(r[8], 3)
                tier = r[9] if len(r) > 9 else 'mid'

            # Format entry with tier label
            tier_label = f"[{tier.upper()}]" if tier else "[MID]"
            type_info = knowledge_type or 'knowledge'
            if category:
                type_info += f"/{category}"
            confidence_str = f"conf={confidence}%" if confidence else ""
            applied_str = f"used {times_applied}x" if times_applied else "never used"

            context_lines.append(f"{tier_label} {title} ({similarity} match, {type_info})")
            context_lines.append(f"   {confidence_str} | {applied_str}")
            context_lines.append("")
            context_lines.append(description)

            if code_example:
                context_lines.append("")
                context_lines.append("Code Example:")
                context_lines.append(code_example)

            context_lines.append("")
            context_lines.append("-" * 70)
            context_lines.append("")

        logger.info(f"Knowledge query success: {len(results)} entries, latency={latency_ms}ms")
        conn.close()
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Knowledge query failed: {e}", exc_info=True)
        return None


def query_knowledge_graph(user_prompt: str, project_name: str, session_id: str = None,
                          max_initial_hits: int = 3, max_hops: int = 2,
                          min_similarity: float = 0.55, token_budget: int = 400) -> Optional[str]:
    """Graph-aware knowledge search: pgvector seed + recursive CTE graph walk.

    Enhanced version of query_knowledge that also walks knowledge_relations
    to discover connected entries. Falls back to query_knowledge on error.

    Args:
        user_prompt: The user's question/prompt
        project_name: Current project name
        session_id: Current session ID (for logging)
        max_initial_hits: Max pgvector seed results
        max_hops: Max relationship hops from seed nodes
        min_similarity: Minimum similarity score (0-1)
        token_budget: Approximate token budget for results

    Returns:
        Formatted context string or None if no results
    """
    if not DB_AVAILABLE:
        return None

    try:
        start_time = time.time()

        query_text = extract_query_from_prompt(user_prompt)
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return None

        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()

        # Call the graph-aware search SQL function (explicit casts for psycopg type matching)
        cur.execute("""
            SELECT * FROM claude.graph_aware_search(
                %s::vector, %s::integer, %s::integer, 0.3::numeric, %s::numeric, %s::integer
            )
        """, (query_embedding, max_initial_hits, max_hops,
              min_similarity, token_budget))

        results = cur.fetchall()

        if not results:
            conn.close()
            return None

        # Update access stats via the bulk function
        knowledge_ids = [r['knowledge_id'] if isinstance(r, dict) else r[0] for r in results]
        cur.execute("SELECT claude.update_knowledge_access(%s)", (knowledge_ids,))
        conn.commit()

        latency_ms = int((time.time() - start_time) * 1000)
        direct_count = sum(1 for r in results if (r['source_type'] if isinstance(r, dict) else r[6]) == 'direct')
        graph_count = sum(1 for r in results if (r['source_type'] if isinstance(r, dict) else r[6]) == 'graph')

        # Format results
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        label = f"KNOWLEDGE GRAPH ({len(results)} entries: {direct_count} direct + {graph_count} graph, {latency_ms}ms)"
        context_lines.append(label)
        context_lines.append("=" * 70)
        context_lines.append("")

        for r in results:
            if isinstance(r, dict):
                title = r['title']
                description = r['description']
                knowledge_type = r['knowledge_type']
                category = r['knowledge_category']
                confidence = r['confidence_level']
                source_type = r['source_type']
                similarity = round(r['similarity'], 3)
                graph_depth = r['graph_depth']
                edge_path = r['edge_path']
                relevance = round(r['relevance_score'], 3)
            else:
                title = r[1]
                description = r[4]
                knowledge_type = r[2]
                category = r[3]
                confidence = r[5]
                source_type = r[6]
                similarity = round(r[7], 3)
                graph_depth = r[8]
                edge_path = r[9]
                relevance = round(r[10], 3)

            type_info = knowledge_type or 'knowledge'
            if category:
                type_info += f"/{category}"
            confidence_str = f"conf={confidence}%" if confidence else ""

            # Show source indicator
            if source_type == 'graph':
                source_label = f"graph:{edge_path}(depth={graph_depth})"
            else:
                source_label = f"direct(sim={similarity})"

            context_lines.append(f"💡 {title} ({relevance} score, {type_info})")
            context_lines.append(f"   {confidence_str} | {source_label}")
            context_lines.append("")
            context_lines.append(description)
            context_lines.append("")
            context_lines.append("-" * 70)
            context_lines.append("")

        logger.info(f"Graph knowledge query: {len(results)} entries ({direct_count}+{graph_count}g), {latency_ms}ms")
        conn.close()
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Graph knowledge query failed, falling back: {e}", exc_info=True)
        # Fall back to standard pgvector-only search
        return query_knowledge(user_prompt, project_name, session_id,
                               top_k=max_initial_hits, min_similarity=min_similarity)


# =============================================================================
# SESSION FACTS AUTO-INJECTION (No embedding - just SQL)
# =============================================================================
# Lightweight query to inject critical session facts (credentials, endpoints,
# decisions) into every prompt. No Voyage AI needed - just a simple SELECT.

CRITICAL_FACT_TYPES = ['credential', 'endpoint', 'decision', 'config']


def query_critical_session_facts(project_name: str, session_id: str = None,
                                  limit: int = 5) -> Optional[str]:
    """Query critical session facts for auto-injection.

    This is LIGHTWEIGHT - no embeddings, just a simple SQL query.
    Only returns facts of critical types that Claude should always see.

    Args:
        project_name: Current project name
        session_id: Current session ID (optional)
        limit: Max facts to return

    Returns:
        Formatted context string or None if no facts
    """
    if not DB_AVAILABLE:
        return None

    try:
        start_time = time.time()
        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()

        # Simple query - no embeddings needed
        # Cast session_id to text for type inference on NULL check (fixes PostgreSQL parameter $4 error)
        cur.execute("""
            SELECT fact_key, fact_value, fact_type, is_sensitive
            FROM claude.session_facts
            WHERE project_name = %s
              AND fact_type = ANY(%s)
              AND (session_id::text = %s OR session_id IS NULL OR %s::text IS NULL)
            ORDER BY
                CASE fact_type
                    WHEN 'credential' THEN 1
                    WHEN 'endpoint' THEN 2
                    WHEN 'config' THEN 3
                    WHEN 'decision' THEN 4
                    ELSE 5
                END,
                created_at DESC
            LIMIT %s
        """, (project_name, CRITICAL_FACT_TYPES, session_id, session_id, limit))

        facts = cur.fetchall()
        conn.close()

        if not facts:
            return None

        latency_ms = int((time.time() - start_time) * 1000)

        # Format as compact notepad view
        lines = []
        lines.append("")
        lines.append("📓 YOUR NOTEPAD (auto-loaded critical facts):")

        for f in facts:
            if isinstance(f, dict):
                key = f['fact_key']
                value = f['fact_value'] if not f['is_sensitive'] else '[SENSITIVE]'
                ftype = f['fact_type']
            else:
                key = f[0]
                value = f[1] if not f[3] else '[SENSITIVE]'
                ftype = f[2]

            # Truncate long values
            if len(value) > 60:
                value = value[:57] + "..."

            lines.append(f"  [{ftype}] {key}: {value}")

        lines.append(f"  (Use list_session_facts() for full notepad | {latency_ms}ms)")
        lines.append("")

        logger.info(f"Session facts auto-inject: {len(facts)} facts, {latency_ms}ms")
        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Session facts query failed: {e}")
        return None


# Nimbus project names that should trigger nimbus_context queries
NIMBUS_PROJECTS = [
    'monash-nimbus-reports',
    'nimbus-user-loader',
    'nimbus-customer-app',
    'ATO-Tax-Agent',
]


def query_nimbus_context(user_prompt: str, project_name: str, top_k: int = 3) -> str:
    """Query nimbus_context schema for Nimbus project knowledge.

    Uses keyword search (no embeddings) for:
    - code_patterns: Reusable code patterns
    - project_learnings: Lessons learned
    - project_facts: Known facts about the codebase

    Args:
        user_prompt: The user's question/prompt
        project_name: Current project name
        top_k: Number of results per table

    Returns:
        Formatted context string or None if no results
    """
    if not DB_AVAILABLE:
        return None

    # Only query for Nimbus projects
    if project_name not in NIMBUS_PROJECTS:
        return None

    try:
        start_time = time.time()
        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()

        # Extract keywords from prompt (simple tokenization)
        keywords = [w.lower() for w in re.findall(r'\w+', user_prompt) if len(w) > 3]
        if not keywords:
            conn.close()
            return None

        # Build search pattern (any keyword match)
        search_pattern = '%' + '%'.join(keywords[:5]) + '%'  # Limit to 5 keywords

        results = []

        # 1. Search code_patterns
        try:
            cur.execute("""
                SELECT 'pattern' as source, pattern_type, solution, context, created_at
                FROM nimbus_context.code_patterns
                WHERE solution ILIKE %s OR context ILIKE %s OR pattern_type ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (search_pattern, search_pattern, search_pattern, top_k))
            results.extend([('pattern', r) for r in cur.fetchall()])
        except Exception as e:
            logger.warning(f"code_patterns query failed: {e}")

        # 2. Search project_learnings
        try:
            cur.execute("""
                SELECT 'learning' as source, category, learning, context, created_at
                FROM nimbus_context.project_learnings
                WHERE learning ILIKE %s OR context ILIKE %s OR category ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (search_pattern, search_pattern, search_pattern, top_k))
            results.extend([('learning', r) for r in cur.fetchall()])
        except Exception as e:
            logger.warning(f"project_learnings query failed: {e}")

        # 3. Search project_facts
        try:
            cur.execute("""
                SELECT 'fact' as source, category, fact_key, fact_value, created_at
                FROM nimbus_context.project_facts
                WHERE fact_key ILIKE %s OR fact_value ILIKE %s OR category ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (search_pattern, search_pattern, search_pattern, top_k))
            results.extend([('fact', r) for r in cur.fetchall()])
        except Exception as e:
            logger.warning(f"project_facts query failed: {e}")

        conn.close()

        if not results:
            logger.info(f"No nimbus_context results for keywords: {keywords[:3]}")
            return None

        latency_ms = int((time.time() - start_time) * 1000)

        # Format results
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        context_lines.append(f"NIMBUS PROJECT CONTEXT ({len(results)} entries, {latency_ms}ms)")
        context_lines.append("=" * 70)
        context_lines.append("")

        for source_type, r in results:
            if isinstance(r, dict):
                if source_type == 'pattern':
                    context_lines.append(f"🔧 PATTERN [{r['pattern_type']}]")
                    context_lines.append(f"   Context: {r['context'] or 'N/A'}")
                    context_lines.append(f"   Solution: {r['solution'][:200]}...")
                elif source_type == 'learning':
                    context_lines.append(f"💡 LEARNING [{r['category']}]")
                    context_lines.append(f"   Context: {r['context'] or 'N/A'}")
                    context_lines.append(f"   {r['learning']}")
                elif source_type == 'fact':
                    context_lines.append(f"📋 FACT [{r['category']}]")
                    context_lines.append(f"   {r['fact_key']}: {r['fact_value']}")
            else:
                # Tuple format (psycopg2)
                if source_type == 'pattern':
                    context_lines.append(f"🔧 PATTERN [{r[1]}]")
                    context_lines.append(f"   Context: {r[3] or 'N/A'}")
                    context_lines.append(f"   Solution: {r[2][:200] if r[2] else 'N/A'}...")
                elif source_type == 'learning':
                    context_lines.append(f"💡 LEARNING [{r[1]}]")
                    context_lines.append(f"   Context: {r[3] or 'N/A'}")
                    context_lines.append(f"   {r[2]}")
                elif source_type == 'fact':
                    context_lines.append(f"📋 FACT [{r[1]}]")
                    context_lines.append(f"   {r[2]}: {r[3]}")
            context_lines.append("")

        context_lines.append("-" * 70)
        context_lines.append("")

        logger.info(f"Nimbus context query: {len(results)} results, latency={latency_ms}ms")
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Nimbus context query failed: {e}", exc_info=True)
        return None


def query_vault_rag(user_prompt: str, project_name: str, session_id: str = None,
                    top_k: int = 3, min_similarity: float = 0.45) -> str:
    """Query vault embeddings and return formatted context.

    Args:
        user_prompt: The user's question/prompt
        project_name: Current project name
        session_id: Current session ID (for logging)
        top_k: Number of results to return
        min_similarity: Minimum similarity score (0-1)

    Returns:
        Formatted context string or None if no results
    """
    if not DB_AVAILABLE:
        logger.warning("Database not available - skipping RAG")
        return None

    # Note: VOYAGE_AVAILABLE is checked inside generate_embedding() (lazy-loaded)

    try:
        start_time = time.time()

        # Extract query from user prompt
        query_text = extract_query_from_prompt(user_prompt)

        # Connect to database (needed for vocabulary expansion and search)
        conn = get_db_connection()
        if not conn:
            logger.warning("Could not connect to database - skipping RAG")
            return None

        # VOCABULARY EXPANSION: Expand query with learned user vocabulary
        # This translates user phrases (e.g., "spin up") to canonical concepts (e.g., "create")
        expanded_query = expand_query_with_vocabulary(conn, query_text)

        # Generate embedding for EXPANDED query (better semantic matching)
        query_embedding = generate_embedding(expanded_query)
        if not query_embedding:
            conn.close()
            return None

        cur = conn.cursor()

        # Search for similar documents (prefer vault docs, include project docs)
        # EXCLUSIONS: awesome-copilot-reference is reference material, not searchable knowledge
        # DEDUPLICATION: Fetch extra results, then dedupe by doc_path (take best chunk per doc)
        fetch_count = top_k * 3  # Fetch 3x to allow for deduplication
        cur.execute("""
            SELECT
                doc_path,
                doc_title,
                chunk_text,
                doc_source,
                1 - (embedding <=> %s::vector) as similarity_score
            FROM claude.vault_embeddings
            WHERE 1 - (embedding <=> %s::vector) >= %s
              AND (doc_source = 'vault' OR (doc_source = 'project' AND project_name = %s))
              AND doc_path NOT LIKE '%%awesome-copilot%%'
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity, project_name, query_embedding, fetch_count))

        raw_results = cur.fetchall()

        # DEDUPLICATION: Group by doc_path, keep highest similarity chunk per doc
        # This prevents the same document appearing 2-3 times with different chunks
        seen_docs = {}
        for r in raw_results:
            doc_path = r['doc_path'] if isinstance(r, dict) else r[0]
            similarity = r['similarity_score'] if isinstance(r, dict) else r[4]

            if doc_path not in seen_docs or similarity > (seen_docs[doc_path]['similarity_score'] if isinstance(seen_docs[doc_path], dict) else seen_docs[doc_path][4]):
                seen_docs[doc_path] = r

        # Convert back to list and take top_k
        results = list(seen_docs.values())[:top_k]
        logger.info(f"Deduplication: {len(raw_results)} raw -> {len(seen_docs)} unique docs -> {len(results)} returned")

        # Log usage
        latency_ms = int((time.time() - start_time) * 1000)
        docs_returned = [r['doc_path'] if isinstance(r, dict) else r[0] for r in results]
        top_similarity = results[0]['similarity_score'] if results and isinstance(results[0], dict) else (results[0][4] if results else None)

        # Log RAG usage to database (try with session_id, fall back to NULL if FK fails)
        try:
            cur.execute("""
                INSERT INTO claude.rag_usage_log
                (session_id, project_name, query_type, query_text, results_count,
                 top_similarity, docs_returned, latency_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session_id,  # May be None or invalid
                project_name,
                "user_prompt",
                query_text,
                len(results),
                top_similarity,
                docs_returned,
                latency_ms
            ))
            conn.commit()
            logger.info(f"RAG usage logged to database (session_id={'NULL' if not session_id else session_id[:8]}...)")
        except Exception as log_error:
            # If foreign key constraint fails (session_id not in sessions table),
            # retry with NULL session_id to preserve usage data
            error_msg = str(log_error)
            if 'fk_session' in error_msg or 'foreign key constraint' in error_msg:
                logger.warning(f"Session ID {session_id[:8] if session_id else 'None'}... not in database, logging with NULL")
                try:
                    # CRITICAL: Rollback failed transaction before retry
                    conn.rollback()

                    cur.execute("""
                        INSERT INTO claude.rag_usage_log
                        (session_id, project_name, query_type, query_text, results_count,
                         top_similarity, docs_returned, latency_ms)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        None,  # Use NULL instead of invalid session_id
                        project_name,
                        "user_prompt",
                        query_text,
                        len(results),
                        top_similarity,
                        docs_returned,
                        latency_ms
                    ))
                    conn.commit()
                    logger.info("RAG usage logged with NULL session_id (session mismatch)")
                except Exception as retry_error:
                    logger.error(f"Failed to log RAG usage even with NULL session_id: {retry_error}")
            else:
                logger.warning(f"Failed to log RAG usage: {log_error}")

        if not results:
            logger.info(f"No RAG results for query (similarity < {min_similarity}). Query: {query_text[:100]}")
            conn.close()
            return None

        # Format results
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        context_lines.append(f"KNOWLEDGE VAULT CONTEXT ({len(results)} relevant docs, {latency_ms}ms)")
        context_lines.append("=" * 70)
        context_lines.append("")

        for r in results:
            if isinstance(r, dict):
                doc_title = r['doc_title']
                doc_path = r['doc_path']
                chunk_text = r['chunk_text']
                similarity = round(r['similarity_score'], 3)
            else:
                doc_title = r[1]
                doc_path = r[0]
                chunk_text = r[2]
                similarity = round(r[4], 3)

            context_lines.append(f"📄 {doc_title} ({similarity} match)")
            context_lines.append(f"   Location: {doc_path}")
            context_lines.append("")
            # Include full chunk text (not truncated)
            context_lines.append(chunk_text)
            context_lines.append("")
            context_lines.append("-" * 70)
            context_lines.append("")

        logger.info(f"RAG query success: {len(results)} docs, top={top_similarity:.3f}, latency={latency_ms}ms")
        conn.close()
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        return None


def query_skill_suggestions(user_prompt: str, project_name: str,
                             top_k: int = 2, min_similarity: float = 0.50) -> str:
    """Query skill_content for relevant skills by semantic similarity.

    Args:
        user_prompt: The user's question/prompt
        project_name: Current project name
        top_k: Number of skills to suggest
        min_similarity: Minimum similarity score (0-1)

    Returns:
        Formatted skill suggestions or None if no matches
    """
    if not DB_AVAILABLE:
        return None

    # Note: VOYAGE_AVAILABLE is checked inside generate_embedding() (lazy-loaded)

    try:
        start_time = time.time()

        # Generate embedding for query (lazy-loads voyageai if needed)
        query_text = extract_query_from_prompt(user_prompt)
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return None

        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()

        # Search skill_content by embedding similarity
        cur.execute("""
            SELECT
                name,
                description,
                category,
                1 - (description_embedding <=> %s::vector) as similarity_score
            FROM claude.skill_content
            WHERE active = true
              AND description_embedding IS NOT NULL
              AND 1 - (description_embedding <=> %s::vector) >= %s
            ORDER BY description_embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity, query_embedding, top_k))

        results = cur.fetchall()
        conn.close()

        if not results:
            logger.info(f"No skill matches >= {min_similarity} for query: {query_text[:50]}")
            return None

        latency_ms = int((time.time() - start_time) * 1000)

        # Format suggestions
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        context_lines.append(f"SKILL SUGGESTIONS ({len(results)} matches, {latency_ms}ms)")
        context_lines.append("=" * 70)
        context_lines.append("")

        for r in results:
            if isinstance(r, dict):
                name = r['name']
                description = r['description']
                category = r['category']
                similarity = round(r['similarity_score'], 2)
            else:
                name = r[0]
                description = r[1]
                category = r[2]
                similarity = round(r[3], 2)

            # Truncate description
            desc_short = description[:100] + "..." if len(description) > 100 else description

            context_lines.append(f">> {name} ({similarity} match, {category})")
            context_lines.append(f"   {desc_short}")
            context_lines.append(f"   Action: Use Skill tool to load if task is complex")
            context_lines.append("")

        context_lines.append("-" * 70)
        context_lines.append("")

        logger.info(f"Skill suggestions: {len(results)} matches, top={results[0]['similarity_score'] if isinstance(results[0], dict) else results[0][3]:.2f}")
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Skill suggestion query failed: {e}", exc_info=True)
        return None


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

        # SKILL SUGGESTIONS: Re-enabled (FB138 fix)
        # Query skill_content for semantically relevant skills on non-command prompts.
        # Previously disabled ("never acted on") but the discovery gap was the root cause.
        skill_context = None
        if DB_AVAILABLE:
            try:
                skill_context = query_skill_suggestions(
                    user_prompt=user_prompt,
                    project_name=project_name,
                    top_k=2,
                    min_similarity=0.55
                )
            except Exception as e:
                logger.warning(f"Skill suggestion query failed: {e}")

        # CONDITIONAL: Only query RAG/knowledge for questions and exploration
        # Action prompts ("implement X", "fix Y") don't benefit from documentation retrieval
        knowledge_context = None
        rag_context = None
        nimbus_context = None

        if needs_rag(user_prompt):
            logger.info(f"RAG enabled for prompt: {user_prompt[:50]}")

            # Query KNOWLEDGE GRAPH (pgvector seed + relationship walk)
            # Note: Voyage-3 similarity scores are typically 0.3-0.5 for good matches
            knowledge_context = query_knowledge_graph(
                user_prompt=user_prompt,
                project_name=project_name,
                session_id=session_id,
                max_initial_hits=3,
                max_hops=2,
                min_similarity=0.35,
                token_budget=400,
            )

            # Query RAG (vault knowledge - documentation)
            rag_context = query_vault_rag(
                user_prompt=user_prompt,
                project_name=project_name,
                session_id=session_id,
                top_k=3,
                min_similarity=0.45
            )

            # Query NIMBUS CONTEXT (keyword search for Nimbus projects only)
            nimbus_context = query_nimbus_context(
                user_prompt=user_prompt,
                project_name=project_name,
                top_k=3
            )
        else:
            logger.info(f"RAG skipped for action prompt: {user_prompt[:50]}")

        # Combine contexts in priority order:
        # 1. Core protocol (ALWAYS - task discipline)
        # 2. Critical session facts (ALWAYS - lightweight notepad)
        # 3. Session context (if session keywords detected)
        # 4. Config warning (if config keywords detected)
        # 5. Knowledge recall (if RAG enabled - questions only)
        # 6. Vault RAG (if RAG enabled - questions only)
        # 7. Nimbus context (if RAG enabled + Nimbus project)
        combined_context_parts = []

        combined_context_parts.append(_get_core_protocol())

        # PROCESS FAILURES: Surface pending auto-filed failures for self-improvement
        try:
            from failure_capture import get_pending_failures, format_pending_failures
            pending_failures = get_pending_failures(project_name, max_age_hours=48)
            failure_context = format_pending_failures(pending_failures)
            if failure_context:
                combined_context_parts.append(failure_context)
        except Exception:
            pass  # Don't let failure surfacing break the hook

        if critical_facts:
            combined_context_parts.append(critical_facts)
        if session_context:
            combined_context_parts.append(session_context)
        if config_warning:
            combined_context_parts.append(config_warning)
        if knowledge_context:
            combined_context_parts.append(knowledge_context)
        if rag_context:
            combined_context_parts.append(rag_context)
        if nimbus_context:
            combined_context_parts.append(nimbus_context)
        if skill_context:
            combined_context_parts.append(skill_context)

        combined_context = "\n".join(combined_context_parts) if combined_context_parts else ""

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
