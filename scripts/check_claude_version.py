#!/usr/bin/env python3
"""
Claude Code Version Checker

Lightweight version check using GitHub Releases API.
Compares installed version against latest release.
Stores state in claude.session_facts via DB or local file fallback.

Usage:
    python check_claude_version.py          # Quick check
    python check_claude_version.py --full   # Include recent changelog summary
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

STATE_FILE = Path(__file__).parent / ".version_state.json"


def get_installed_version() -> Optional[str]:
    """Get currently installed Claude Code version."""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            # Output format: "2.1.70 (Claude Code)"
            return result.stdout.strip().split()[0]
    except Exception as e:
        print(f"  [WARN] Could not get installed version: {e}")
    return None


def get_latest_release() -> Optional[dict]:
    """Get latest release from GitHub API via gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "api", "repos/anthropics/claude-code/releases",
             "--jq", ".[0] | {tag_name, published_at, name, body}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"  [WARN] Could not fetch latest release: {e}")
    return None


def get_recent_releases(count: int = 5) -> list:
    """Get recent releases for changelog summary."""
    try:
        result = subprocess.run(
            ["gh", "api", "repos/anthropics/claude-code/releases",
             "--jq", f".[0:{count}] | .[] | {{tag_name, published_at, name}}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            releases = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    releases.append(json.loads(line))
            return releases
    except Exception:
        pass
    return []


def load_state() -> dict:
    """Load previous check state."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state: dict):
    """Save check state."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        print(f"  [WARN] State save failed: {e}")


def check_version(full: bool = False) -> Tuple[bool, str]:
    """Check for Claude Code updates.

    Returns:
        (has_update, report_text)
    """
    installed = get_installed_version()
    latest_release = get_latest_release()
    state = load_state()

    report = []
    report.append(f"{'='*60}")
    report.append("Claude Code Version Check")
    report.append(f"{'='*60}")

    if not installed:
        report.append("[ERROR] Could not determine installed version")
        return False, "\n".join(report)

    report.append(f"  Installed: v{installed}")

    if not latest_release:
        report.append("[ERROR] Could not fetch latest release from GitHub")
        return False, "\n".join(report)

    latest_tag = latest_release["tag_name"].lstrip("v")
    published = latest_release.get("published_at", "unknown")

    report.append(f"  Latest:    v{latest_tag} (released {published[:10]})")

    has_update = installed != latest_tag

    if has_update:
        report.append(f"\n  [!] UPDATE AVAILABLE: v{installed} -> v{latest_tag}")

        # Show versions between installed and latest
        if full:
            recent = get_recent_releases(10)
            missed = [r for r in recent
                      if r["tag_name"].lstrip("v") > installed]
            if missed:
                report.append(f"\n  Versions you missed ({len(missed)}):")
                for r in missed:
                    tag = r["tag_name"]
                    date = r.get("published_at", "")[:10]
                    report.append(f"    {tag} ({date})")
    else:
        report.append(f"\n  [OK] You're on the latest version!")

    # Track state
    previous_version = state.get("last_installed_version")
    if previous_version and previous_version != installed:
        report.append(f"\n  [+] Upgraded since last check: v{previous_version} -> v{installed}")

    state["last_installed_version"] = installed
    state["last_latest_version"] = latest_tag
    state["last_check"] = datetime.now().isoformat()
    state["has_update"] = has_update
    save_state(state)

    report.append(f"\n  Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"{'='*60}")

    return has_update, "\n".join(report)


def main():
    full = "--full" in sys.argv
    has_update, report = check_version(full)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
