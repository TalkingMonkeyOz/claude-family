#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Install Git Hooks for Claude Family

Copies pre-commit hook to .git/hooks/ and makes it executable.
Run: python scripts/install_git_hooks.py
"""

import os
import sys
import shutil
import stat
from pathlib import Path

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def install_hook():
    """Install pre-commit hook"""
    project_root = Path(__file__).parent.parent
    hook_source = project_root / 'scripts' / 'pre-commit-hook.sh'
    hook_dest = project_root / '.git' / 'hooks' / 'pre-commit'

    # Check if source exists
    if not hook_source.exists():
        print(f"[XX] Hook source not found: {hook_source}")
        return False

    # Check if .git directory exists
    git_hooks_dir = hook_dest.parent
    if not git_hooks_dir.exists():
        print(f"[XX] Git hooks directory not found: {git_hooks_dir}")
        print("     Are you in a git repository?")
        return False

    # Backup existing hook if present
    if hook_dest.exists():
        backup = hook_dest.with_suffix('.backup')
        print(f"[>>] Backing up existing hook to: {backup.name}")
        shutil.copy2(hook_dest, backup)

    # Copy hook
    print(f"[>>] Installing pre-commit hook...")
    shutil.copy2(hook_source, hook_dest)

    # Make executable (Unix/Mac/Git Bash on Windows)
    try:
        current_permissions = os.stat(hook_dest).st_mode
        os.chmod(hook_dest, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"[OK] Hook installed and made executable")
    except Exception as e:
        print(f"[!!] Hook installed but couldn't make executable: {e}")
        print(f"     (This is normal on Windows - Git will still use the hook)")

    return True

def main():
    print("\n" + "="*60)
    print("Git Pre-Commit Hook Installer")
    print("="*60 + "\n")

    if install_hook():
        print("\n[OK] Installation complete!")
        print("\nThe pre-commit hook will now:")
        print("  - Check CLAUDE.md line count before each commit")
        print("  - Block commits if CLAUDE.md exceeds 250 lines")
        print("  - Show helpful error messages with fix suggestions")
        print("\nTo test: git add CLAUDE.md && git commit -m 'test'")
        return 0
    else:
        print("\n[XX] Installation failed")
        return 1

if __name__ == '__main__':
    exit(main())
