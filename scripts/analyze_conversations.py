#!/usr/bin/env python3
"""
Conversation Analyzer for Vocabulary Learning

Analyzes existing Claude Code conversation transcripts (.jsonl files) to:
1. Extract user vocabulary patterns
2. Update vocabulary_mappings with discovered phrases
3. Optionally clean up old transcripts

Usage:
    python scripts/analyze_conversations.py              # Analyze all projects
    python scripts/analyze_conversations.py --project claude-family  # Specific project
    python scripts/analyze_conversations.py --cleanup --days 30      # Delete files older than 30 days
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection as _get_db_connection_shared, detect_psycopg
_psycopg_mod, PSYCOPG_VERSION, _, _ = detect_psycopg()
DB_AVAILABLE = _psycopg_mod is not None

# Conversation transcripts location
TRANSCRIPTS_DIR = Path.home() / ".claude" / "projects"

# Informal vocabulary patterns to detect
# These are colloquial phrases that might not match formal docs
INFORMAL_PATTERNS = [
    # Creation verbs
    (r'\b(spin up|whip up|throw together|knock out|bang out|crank out|put together)\b', 'create'),
    # Investigation verbs
    (r'\b(dig into|poke around|look into|check out|take a look at|have a look at)\b', 'investigate'),
    # Fixing verbs
    (r'\b(sort out|clean up|fix up|tidy up|straighten out|iron out)\b', 'fix'),
    # Starting/ending
    (r'\b(kick off|get going|fire up|boot up)\b', 'start'),
    (r'\b(wrap up|wind down|finish off|close out)\b', 'finish'),
    # UI references
    (r'\b(the panel|a panel|that panel|this panel)\b', 'UI component'),
    (r'\b(the screen|a screen|that screen|this screen)\b', 'UI view'),
    (r'\b(the dialog|a dialog|popup|modal)\b', 'dialog'),
    # Vague references
    (r'\b(the thing that|the thingy|that stuff|the widget)\b', 'component'),
    (r'\b(the bit where|the part that|the section)\b', 'component'),
    # Quick actions
    (r'\b(real quick|quickly|just)\s+(make|create|add|do)\b', 'create quickly'),
]


def get_db_connection():
    """Get PostgreSQL connection."""
    if not DB_AVAILABLE:
        return None
    return _get_db_connection_shared()


def get_existing_mappings(conn) -> Set[str]:
    """Get existing user phrases from vocabulary_mappings."""
    if not conn:
        return set()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_phrase FROM claude.vocabulary_mappings WHERE active = true")
        return {row['user_phrase'] if isinstance(row, dict) else row[0] for row in cur.fetchall()}
    except Exception:
        return set()


def extract_user_messages(jsonl_path: Path) -> List[str]:
    """Extract user messages from a JSONL transcript file."""
    messages = []
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get('type') == 'user':
                        msg = d.get('message', {})
                        content = msg.get('content', '')
                        if isinstance(content, str) and len(content) > 10:
                            # Skip command messages
                            if not content.startswith('<command-'):
                                messages.append(content)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"  Error reading {jsonl_path.name}: {e}")
    return messages


def find_vocabulary_candidates(messages: List[str]) -> Counter:
    """Find informal vocabulary patterns in messages."""
    candidates = Counter()

    for msg in messages:
        msg_lower = msg.lower()
        for pattern, _ in INFORMAL_PATTERNS:
            matches = re.findall(pattern, msg_lower)
            for match in matches:
                # Normalize the match
                phrase = match.strip() if isinstance(match, str) else match[0].strip()
                candidates[phrase] += 1

    return candidates


def analyze_project(project_dir: Path, existing_phrases: Set[str]) -> Tuple[Counter, int, int]:
    """Analyze all conversations in a project directory.

    Returns: (vocabulary_candidates, message_count, file_count)
    """
    all_candidates = Counter()
    total_messages = 0
    file_count = 0

    # Only analyze main session files, not agent files
    jsonl_files = [f for f in project_dir.glob("*.jsonl") if not f.name.startswith("agent-")]

    for jsonl_file in jsonl_files:
        messages = extract_user_messages(jsonl_file)
        if messages:
            candidates = find_vocabulary_candidates(messages)
            all_candidates.update(candidates)
            total_messages += len(messages)
            file_count += 1

    # Filter out already-known phrases
    for phrase in list(all_candidates.keys()):
        if phrase in existing_phrases:
            del all_candidates[phrase]

    return all_candidates, total_messages, file_count


def update_vocabulary_mappings(conn, candidates: Counter, min_count: int = 2) -> int:
    """Add new vocabulary mappings for frequently-seen phrases."""
    if not conn:
        return 0

    added = 0
    cur = conn.cursor()

    for phrase, count in candidates.most_common():
        if count < min_count:
            continue

        # Find the canonical concept for this phrase
        canonical = None
        for pattern, concept in INFORMAL_PATTERNS:
            if re.search(pattern, phrase):
                canonical = concept
                break

        if not canonical:
            continue

        try:
            cur.execute("""
                INSERT INTO claude.vocabulary_mappings
                (user_phrase, canonical_concept, times_seen, confidence, source)
                VALUES (%s, %s, %s, %s, 'auto_extracted')
                ON CONFLICT (user_phrase) DO UPDATE SET
                    times_seen = claude.vocabulary_mappings.times_seen + EXCLUDED.times_seen,
                    updated_at = NOW()
            """, (phrase, canonical, count, 0.6))
            added += 1
        except Exception as e:
            print(f"  Error adding '{phrase}': {e}")

    conn.commit()
    return added


def cleanup_old_files(days: int, dry_run: bool = True) -> Tuple[int, int]:
    """Delete conversation files older than specified days.

    Returns: (files_deleted, bytes_freed)
    """
    if not TRANSCRIPTS_DIR.exists():
        return 0, 0

    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0
    bytes_freed = 0

    for project_dir in TRANSCRIPTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        for jsonl_file in project_dir.glob("*.jsonl"):
            mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
            if mtime < cutoff:
                size = jsonl_file.stat().st_size
                if dry_run:
                    print(f"  Would delete: {jsonl_file.name} ({size // 1024}KB, {mtime.date()})")
                else:
                    jsonl_file.unlink()
                    print(f"  Deleted: {jsonl_file.name} ({size // 1024}KB)")
                deleted += 1
                bytes_freed += size

    return deleted, bytes_freed


def main():
    parser = argparse.ArgumentParser(description="Analyze conversations for vocabulary learning")
    parser.add_argument('--project', help='Analyze specific project only')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old transcript files')
    parser.add_argument('--days', type=int, default=30, help='Delete files older than N days (default: 30)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')
    parser.add_argument('--min-count', type=int, default=2, help='Minimum occurrences to add mapping (default: 2)')
    args = parser.parse_args()

    if args.cleanup:
        print(f"\n{'DRY RUN: ' if args.dry_run else ''}Cleaning up files older than {args.days} days...")
        deleted, freed = cleanup_old_files(args.days, dry_run=args.dry_run)
        print(f"\n{'Would delete' if args.dry_run else 'Deleted'}: {deleted} files, {freed // 1024 // 1024}MB freed")
        if args.dry_run:
            print("\nRun with --cleanup (without --dry-run) to actually delete files.")
        return

    print("\n" + "=" * 60)
    print("CONVERSATION VOCABULARY ANALYZER")
    print("=" * 60)

    if not TRANSCRIPTS_DIR.exists():
        print(f"Transcripts directory not found: {TRANSCRIPTS_DIR}")
        return

    # Get database connection
    conn = get_db_connection()
    existing = get_existing_mappings(conn)
    print(f"\nExisting vocabulary mappings: {len(existing)}")

    # Analyze projects
    all_candidates = Counter()
    total_messages = 0
    total_files = 0

    project_dirs = list(TRANSCRIPTS_DIR.iterdir())
    if args.project:
        project_dirs = [d for d in project_dirs if args.project.lower() in d.name.lower()]

    for project_dir in project_dirs:
        if not project_dir.is_dir():
            continue

        print(f"\nAnalyzing: {project_dir.name}")
        candidates, msg_count, file_count = analyze_project(project_dir, existing)

        if candidates:
            print(f"  Files: {file_count}, Messages: {msg_count}")
            print(f"  New vocabulary candidates: {len(candidates)}")
            for phrase, count in candidates.most_common(5):
                print(f"    - '{phrase}': {count}x")

        all_candidates.update(candidates)
        total_messages += msg_count
        total_files += file_count

    print("\n" + "-" * 60)
    print("SUMMARY")
    print("-" * 60)
    print(f"Total files analyzed: {total_files}")
    print(f"Total user messages: {total_messages}")
    print(f"Unique new phrases found: {len(all_candidates)}")

    if all_candidates:
        print("\nTop 10 new vocabulary candidates:")
        for phrase, count in all_candidates.most_common(10):
            print(f"  '{phrase}': {count}x")

        if conn:
            print(f"\nAdding phrases with {args.min_count}+ occurrences to database...")
            added = update_vocabulary_mappings(conn, all_candidates, min_count=args.min_count)
            print(f"Added/updated {added} vocabulary mappings")
            conn.close()
    else:
        print("\nNo new vocabulary patterns found.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
