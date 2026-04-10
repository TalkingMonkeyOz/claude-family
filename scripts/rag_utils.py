#!/usr/bin/env python3
"""
RAG Utilities — Embedding generation, NLP utilities, and prompt classification.

Extracted from rag_query_hook.py. Contains:
- generate_embedding(): Voyage AI embedding generation (lazy-loaded)
- extract_query_from_prompt(): Prompt truncation/normalization
- expand_query_with_vocabulary(): DB-backed query expansion
- is_command(): Short imperative command detection
- needs_rag(): RAG relevance gate
- detect_explicit_negative(): Negative feedback signal detection
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re
import logging
from typing import List, Tuple, Optional

from config import detect_psycopg

psycopg_mod, _, _, _ = detect_psycopg()
DB_AVAILABLE = psycopg_mod is not None

logger = logging.getLogger('rag_query.utils')

# =============================================================================
# COMMAND DETECTION CONSTANTS
# =============================================================================

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


# =============================================================================
# RAG RELEVANCE CONSTANTS
# =============================================================================

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
    'i want to know',  # Conversational question forms
    'can you',         # Requests that often need context
    'can we',
    'find ',           # "find the credentials", "find the docs" (trailing space avoids matching "find" in words)
    'look at',         # "look at the session lifecycle"
    'look into',
    'check if',        # "check if we have UserSDK docs"
    'check the',
    'have a look',     # Conversational phrasing
    'whats ',          # "whats the session lifecycle" (no apostrophe, common in speech-to-text)
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


# =============================================================================
# SELF-LEARNING: Implicit Feedback Detection
# =============================================================================

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


# =============================================================================
# FUNCTIONS
# =============================================================================

def generate_embedding(text: str) -> list:
    """Generate embedding using the configured provider (FastEmbed local or Voyage AI API).

    Uses embedding_provider.py abstraction layer. Default: FastEmbed (local CPU, no API key).
    Set EMBEDDING_PROVIDER=voyage to use Voyage AI instead.
    """
    try:
        from embedding_provider import embed
        return embed(text)
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
            # Override 1: Compound prompts with embedded questions
            EMBEDDED_QUESTION_INDICATORS = [
                '?', 'explain', 'how do', 'what is', 'why does',
                'understand', 'describe', 'clarify', 'tell me about',
            ]
            if len(prompt_lower) > 50 and any(
                q in prompt_lower for q in EMBEDDED_QUESTION_INDICATORS
            ):
                return True

            # Override 2: Action prompts that reference existing knowledge
            # "implement X using the existing patterns" needs context about X
            KNOWLEDGE_REFERENCE_SIGNALS = [
                'using existing', 'using the', 'with the existing',
                'about the', 'based on', 'according to',
                'the existing', 'our existing', 'the current',
                'sdk', 'api', 'endpoint',  # Domain terms that need lookup
            ]
            if any(sig in prompt_lower for sig in KNOWLEDGE_REFERENCE_SIGNALS):
                return True

            return False

    # Slash commands don't need RAG (they load their own context)
    if prompt_lower.startswith('/'):
        return False

    # Default: if prompt is long enough, it might benefit from RAG
    # Lowered from 100 to 50 chars to catch conversational prompts like
    # "I want to know about the scheduled jobs" (43 chars)
    return len(prompt_lower) > 50


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
