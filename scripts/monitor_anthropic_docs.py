#!/usr/bin/env python3
"""
Anthropic Documentation Monitor

Checks key Anthropic documentation pages for updates and new features.
Stores hashes in PostgreSQL (claude.global_config) to detect changes between runs.

Usage:
    python monitor_anthropic_docs.py
    python monitor_anthropic_docs.py --verbose
"""

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import urllib.request
import urllib.error

try:
    import psycopg2
    from psycopg2.extras import Json
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Documentation pages to monitor
DOCS_TO_MONITOR = {
    "advanced-tool-use": {
        "url": "https://www.anthropic.com/engineering/advanced-tool-use",
        "description": "Advanced tool use patterns (Tool Search, Programmatic Calling)",
        "relevance": "MCP optimization, token reduction"
    },
    "claude-code-best-practices": {
        "url": "https://www.anthropic.com/engineering/claude-code-best-practices",
        "description": "Claude Code usage patterns and workflows",
        "relevance": "Agent patterns, multi-Claude workflows"
    },
    "building-agents": {
        "url": "https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk",
        "description": "Claude Agent SDK architecture",
        "relevance": "Subagent patterns, context management"
    },
    "claude-code-sandboxing": {
        "url": "https://www.anthropic.com/engineering/claude-code-sandboxing",
        "description": "Sandboxing for secure autonomous operation",
        "relevance": "Permission reduction, security"
    },
    "models-overview": {
        "url": "https://platform.claude.com/docs/en/about-claude/models/overview",
        "description": "Model capabilities and context windows",
        "relevance": "1M context, model selection"
    },
    "computer-use": {
        "url": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool",
        "description": "Computer use tool for desktop automation",
        "relevance": "Visual testing, UI automation"
    },
    "token-efficient-tools": {
        "url": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/token-efficient-tool-use",
        "description": "Token-efficient tool use patterns",
        "relevance": "Cost reduction, performance"
    },
    "extended-thinking": {
        "url": "https://platform.claude.com/docs/en/build-with-claude/extended-thinking",
        "description": "Extended thinking and reasoning",
        "relevance": "Complex reasoning, interleaved thinking"
    },
    "mcp-overview": {
        "url": "https://modelcontextprotocol.io/introduction",
        "description": "Model Context Protocol specification",
        "relevance": "MCP server development"
    },
    "claude-code-changelog": {
        "url": "https://claudelog.com/claude-code-changelog/",
        "description": "Claude Code release notes and updates",
        "relevance": "New features, CLI changes"
    }
}

# Fallback to JSON file if no database
STATE_FILE = Path(__file__).parent / ".anthropic_docs_state.json"
CONFIG_KEY = "anthropic_docs_monitor"


def get_db_connection():
    """Get database connection."""
    if not HAS_PSYCOPG2:
        return None
    try:
        return psycopg2.connect(
            host=os.environ.get("PGHOST", "localhost"),
            port=os.environ.get("PGPORT", "5432"),
            database=os.environ.get("PGDATABASE", "ai_company_foundation"),
            user=os.environ.get("PGUSER", "postgres"),
            password=os.environ.get("PGPASSWORD", "")
        )
    except Exception as e:
        print(f"  [WARN] Database connection failed: {e}")
        return None


def load_state() -> Dict:
    """Load previous state from database or file."""
    # Try database first
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT value FROM claude.global_config WHERE key = %s",
                    (CONFIG_KEY,)
                )
                row = cur.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            print(f"  [WARN] Database read failed: {e}")
        finally:
            conn.close()

    # Fallback to JSON file
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)

    return {"hashes": {}, "last_check": None, "docs": DOCS_TO_MONITOR}


def save_state(state: Dict):
    """Save state to database and file."""
    # Always save to file as backup
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)

    # Try database
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE claude.global_config
                    SET value = %s, updated_at = NOW()
                    WHERE key = %s
                """, (Json(state), CONFIG_KEY))

                if cur.rowcount == 0:
                    # Insert if doesn't exist
                    cur.execute("""
                        INSERT INTO claude.global_config (config_id, key, value, description, created_at, updated_at)
                        VALUES (gen_random_uuid(), %s, %s, %s, NOW(), NOW())
                    """, (CONFIG_KEY, Json(state), "Anthropic documentation monitor state"))

                conn.commit()
        except Exception as e:
            print(f"  [WARN] Database write failed: {e}")
            conn.rollback()
        finally:
            conn.close()


def fetch_page_hash(url: str) -> Optional[str]:
    """Fetch page and return content hash."""
    try:
        request = urllib.request.Request(
            url,
            headers={'User-Agent': 'Claude-Family-Doc-Monitor/1.0'}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
            return hashlib.sha256(content).hexdigest()[:16]
    except urllib.error.URLError as e:
        print(f"  ERROR fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def check_for_updates(verbose: bool = False) -> Dict[str, List[str]]:
    """Check all docs for updates."""
    state = load_state()
    previous_hashes = state.get("hashes", {})

    results = {
        "changed": [],
        "new": [],
        "unchanged": [],
        "errors": []
    }

    current_hashes = {}

    print(f"\n{'='*60}")
    print(f"Anthropic Documentation Monitor")
    print(f"Checking {len(DOCS_TO_MONITOR)} pages for updates...")
    print(f"{'='*60}\n")

    for doc_id, doc_info in DOCS_TO_MONITOR.items():
        url = doc_info["url"]
        if verbose:
            print(f"Checking: {doc_id}")
            print(f"  URL: {url}")

        current_hash = fetch_page_hash(url)

        if current_hash is None:
            results["errors"].append(doc_id)
            if verbose:
                print(f"  Status: ERROR\n")
            continue

        current_hashes[doc_id] = current_hash
        previous_hash = previous_hashes.get(doc_id)

        if previous_hash is None:
            results["new"].append(doc_id)
            status = "NEW (first check)"
        elif current_hash != previous_hash:
            results["changed"].append(doc_id)
            status = f"CHANGED! (was {previous_hash}, now {current_hash})"
        else:
            results["unchanged"].append(doc_id)
            status = "unchanged"

        if verbose or status.startswith("CHANGED") or status.startswith("NEW"):
            print(f"  [{doc_id}] {status}")
            if status.startswith("CHANGED"):
                print(f"  >>> {doc_info['description']}")
                print(f"  >>> Relevance: {doc_info['relevance']}")
                print(f"  >>> URL: {url}")

    # Update state
    state["hashes"] = current_hashes
    state["last_check"] = datetime.now().isoformat()
    state["docs"] = DOCS_TO_MONITOR
    save_state(state)

    return results


def generate_report(results: Dict[str, List[str]]) -> str:
    """Generate summary report."""
    report = []
    report.append(f"\n{'='*60}")
    report.append("SUMMARY")
    report.append(f"{'='*60}")

    if results["changed"]:
        report.append(f"\n[!] CHANGED ({len(results['changed'])}):")
        for doc_id in results["changed"]:
            doc = DOCS_TO_MONITOR[doc_id]
            report.append(f"  - {doc_id}: {doc['description']}")
            report.append(f"    URL: {doc['url']}")
            report.append(f"    Relevance: {doc['relevance']}")

    if results["new"]:
        report.append(f"\n[+] NEW ({len(results['new'])}):")
        for doc_id in results["new"]:
            report.append(f"  - {doc_id}")

    report.append(f"\n[=] Unchanged: {len(results['unchanged'])}")

    if results["errors"]:
        report.append(f"\n[X] Errors: {len(results['errors'])}")
        for doc_id in results["errors"]:
            report.append(f"  - {doc_id}")

    report.append(f"\nLast checked: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(report)


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    results = check_for_updates(verbose)
    report = generate_report(results)
    print(report)

    # Exit with code 1 if changes detected (useful for CI/scheduling)
    if results["changed"]:
        print("\n[!] Documentation changes detected! Review the changes above.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
