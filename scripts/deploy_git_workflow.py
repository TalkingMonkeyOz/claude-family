#!/usr/bin/env python3
"""
Deploy Git Workflow to Claude Family Projects

Deploys:
- Git hooks (.githooks/)
- PR template (.github/PULL_REQUEST_TEMPLATE.md)
- Issue templates (.github/ISSUE_TEMPLATE/)

Usage:
    python scripts/deploy_git_workflow.py                    # Deploy to all projects
    python scripts/deploy_git_workflow.py --project nimbus   # Deploy to one project
    python scripts/deploy_git_workflow.py --dry-run          # Preview changes

Logs deployments to claude.git_workflow_deployments table.
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Database connection (optional - for logging)
DB_AVAILABLE = False
try:
    import psycopg2
    DB_AVAILABLE = True
except ImportError:
    pass

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TEMPLATES_DIR = PROJECT_ROOT / 'templates' / 'github'

# Embedded hook content (no need for source .githooks directory)
PREPARE_COMMIT_MSG_HOOK = '''#!/bin/bash
# Auto-prepend work item reference from branch name
COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2
if [ "$COMMIT_SOURCE" != "" ]; then exit 0; fi
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
if [ -z "$BRANCH" ]; then exit 0; fi
WORK_ITEM=""
if [[ $BRANCH =~ ^feature/(F[0-9]+) ]]; then WORK_ITEM="${BASH_REMATCH[1]}"; fi
if [[ $BRANCH =~ ^fix/(FB[0-9]+) ]]; then WORK_ITEM="${BASH_REMATCH[1]}"; fi
if [[ $BRANCH =~ ^task/(BT[0-9]+) ]]; then WORK_ITEM="${BASH_REMATCH[1]}"; fi
if [ -n "$WORK_ITEM" ]; then
    FIRST_LINE=$(head -n 1 "$COMMIT_MSG_FILE")
    if ! echo "$FIRST_LINE" | grep -qE "^\\[$WORK_ITEM\\]"; then
        TEMP_FILE=$(mktemp)
        echo "[$WORK_ITEM] $FIRST_LINE" > "$TEMP_FILE"
        tail -n +2 "$COMMIT_MSG_FILE" >> "$TEMP_FILE"
        mv "$TEMP_FILE" "$COMMIT_MSG_FILE"
    fi
fi
exit 0
'''

COMMIT_MSG_HOOK = '''#!/bin/bash
# Validate work item reference (soft enforcement)
COMMIT_MSG=$(cat "$1")
if ! echo "$COMMIT_MSG" | grep -qE '\\[(F|FB|BT)[0-9]+\\]'; then
    echo ""
    echo "=============================================="
    echo "NOTE: No work item reference in commit message"
    echo "=============================================="
    echo "Consider: feature/F1-desc, fix/FB1-desc branch naming"
    echo "=============================================="
fi
exit 0
'''

# Projects to deploy to (from database or fallback)
PROJECTS = [
    ("claude-family", r"C:\Projects\claude-family"),
    ("claude-manager-mui", r"C:\Projects\claude-manager-mui"),
    ("claude-family-manager-v2", r"C:\Projects\claude-family-manager-v2"),
    ("nimbus-mui", r"C:\Projects\nimbus-mui"),
    ("nimbus-import", r"C:\Projects\nimbus-import"),
    ("nimbus-user-loader", r"C:\Projects\nimbus-user-loader"),
    ("ATO-Tax-Agent", r"C:\Projects\ATO-Tax-Agent"),
    ("ATO-Infrastructure", r"C:\Projects\ATO-Infrastructure"),
    ("finance-mui", r"C:\Projects\finance-mui"),
    ("claude-desktop-config", r"C:\Projects\claude-desktop-config"),
]


def get_db_connection():
    """Get database connection for logging."""
    if not DB_AVAILABLE:
        return None
    try:
        return psycopg2.connect(
            host="localhost",
            database="ai_company_foundation",
            user="postgres",
            password=os.environ.get("POSTGRES_PASSWORD", "05OX79HNFCjQwhotDjVx")
        )
    except Exception as e:
        print(f"[WARN] Database connection failed: {e}")
        return None


def log_deployment(project_name: str, component: str, status: str, details: str = None):
    """Log deployment to database."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.git_workflow_deployments
            (project_name, component, status, details, deployed_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (project_name, component, status, details, datetime.now()))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        # Table might not exist yet - that's ok
        print(f"[DEBUG] Logging failed (table may not exist): {e}")
        conn.close()


def is_git_repo(path: Path) -> bool:
    """Check if path is a git repository."""
    return (path / '.git').is_dir()


def deploy_hooks(project_path: Path, dry_run: bool = False) -> bool:
    """Deploy git hooks to project using embedded content."""
    dest_hooks = project_path / '.githooks'

    if dry_run:
        print(f"  [DRY] Would create hooks in {dest_hooks}")
        return True

    # Create hooks directory
    dest_hooks.mkdir(exist_ok=True)

    # Write hook files
    (dest_hooks / 'prepare-commit-msg').write_text(PREPARE_COMMIT_MSG_HOOK, encoding='utf-8')
    (dest_hooks / 'commit-msg').write_text(COMMIT_MSG_HOOK, encoding='utf-8')

    # Configure git to use hooks
    try:
        subprocess.run(
            ['git', 'config', 'core.hooksPath', '.githooks'],
            cwd=project_path,
            check=True,
            capture_output=True
        )
        print(f"  [OK] Hooks deployed and configured")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [ERR] Failed to configure hooks: {e}")
        return False


def deploy_pr_template(project_path: Path, dry_run: bool = False) -> bool:
    """Deploy PR template to project."""
    source = TEMPLATES_DIR / 'PULL_REQUEST_TEMPLATE.md'
    if not source.exists():
        print(f"  [SKIP] No PR template source")
        return False

    dest_dir = project_path / '.github'
    dest = dest_dir / 'PULL_REQUEST_TEMPLATE.md'

    if dry_run:
        print(f"  [DRY] Would copy PR template to {dest}")
        return True

    dest_dir.mkdir(exist_ok=True)
    shutil.copy2(source, dest)
    print(f"  [OK] PR template deployed")
    return True


def deploy_issue_templates(project_path: Path, dry_run: bool = False) -> bool:
    """Deploy issue templates to project."""
    source_dir = TEMPLATES_DIR / 'ISSUE_TEMPLATE'
    if not source_dir.exists():
        print(f"  [SKIP] No issue templates source")
        return False

    dest_dir = project_path / '.github' / 'ISSUE_TEMPLATE'

    if dry_run:
        print(f"  [DRY] Would copy issue templates to {dest_dir}")
        return True

    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for template in source_dir.glob('*.md'):
        shutil.copy2(template, dest_dir / template.name)

    print(f"  [OK] Issue templates deployed ({len(list(source_dir.glob('*.md')))} templates)")
    return True


def deploy_to_project(project_name: str, project_path: str, dry_run: bool = False) -> dict:
    """Deploy all git workflow components to a project."""
    path = Path(project_path)
    results = {
        'hooks': False,
        'pr_template': False,
        'issue_templates': False,
    }

    print(f"\n{'='*60}")
    print(f"Deploying to: {project_name}")
    print(f"Path: {project_path}")
    print(f"{'='*60}")

    if not path.exists():
        print(f"  [SKIP] Project path does not exist")
        return results

    if not is_git_repo(path):
        print(f"  [SKIP] Not a git repository")
        return results

    # Deploy each component
    results['hooks'] = deploy_hooks(path, dry_run)
    results['pr_template'] = deploy_pr_template(path, dry_run)
    results['issue_templates'] = deploy_issue_templates(path, dry_run)

    # Log to database
    if not dry_run:
        for component, success in results.items():
            status = 'success' if success else 'skipped'
            log_deployment(project_name, component, status)

    return results


def main():
    parser = argparse.ArgumentParser(description='Deploy Git Workflow to Claude Projects')
    parser.add_argument('--project', '-p', help='Deploy to specific project only')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Preview changes without applying')
    parser.add_argument('--list', '-l', action='store_true', help='List projects and exit')
    args = parser.parse_args()

    print("\n" + "="*60)
    print("Git Workflow Deployment")
    print("="*60)
    print(f"Templates source: {TEMPLATES_DIR}")
    print(f"Hooks: embedded in script")
    if args.dry_run:
        print("[DRY RUN MODE - No changes will be made]")

    if args.list:
        print("\nProjects:")
        for name, path in PROJECTS:
            exists = Path(path).exists()
            git = is_git_repo(Path(path)) if exists else False
            status = "OK" if git else ("no git" if exists else "missing")
            print(f"  {name}: [{status}]")
        return 0

    # Filter to specific project if requested
    projects = PROJECTS
    if args.project:
        projects = [(n, p) for n, p in PROJECTS if args.project.lower() in n.lower()]
        if not projects:
            print(f"\n[ERR] No project matching '{args.project}'")
            return 1

    # Deploy to each project
    total_results = {'hooks': 0, 'pr_template': 0, 'issue_templates': 0}
    for project_name, project_path in projects:
        results = deploy_to_project(project_name, project_path, args.dry_run)
        for key, success in results.items():
            if success:
                total_results[key] += 1

    # Summary
    print("\n" + "="*60)
    print("DEPLOYMENT SUMMARY")
    print("="*60)
    print(f"Projects processed: {len(projects)}")
    print(f"Hooks deployed: {total_results['hooks']}")
    print(f"PR templates deployed: {total_results['pr_template']}")
    print(f"Issue templates deployed: {total_results['issue_templates']}")

    if args.dry_run:
        print("\n[DRY RUN] No changes were made. Run without --dry-run to apply.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
