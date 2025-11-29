#!/usr/bin/env python3
"""
Install claude-family-core plugin to a project.

Usage:
    cd /path/to/your/project
    python C:/Projects/claude-family/scripts/install_plugin.py

Or specify target:
    python C:/Projects/claude-family/scripts/install_plugin.py /path/to/project
"""

import json
import os
import shutil
import sys
from pathlib import Path

# Source locations
PLUGIN_SOURCE = Path("C:/Projects/claude-family/.claude-plugins/claude-family-core")
HOOKS_SOURCE = Path("C:/Projects/claude-family/.claude/hooks.json")
COMMANDS_SOURCE = PLUGIN_SOURCE / "commands"

# Commands to install
COMMANDS = [
    "session-start.md",
    "session-end.md",
    "inbox-check.md",
    "broadcast.md",
    "feedback-check.md",
    "feedback-create.md",
    "team-status.md",
]


def install_plugin(target_dir: Path):
    """Install claude-family-core plugin to target directory."""

    print(f"Installing claude-family-core to: {target_dir}")
    print("=" * 50)

    # Create .claude directory if needed
    claude_dir = target_dir / ".claude"
    claude_dir.mkdir(exist_ok=True)

    # Create commands directory
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(exist_ok=True)

    # Create plugin directory structure
    plugin_dir = target_dir / ".claude-plugins" / "claude-family-core"
    plugin_scripts_dir = plugin_dir / "scripts"
    plugin_scripts_dir.mkdir(parents=True, exist_ok=True)

    # Copy commands
    print("\n[Commands] Installing...")
    for cmd in COMMANDS:
        src = COMMANDS_SOURCE / cmd
        dst = commands_dir / cmd
        if src.exists():
            shutil.copy2(src, dst)
            print(f"   + {cmd}")
        else:
            print(f"   - {cmd} (not found)")

    # Copy/merge hooks.json
    print("\n[Hooks] Installing...")
    dst_hooks = claude_dir / "hooks.json"
    if dst_hooks.exists():
        # Merge hooks
        print("   Existing hooks.json found - merging...")
        with open(HOOKS_SOURCE) as f:
            src_hooks = json.load(f)
        with open(dst_hooks) as f:
            dst_hooks_data = json.load(f)

        # Merge hook arrays
        for event_type, hooks_list in src_hooks.get("hooks", {}).items():
            if event_type not in dst_hooks_data.get("hooks", {}):
                if "hooks" not in dst_hooks_data:
                    dst_hooks_data["hooks"] = {}
                dst_hooks_data["hooks"][event_type] = hooks_list
            else:
                # Add hooks that don't exist
                existing_matchers = {h.get("matcher") for h in dst_hooks_data["hooks"][event_type]}
                for hook in hooks_list:
                    if hook.get("matcher") not in existing_matchers:
                        dst_hooks_data["hooks"][event_type].append(hook)

        with open(dst_hooks, 'w') as f:
            json.dump(dst_hooks_data, f, indent=2)
        print("   + hooks.json (merged)")
    else:
        shutil.copy2(HOOKS_SOURCE, dst_hooks)
        print("   + hooks.json (created)")

    # Copy startup script
    print("\n[Scripts] Installing...")
    src_script = PLUGIN_SOURCE / "scripts" / "session_startup_hook.py"
    dst_script = plugin_scripts_dir / "session_startup_hook.py"
    if src_script.exists():
        shutil.copy2(src_script, dst_script)
        print("   + session_startup_hook.py")

    # Copy plugin.json
    src_plugin_json = PLUGIN_SOURCE / ".claude-plugin" / "plugin.json"
    dst_plugin_json_dir = plugin_dir / ".claude-plugin"
    dst_plugin_json_dir.mkdir(exist_ok=True)
    if src_plugin_json.exists():
        shutil.copy2(src_plugin_json, dst_plugin_json_dir / "plugin.json")
        print("   + plugin.json")

    print("\n" + "=" * 50)
    print("Installation complete!")
    print("\nAvailable commands:")
    print("  /session-start  - Start session with context")
    print("  /session-end    - End session, save state")
    print("  /inbox-check    - Check messages")
    print("  /broadcast      - Send to all Claudes")
    print("  /feedback-check - View feedback items")
    print("  /team-status    - View team activity")
    print("\nNote: Restart Claude Code for hooks to take effect.")


def main():
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = Path.cwd()

    if not target.exists():
        print(f"Error: Target directory does not exist: {target}")
        sys.exit(1)

    # Check if it's a valid project (has .claude or is git repo)
    if not (target / ".claude").exists() and not (target / ".git").exists():
        print(f"Warning: {target} doesn't look like a Claude project")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    install_plugin(target)


if __name__ == "__main__":
    main()
