#!/usr/bin/env python3
"""
Import configuration files into the Claude database.

This script populates three tables:
1. claude.skills - from ~/.claude/skills/ and .claude/skills/
2. claude.instructions - from ~/.claude/instructions/*.instructions.md
3. claude.rules - from .claude/rules/*.md

Usage:
    python import_config_to_database.py

Environment:
    DATABASE_URL - PostgreSQL connection string (default: postgresql://localhost/ai_company_foundation)
"""

import os
import sys
import re
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

# Handle Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Default connection string - load from ai-workspace secure config
DEFAULT_CONN_STR = None
try:
    sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
    from config import POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
except ImportError:
    pass


class ConfigImporter:
    """Import config files into PostgreSQL."""

    CLAUDE_PROJECT_ID = "20b5627c-e72c-4501-8537-95b559731b59"

    def __init__(self, db_url: Optional[str] = None):
        """Initialize database connection."""
        self.db_url = db_url or os.getenv("DATABASE_URL", DEFAULT_CONN_STR)
        if not self.db_url:
            print("Error: No database connection string. Set DATABASE_URL or configure ai-workspace.")
            sys.exit(1)
        self.conn = None
        self.stats = {
            "skills_imported": 0,
            "instructions_imported": 0,
            "rules_imported": 0,
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

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List]:
        """Execute a query and return results."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
                self.conn.commit()
                return None
        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"✗ Query failed: {e}")
            print(f"  Query: {query}")
            raise

    def _read_file(self, path: str) -> str:
        """Read file content."""
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            print(f"✗ Failed to read {path}: {e}")
            return ""

    def _parse_yaml_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract YAML frontmatter from markdown file."""
        if not content.startswith("---"):
            return {}

        try:
            # Find closing ---
            lines = content.split('\n')
            end_idx = None
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    end_idx = i
                    break

            if end_idx is None:
                return {}

            fm_text = '\n'.join(lines[1:end_idx])
            return yaml.safe_load(fm_text) or {}
        except Exception as e:
            print(f"  Warning: Failed to parse frontmatter: {e}")
            return {}

    def import_skills(self):
        """Import skills from ~/.claude/skills/ (global) and .claude/skills/ (project)."""
        print("\n--- Importing Skills ---")

        # Global skills
        global_skills_dir = Path("C:/Users/johnd/.claude/skills/")
        if global_skills_dir.exists():
            self._import_skills_from_dir(global_skills_dir, scope="global", scope_ref=None)

        # Project skills
        project_skills_dir = Path("C:/Projects/claude-family/.claude/skills/")
        if project_skills_dir.exists():
            self._import_skills_from_dir(
                project_skills_dir,
                scope="project",
                scope_ref=self.CLAUDE_PROJECT_ID
            )

    def _import_skills_from_dir(self, skills_dir: Path, scope: str, scope_ref: Optional[str]):
        """Import skills from directory."""
        for skill_folder in sorted(skills_dir.iterdir()):
            if not skill_folder.is_dir():
                continue

            # Concatenate all .md files in folder as content
            skill_files = list(skill_folder.glob("*.md"))
            if not skill_files:
                continue

            # Read and concatenate content
            content_parts = []
            for skill_file in sorted(skill_files):
                content = self._read_file(str(skill_file))
                if content:
                    content_parts.append(content)

            if not content_parts:
                continue

            full_content = "\n\n---\n\n".join(content_parts)
            skill_name = skill_folder.name

            # Insert skill
            query = """
                INSERT INTO claude.skills
                (skill_id, name, scope, scope_ref, content, description, is_active, created_at, updated_at)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name, scope, scope_ref)
                DO UPDATE SET
                    content = EXCLUDED.content,
                    updated_at = EXCLUDED.updated_at;
            """

            try:
                with self.conn.cursor() as cur:
                    cur.execute(query, (
                        str(uuid.uuid4()),
                        skill_name,
                        scope,
                        scope_ref,
                        full_content,
                        None,  # description
                        True,  # is_active
                        datetime.utcnow(),
                        datetime.utcnow(),
                    ))
                self.conn.commit()
                self.stats["skills_imported"] += 1
                print(f"✓ Imported skill: {skill_name} ({scope})")
            except psycopg2.Error as e:
                self.conn.rollback()
                print(f"✗ Failed to import skill {skill_name}: {e}")

    def import_instructions(self):
        """Import instructions from ~/.claude/instructions/*.instructions.md"""
        print("\n--- Importing Instructions ---")

        instructions_dir = Path("C:/Users/johnd/.claude/instructions/")
        if not instructions_dir.exists():
            print("  (no global instructions directory)")
            return

        for instr_file in sorted(instructions_dir.glob("*.instructions.md")):
            content = self._read_file(str(instr_file))
            if not content:
                continue

            # Parse YAML frontmatter
            frontmatter = self._parse_yaml_frontmatter(content)
            applies_to = frontmatter.get("applyTo", "")

            # applies_to is NOT NULL - use a default if missing
            if not applies_to:
                # Extract from filename for fallback pattern
                instr_name_base = instr_file.stem.replace(".instructions", "")
                applies_to = f"**/*.{instr_name_base}"

            # Extract name from filename (e.g., a11y.instructions.md -> a11y)
            instr_name = instr_file.stem.replace(".instructions", "")

            # Insert instruction
            query = """
                INSERT INTO claude.instructions
                (instruction_id, name, scope, scope_ref, applies_to, content, priority, is_active, created_at, updated_at)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name, scope, scope_ref)
                DO UPDATE SET
                    applies_to = EXCLUDED.applies_to,
                    content = EXCLUDED.content,
                    updated_at = EXCLUDED.updated_at;
            """

            try:
                with self.conn.cursor() as cur:
                    cur.execute(query, (
                        str(uuid.uuid4()),
                        instr_name,
                        "global",
                        None,  # scope_ref
                        applies_to,
                        content,
                        10,  # priority (default)
                        True,  # is_active
                        datetime.utcnow(),
                        datetime.utcnow(),
                    ))
                self.conn.commit()
                self.stats["instructions_imported"] += 1
                print(f"✓ Imported instruction: {instr_name} (applies_to: {applies_to})")
            except psycopg2.Error as e:
                self.conn.rollback()
                print(f"✗ Failed to import instruction {instr_name}: {e}")

    def import_rules(self):
        """Import rules from .claude/rules/*.md"""
        print("\n--- Importing Rules ---")

        rules_dir = Path("C:/Projects/claude-family/.claude/rules/")
        if not rules_dir.exists():
            print("  (no project rules directory)")
            return

        for rule_file in sorted(rules_dir.glob("*.md")):
            content = self._read_file(str(rule_file))
            if not content:
                continue

            # Extract rule_type from filename (e.g., commit-rules.md -> commit)
            # Handle patterns like "commit-rules.md" -> "commit"
            match = re.match(r'^([a-z-]+?)(?:-rules)?\.md$', rule_file.name)
            rule_type = match.group(1) if match else rule_file.stem

            # Use filename without .md as rule name
            rule_name = rule_file.stem

            # Insert rule
            query = """
                INSERT INTO claude.rules
                (rule_id, name, scope, scope_ref, content, rule_type, is_active, created_at, updated_at)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name, scope, scope_ref)
                DO UPDATE SET
                    content = EXCLUDED.content,
                    rule_type = EXCLUDED.rule_type,
                    updated_at = EXCLUDED.updated_at;
            """

            try:
                with self.conn.cursor() as cur:
                    cur.execute(query, (
                        str(uuid.uuid4()),
                        rule_name,
                        "project",
                        self.CLAUDE_PROJECT_ID,
                        content,
                        rule_type,
                        True,  # is_active
                        datetime.utcnow(),
                        datetime.utcnow(),
                    ))
                self.conn.commit()
                self.stats["rules_imported"] += 1
                print(f"✓ Imported rule: {rule_name} (type: {rule_type})")
            except psycopg2.Error as e:
                self.conn.rollback()
                print(f"✗ Failed to import rule {rule_name}: {e}")

    def print_summary(self):
        """Print import summary."""
        print("\n" + "="*50)
        print("IMPORT SUMMARY")
        print("="*50)
        print(f"Skills imported:        {self.stats['skills_imported']}")
        print(f"Instructions imported:  {self.stats['instructions_imported']}")
        print(f"Rules imported:         {self.stats['rules_imported']}")
        print(f"Total:                  {sum(self.stats.values())}")
        print("="*50)


def main():
    """Main entry point."""
    print("Claude Config Import Tool")
    print("-" * 50)

    importer = ConfigImporter()

    try:
        importer.connect()
        importer.import_skills()
        importer.import_instructions()
        importer.import_rules()
        importer.print_summary()
        print("\n✓ Import complete!")
    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        sys.exit(1)
    finally:
        importer.close()


if __name__ == "__main__":
    main()
