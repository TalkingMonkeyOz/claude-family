#!/usr/bin/env python3
"""
Project Scaffolding Script - Creates new projects with proper structure

Creates a new project with:
- CLAUDE.md from type-specific template
- README.md from template
- .docs-manifest.json for doc tracking
- Git initialization
- Database registration

Usage:
    python create_project.py <project-name> <project-type>
    python create_project.py my-app web-app
    python create_project.py my-tool python-tool --dry-run

Project Types:
    infrastructure  - Config/scripts projects
    web-app         - Web applications (React, Next.js, etc.)
    python-tool     - Python utilities and tools
    csharp-desktop  - C# desktop applications
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Database imports
DB_AVAILABLE = False
try:
    import psycopg
    from psycopg.rows import dict_row
    DB_AVAILABLE = True
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        DB_AVAILABLE = True
        PSYCOPG_VERSION = 2
    except ImportError:
        DB_AVAILABLE = False


# Configuration
PROJECTS_ROOT = Path("C:/Projects")
TEMPLATES_ROOT = Path(__file__).parent.parent / "templates"
WORKSPACES_FILE = Path(__file__).parent.parent / "workspaces.json"

PROJECT_TYPES = ['infrastructure', 'web-app', 'python-tool', 'csharp-desktop']


def get_db_connection():
    """Get PostgreSQL connection."""
    conn_str = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation'
    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(conn_str, row_factory=dict_row)
        else:
            return psycopg.connect(conn_str, cursor_factory=RealDictCursor)
    except:
        return None


def render_template(content: str, variables: dict) -> str:
    """Replace {{VARIABLE}} placeholders with values."""
    result = content
    for key, value in variables.items():
        result = result.replace(f'{{{{{key}}}}}', str(value))
    return result


def create_project_structure(project_path: Path, project_type: str):
    """Create base project directory structure."""
    dirs_to_create = ['docs']

    if project_type == 'infrastructure':
        dirs_to_create.extend(['scripts', 'configs', '.claude/commands'])
    elif project_type == 'web-app':
        dirs_to_create.extend(['src/components', 'src/pages', 'src/styles', 'src/utils', 'public', 'tests'])
    elif project_type == 'python-tool':
        project_snake = project_path.name.replace('-', '_')
        dirs_to_create.extend([f'src/{project_snake}', 'tests'])
    elif project_type == 'csharp-desktop':
        dirs_to_create.extend([f'src/{project_path.name}', f'tests/{project_path.name}.Tests'])

    for dir_name in dirs_to_create:
        (project_path / dir_name).mkdir(parents=True, exist_ok=True)


def copy_template(template_path: Path, dest_path: Path, variables: dict):
    """Copy and render a template file."""
    if template_path.exists():
        content = template_path.read_text(encoding='utf-8')
        rendered = render_template(content, variables)
        dest_path.write_text(rendered, encoding='utf-8')
        return True
    return False


def register_in_database(project_name: str, project_type: str, project_path: Path) -> bool:
    """Register project in claude.projects table."""
    if not DB_AVAILABLE:
        print("  [SKIP] Database not available")
        return False

    conn = get_db_connection()
    if not conn:
        print("  [SKIP] Could not connect to database")
        return False

    try:
        cur = conn.cursor()

        # Check if already exists
        cur.execute("""
            SELECT project_id FROM claude.projects
            WHERE project_name = %s
        """, (project_name,))

        if cur.fetchone():
            print(f"  [EXISTS] Project already in database")
            cur.close()
            conn.close()
            return True

        # Insert new project
        cur.execute("""
            INSERT INTO claude.projects (project_name, project_type, status, file_path)
            VALUES (%s, %s, 'active', %s)
            RETURNING project_id
        """, (project_name, project_type, str(project_path)))

        result = cur.fetchone()
        project_id = result['project_id'] if isinstance(result, dict) else result[0]

        conn.commit()
        cur.close()
        conn.close()

        print(f"  [DB] Registered with ID: {project_id}")
        return True

    except Exception as e:
        print(f"  [ERROR] Database registration failed: {e}")
        return False


def add_to_workspaces(project_name: str, project_path: Path) -> bool:
    """Add project to workspaces.json."""
    try:
        workspaces = {}
        if WORKSPACES_FILE.exists():
            workspaces = json.loads(WORKSPACES_FILE.read_text(encoding='utf-8'))

        if project_name in workspaces:
            print(f"  [EXISTS] Already in workspaces.json")
            return True

        workspaces[project_name] = {
            "path": str(project_path),
            "added": datetime.now().strftime('%Y-%m-%d')
        }

        WORKSPACES_FILE.write_text(
            json.dumps(workspaces, indent=2),
            encoding='utf-8'
        )

        print(f"  [WORKSPACES] Added to workspaces.json")
        return True

    except Exception as e:
        print(f"  [ERROR] Failed to update workspaces.json: {e}")
        return False


def git_init(project_path: Path) -> bool:
    """Initialize git repository."""
    try:
        result = subprocess.run(
            ['git', 'init'],
            cwd=project_path,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Create .gitignore
            gitignore_content = """# Dependencies
node_modules/
venv/
.venv/
__pycache__/
*.pyc

# Build
dist/
build/
*.egg-info/
bin/
obj/

# IDE
.idea/
.vscode/
*.suo
*.user

# OS
.DS_Store
Thumbs.db

# Env
.env
.env.local
*.local.json

# Logs
*.log
logs/
"""
            (project_path / '.gitignore').write_text(gitignore_content, encoding='utf-8')

            # Initial commit
            subprocess.run(['git', 'add', '.'], cwd=project_path, capture_output=True)
            subprocess.run(
                ['git', 'commit', '-m', 'Initial project scaffold'],
                cwd=project_path,
                capture_output=True
            )

            print(f"  [GIT] Repository initialized")
            return True
        else:
            print(f"  [ERROR] Git init failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"  [ERROR] Git init failed: {e}")
        return False


def create_project(project_name: str, project_type: str, dry_run: bool = False):
    """Create a new project with all scaffolding."""

    project_path = PROJECTS_ROOT / project_name
    today = datetime.now().strftime('%Y-%m-%d')
    project_snake = project_name.replace('-', '_')

    # Template variables
    variables = {
        'PROJECT_NAME': project_name,
        'PROJECT_NAME_SNAKE': project_snake,
        'PROJECT_TYPE': project_type.replace('-', ' ').title(),
        'PROJECT_PATH': str(project_path),
        'CREATED_DATE': today,
        'BUILD_COMMAND': 'npm run build' if project_type == 'web-app' else 'dotnet build' if project_type == 'csharp-desktop' else 'python -m build' if project_type == 'python-tool' else '# No build required',
        'TEST_COMMAND': 'npm test' if project_type == 'web-app' else 'dotnet test' if project_type == 'csharp-desktop' else 'pytest' if project_type == 'python-tool' else '# No tests',
        'RUN_COMMAND': 'npm run dev' if project_type == 'web-app' else 'dotnet run' if project_type == 'csharp-desktop' else f'python -m {project_snake}' if project_type == 'python-tool' else '# Run scripts directly',
    }

    print("=" * 60)
    print(f"Creating Project: {project_name}")
    print(f"Type: {project_type}")
    print(f"Path: {project_path}")
    print("=" * 60)

    if dry_run:
        print("\n[DRY-RUN MODE - No changes will be made]\n")

    # Check if project already exists
    if project_path.exists():
        print(f"\n[ERROR] Project directory already exists: {project_path}")
        sys.exit(1)

    # Step 1: Create directory structure
    print("\n1. Creating directory structure...")
    if not dry_run:
        project_path.mkdir(parents=True, exist_ok=True)
        create_project_structure(project_path, project_type)
    print(f"  [DIR] Created {project_path}")

    # Step 2: Copy CLAUDE.md template
    print("\n2. Creating CLAUDE.md...")
    type_template = TEMPLATES_ROOT / "project-types" / project_type / "CLAUDE.md"
    generic_template = TEMPLATES_ROOT / "CLAUDE.template.md"

    template_to_use = type_template if type_template.exists() else generic_template
    if not dry_run:
        copy_template(template_to_use, project_path / "CLAUDE.md", variables)
    print(f"  [FILE] CLAUDE.md from {template_to_use.name}")

    # Step 3: Copy README.md template
    print("\n3. Creating README.md...")
    readme_template = TEMPLATES_ROOT / "README.template.md"
    if not dry_run:
        copy_template(readme_template, project_path / "README.md", variables)
    print(f"  [FILE] README.md")

    # Step 4: Create .docs-manifest.json
    print("\n4. Creating .docs-manifest.json...")
    manifest_template = TEMPLATES_ROOT / ".docs-manifest.template.json"
    if not dry_run:
        copy_template(manifest_template, project_path / ".docs-manifest.json", variables)
    print(f"  [FILE] .docs-manifest.json")

    # Step 5: Initialize git
    print("\n5. Initializing git repository...")
    if not dry_run:
        git_init(project_path)
    else:
        print("  [DRY-RUN] Would initialize git")

    # Step 6: Register in database
    print("\n6. Registering in database...")
    if not dry_run:
        register_in_database(project_name, project_type, project_path)
    else:
        print("  [DRY-RUN] Would register in claude.projects")

    # Step 7: Add to workspaces.json
    print("\n7. Adding to workspaces.json...")
    if not dry_run:
        add_to_workspaces(project_name, project_path)
    else:
        print("  [DRY-RUN] Would add to workspaces.json")

    print("\n" + "=" * 60)
    print("Project created successfully!")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"  cd {project_path}")
    print(f"  code .  # Open in VS Code")
    print(f"  # Start coding!")


def main():
    parser = argparse.ArgumentParser(
        description='Create a new project with proper scaffolding',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python create_project.py my-api web-app
    python create_project.py data-processor python-tool
    python create_project.py file-manager csharp-desktop
    python create_project.py shared-configs infrastructure --dry-run
        """
    )
    parser.add_argument('name', help='Project name (lowercase, hyphens)')
    parser.add_argument('type', choices=PROJECT_TYPES, help='Project type')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Preview without creating')

    args = parser.parse_args()

    # Validate project name
    if not args.name.replace('-', '').replace('_', '').isalnum():
        print("[ERROR] Project name should only contain letters, numbers, hyphens, and underscores")
        sys.exit(1)

    create_project(args.name, args.type, args.dry_run)


if __name__ == "__main__":
    main()
