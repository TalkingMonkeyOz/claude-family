#!/usr/bin/env python3
"""
Install Claude Family plugins to a project.

Usage:
    cd /path/to/your/project
    python C:/Projects/claude-family/scripts/install_plugin.py

    # Install specific plugins
    python C:/Projects/claude-family/scripts/install_plugin.py --plugins core,web

    # Install to specific directory
    python C:/Projects/claude-family/scripts/install_plugin.py /path/to/project --plugins core
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# Plugin source directory
PLUGINS_SOURCE = Path("C:/Projects/claude-family/.claude-plugins")
HOOKS_SOURCE = Path("C:/Projects/claude-family/.claude/hooks.json")

# Available plugins
PLUGINS = {
    "core": {
        "name": "claude-family-core",
        "description": "Core session management, feedback, messaging (REQUIRED)",
        "layer": 1,
    },
    "web": {
        "name": "web-dev-toolkit",
        "description": "Next.js + shadcn/ui + TypeScript commands",
        "layer": 2,
    },
    "mission-control": {
        "name": "mission-control-tools",
        "description": "Mission Control dashboard and team management",
        "layer": 3,
    },
    "ato": {
        "name": "ato-tax-tools",
        "description": "ATO Tax Agent validation and compliance",
        "layer": 3,
    },
    "nimbus": {
        "name": "nimbus-loader-tools",
        "description": "Nimbus User Loader sync and validation",
        "layer": 3,
    },
}


def list_plugins():
    """Display available plugins."""
    print("\nAvailable Plugins:")
    print("=" * 60)

    for layer in [1, 2, 3]:
        layer_name = {1: "Layer 1 (Universal)", 2: "Layer 2 (Project Type)", 3: "Layer 3 (Project Specific)"}
        print(f"\n{layer_name[layer]}:")
        for key, info in PLUGINS.items():
            if info["layer"] == layer:
                print(f"  {key:15} - {info['description']}")

    print("\n" + "=" * 60)
    print("Usage: --plugins core,web,mission-control")


def install_plugin(plugin_key: str, target_dir: Path, verbose: bool = True):
    """Install a single plugin to target directory."""

    if plugin_key not in PLUGINS:
        print(f"   ERROR: Unknown plugin '{plugin_key}'")
        return False

    plugin_info = PLUGINS[plugin_key]
    plugin_name = plugin_info["name"]
    plugin_source = PLUGINS_SOURCE / plugin_name

    if not plugin_source.exists():
        print(f"   ERROR: Plugin source not found: {plugin_source}")
        return False

    # Create target directories
    claude_dir = target_dir / ".claude"
    claude_dir.mkdir(exist_ok=True)

    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(exist_ok=True)

    # Copy commands
    src_commands = plugin_source / "commands"
    if src_commands.exists():
        for cmd_file in src_commands.glob("*.md"):
            dst = commands_dir / cmd_file.name
            shutil.copy2(cmd_file, dst)
            if verbose:
                print(f"      + {cmd_file.name}")

    # For core plugin, also copy hooks and scripts
    if plugin_key == "core":
        # Copy hooks.json
        dst_hooks = claude_dir / "hooks.json"
        if dst_hooks.exists():
            # Merge hooks
            with open(HOOKS_SOURCE) as f:
                src_hooks = json.load(f)
            with open(dst_hooks) as f:
                dst_hooks_data = json.load(f)

            for event_type, hooks_list in src_hooks.get("hooks", {}).items():
                if event_type not in dst_hooks_data.get("hooks", {}):
                    if "hooks" not in dst_hooks_data:
                        dst_hooks_data["hooks"] = {}
                    dst_hooks_data["hooks"][event_type] = hooks_list

            with open(dst_hooks, 'w') as f:
                json.dump(dst_hooks_data, f, indent=2)
            if verbose:
                print("      + hooks.json (merged)")
        else:
            shutil.copy2(HOOKS_SOURCE, dst_hooks)
            if verbose:
                print("      + hooks.json")

        # Copy startup script
        plugin_scripts_dir = target_dir / ".claude-plugins" / plugin_name / "scripts"
        plugin_scripts_dir.mkdir(parents=True, exist_ok=True)

        src_script = plugin_source / "scripts" / "session_startup_hook.py"
        if src_script.exists():
            shutil.copy2(src_script, plugin_scripts_dir / "session_startup_hook.py")
            if verbose:
                print("      + session_startup_hook.py")

    return True


def main():
    parser = argparse.ArgumentParser(description="Install Claude Family plugins")
    parser.add_argument("target", nargs="?", default=".", help="Target directory")
    parser.add_argument("--plugins", "-p", help="Plugins to install (comma-separated)")
    parser.add_argument("--list", "-l", action="store_true", help="List available plugins")
    parser.add_argument("--all", "-a", action="store_true", help="Install all plugins")

    args = parser.parse_args()

    if args.list:
        list_plugins()
        return

    target = Path(args.target).resolve()

    if not target.exists():
        print(f"Error: Target directory does not exist: {target}")
        sys.exit(1)

    # Determine which plugins to install
    if args.all:
        plugins_to_install = list(PLUGINS.keys())
    elif args.plugins:
        plugins_to_install = [p.strip() for p in args.plugins.split(",")]
        # Always include core
        if "core" not in plugins_to_install:
            plugins_to_install.insert(0, "core")
    else:
        # Interactive selection
        list_plugins()
        print("\nWhich plugins do you want to install?")
        print("Enter plugin keys separated by commas (e.g., 'core,web')")
        print("Or press Enter for 'core' only:")

        selection = input("> ").strip()
        if selection:
            plugins_to_install = [p.strip() for p in selection.split(",")]
        else:
            plugins_to_install = ["core"]

        if "core" not in plugins_to_install:
            plugins_to_install.insert(0, "core")

    # Validate plugins
    for p in plugins_to_install:
        if p not in PLUGINS:
            print(f"Error: Unknown plugin '{p}'")
            list_plugins()
            sys.exit(1)

    print(f"\nInstalling plugins to: {target}")
    print("=" * 60)

    for plugin_key in plugins_to_install:
        plugin_info = PLUGINS[plugin_key]
        print(f"\n[{plugin_info['name']}]")

        if install_plugin(plugin_key, target):
            print(f"   Installed successfully")
        else:
            print(f"   FAILED")

    print("\n" + "=" * 60)
    print("Installation complete!")
    print("\nInstalled commands:")

    commands_dir = target / ".claude" / "commands"
    if commands_dir.exists():
        for cmd in sorted(commands_dir.glob("*.md")):
            if cmd.name != "POSTGRESQL_ARRAY_GUIDE.md":
                print(f"  /{cmd.stem}")

    print("\nNote: Restart Claude Code for hooks to take effect.")


if __name__ == "__main__":
    main()
