#!/usr/bin/env python3
"""
Regenerate configuration files from the database.

Database is source of truth. This script writes DB content back to files
so Claude Code can read them.

TABLES:
- claude.profiles (source_type='global') → ~/.claude/CLAUDE.md
- claude.skills (scope='global') → ~/.claude/skills/{name}/skill.md
- claude.instructions (scope='global') → ~/.claude/instructions/{name}.instructions.md
- claude.rules (scope='global') → ~/.claude/rules/{name}.md

Usage:
    python regenerate_config_from_db.py --global-config
    python regenerate_config_from_db.py --project <project_id>
    python regenerate_config_from_db.py --type <skills|instructions|rules|claude-md>
    python regenerate_config_from_db.py --global-config --type skills
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

# Handle Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Load config from scripts/config.py
DEFAULT_CONN_STR = None
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import DATABASE_URI as _DB_URI, POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = _DB_URI
except ImportError:
    pass


class ConfigRegenerator:
    """Regenerate config files from PostgreSQL database."""

    CLAUDE_PROJECT_ID = "20b5627c-e72c-4501-8537-95b559731b59"

    def __init__(self, db_url: Optional[str] = None):
        """Initialize database connection."""
        self.db_url = db_url or os.getenv("DATABASE_URL", DEFAULT_CONN_STR)
        if not self.db_url:
            print("Error: No database connection string. Set DATABASE_URL or configure config.py.")
            sys.exit(1)
        self.conn = None
        self.stats = {
            "claude_md_written": 0,
            "skills_written": 0,
            "instructions_written": 0,
            "rules_written": 0,
            "directories_created": 0,
        }

    def connect(self):
        """Connect to database."""
        try:
            self.conn = psycopg2.connect(self.db_url)
            print(f"✓ Connected to database")
        except psycopg2.Error as e:
            print(f"✗ Database connection failed: {e}")
            sys.exit(1)

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict]]:
        """Execute a query and return results as list of dicts."""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
        except psycopg2.Error as e:
            print(f"✗ Query failed: {e}")
            print(f"  Query: {query}")
            raise

    def _ensure_dir(self, path: Path) -> bool:
        """Create directory if it doesn't exist. Returns True if created."""
        if path.exists():
            return False
        try:
            path.mkdir(parents=True, exist_ok=True)
            self.stats["directories_created"] += 1
            return True
        except Exception as e:
            print(f"✗ Failed to create directory {path}: {e}")
            raise

    def _write_file(self, path: Path, content: str) -> bool:
        """Write file with UTF-8 encoding. Returns True if successful."""
        try:
            # Ensure parent directory exists
            self._ensure_dir(path.parent)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"✗ Failed to write {path}: {e}")
            raise

    def regenerate_global_claude_md(self):
        """Write global CLAUDE.md from profiles table (source_type='global')."""
        print("\n--- Regenerating Global CLAUDE.md ---")

        query = """
            SELECT config->>'behavior' as content
            FROM claude.profiles
            WHERE source_type = 'global'
            AND is_active = true
            LIMIT 1;
        """

        results = self.execute_query(query)
        if not results or not results[0]['content']:
            print("  (no global profile found)")
            return

        content = results[0]['content']
        target_path = Path.home() / ".claude" / "CLAUDE.md"

        try:
            self._write_file(target_path, content)
            self.stats["claude_md_written"] += 1
            print(f"✓ Wrote CLAUDE.md ({len(content)} bytes)")
            print(f"  → {target_path}")
        except Exception as e:
            print(f"✗ Failed to write CLAUDE.md: {e}")

    def regenerate_skills(self, scope: str = 'global', scope_ref: Optional[str] = None):
        """Write skills from database to files."""
        print(f"\n--- Regenerating {scope.capitalize()} Skills ---")

        query = """
            SELECT name, content
            FROM claude.skills
            WHERE scope = %s
            AND scope_ref IS NOT DISTINCT FROM %s
            AND is_active = true
            ORDER BY name;
        """

        results = self.execute_query(query, (scope, scope_ref))
        if not results:
            print(f"  (no {scope} skills found)")
            return

        # Determine base path
        if scope == 'global':
            base_path = Path.home() / ".claude" / "skills"
        else:
            base_path = Path(".claude/skills")

        for row in results:
            skill_name = row['name']
            content = row['content']

            # Create skill directory
            skill_dir = base_path / skill_name
            self._ensure_dir(skill_dir)

            # Write skill.md
            skill_file = skill_dir / "skill.md"
            try:
                self._write_file(skill_file, content)
                self.stats["skills_written"] += 1
                print(f"✓ Wrote skill: {skill_name} ({len(content)} bytes)")
                print(f"  → {skill_file}")
            except Exception as e:
                print(f"✗ Failed to write skill {skill_name}: {e}")

    def regenerate_instructions(self, scope: str = 'global', scope_ref: Optional[str] = None):
        """Write instructions from database to files."""
        print(f"\n--- Regenerating {scope.capitalize()} Instructions ---")

        query = """
            SELECT name, content
            FROM claude.instructions
            WHERE scope = %s
            AND scope_ref IS NOT DISTINCT FROM %s
            AND is_active = true
            ORDER BY name;
        """

        results = self.execute_query(query, (scope, scope_ref))
        if not results:
            print(f"  (no {scope} instructions found)")
            return

        # Determine base path
        if scope == 'global':
            base_path = Path.home() / ".claude" / "instructions"
        else:
            base_path = Path(".claude/instructions")

        self._ensure_dir(base_path)

        for row in results:
            instr_name = row['name']
            content = row['content']

            # Write {name}.instructions.md
            instr_file = base_path / f"{instr_name}.instructions.md"
            try:
                self._write_file(instr_file, content)
                self.stats["instructions_written"] += 1
                print(f"✓ Wrote instruction: {instr_name} ({len(content)} bytes)")
                print(f"  → {instr_file}")
            except Exception as e:
                print(f"✗ Failed to write instruction {instr_name}: {e}")

    def regenerate_rules(self, scope: str = 'project', scope_ref: Optional[str] = None):
        """Write rules from database to files."""
        print(f"\n--- Regenerating {scope.capitalize()} Rules ---")

        query = """
            SELECT name, content
            FROM claude.rules
            WHERE scope = %s
            AND scope_ref IS NOT DISTINCT FROM %s
            AND is_active = true
            ORDER BY name;
        """

        results = self.execute_query(query, (scope, scope_ref))
        if not results:
            print(f"  (no {scope} rules found)")
            return

        # Determine base path
        if scope == 'global':
            base_path = Path.home() / ".claude" / "rules"
        else:
            base_path = Path(".claude/rules")

        self._ensure_dir(base_path)

        for row in results:
            rule_name = row['name']
            content = row['content']

            # Write {name}.md
            rule_file = base_path / f"{rule_name}.md"
            try:
                self._write_file(rule_file, content)
                self.stats["rules_written"] += 1
                print(f"✓ Wrote rule: {rule_name} ({len(content)} bytes)")
                print(f"  → {rule_file}")
            except Exception as e:
                print(f"✗ Failed to write rule {rule_name}: {e}")

    def regenerate_global_all(self):
        """Regenerate all global configuration."""
        print("="*60)
        print("REGENERATING GLOBAL CONFIGURATION FROM DATABASE")
        print("="*60)

        self.regenerate_global_claude_md()
        self.regenerate_skills(scope='global', scope_ref=None)
        self.regenerate_instructions(scope='global', scope_ref=None)
        self.regenerate_rules(scope='global', scope_ref=None)

    def regenerate_project_all(self, project_id: str):
        """Regenerate all project-specific configuration."""
        print("="*60)
        print(f"REGENERATING PROJECT CONFIGURATION FOR {project_id}")
        print("="*60)

        # Project doesn't have CLAUDE.md, only skills/instructions/rules
        self.regenerate_skills(scope='project', scope_ref=project_id)
        self.regenerate_instructions(scope='project', scope_ref=project_id)
        self.regenerate_rules(scope='project', scope_ref=project_id)

    def print_summary(self):
        """Print regeneration summary."""
        print("\n" + "="*60)
        print("REGENERATION SUMMARY")
        print("="*60)
        print(f"CLAUDE.md files written:    {self.stats['claude_md_written']}")
        print(f"Skills written:             {self.stats['skills_written']}")
        print(f"Instructions written:       {self.stats['instructions_written']}")
        print(f"Rules written:              {self.stats['rules_written']}")
        print(f"Directories created:        {self.stats['directories_created']}")
        print(f"Total files written:        {sum(v for k, v in self.stats.items() if 'written' in k)}")
        print("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Regenerate configuration files from database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python regenerate_config_from_db.py --global-config
  python regenerate_config_from_db.py --project 20b5627c-e72c-4501-8537-95b559731b59
  python regenerate_config_from_db.py --global-config --type skills
  python regenerate_config_from_db.py --global-config --type instructions
        """
    )

    parser.add_argument(
        '--global-config',
        action='store_true',
        dest='is_global',
        help='Regenerate all global configuration'
    )
    parser.add_argument(
        '--project',
        type=str,
        help='Regenerate project-specific configuration (provide project ID)'
    )
    parser.add_argument(
        '--type',
        choices=['skills', 'instructions', 'rules', 'claude-md'],
        help='Regenerate specific type only'
    )
    parser.add_argument(
        '--database-url',
        type=str,
        help='Database connection URL (optional, defaults to config or environment)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.is_global and not args.project:
        parser.print_help()
        print("\n✗ Error: Specify either --global-config or --project")
        sys.exit(1)

    print("Claude Config Regenerator")
    print("-" * 60)

    regenerator = ConfigRegenerator(db_url=args.database_url)

    try:
        regenerator.connect()

        if args.is_global:
            if args.type:
                # Specific type only
                if args.type == 'claude-md':
                    regenerator.regenerate_global_claude_md()
                elif args.type == 'skills':
                    regenerator.regenerate_skills(scope='global', scope_ref=None)
                elif args.type == 'instructions':
                    regenerator.regenerate_instructions(scope='global', scope_ref=None)
                elif args.type == 'rules':
                    regenerator.regenerate_rules(scope='global', scope_ref=None)
            else:
                # All global
                regenerator.regenerate_global_all()

        elif args.project:
            if args.type:
                # Specific type only for project
                if args.type == 'skills':
                    regenerator.regenerate_skills(scope='project', scope_ref=args.project)
                elif args.type == 'instructions':
                    regenerator.regenerate_instructions(scope='project', scope_ref=args.project)
                elif args.type == 'rules':
                    regenerator.regenerate_rules(scope='project', scope_ref=args.project)
                elif args.type == 'claude-md':
                    print("✗ Error: claude-md is global only")
                    sys.exit(1)
            else:
                # All project
                regenerator.regenerate_project_all(args.project)

        regenerator.print_summary()
        print("\n✓ Regeneration complete!")

    except Exception as e:
        print(f"\n✗ Regeneration failed: {e}")
        sys.exit(1)
    finally:
        regenerator.close()


if __name__ == "__main__":
    main()
