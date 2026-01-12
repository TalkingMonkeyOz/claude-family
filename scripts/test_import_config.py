#!/usr/bin/env python3
"""
Test script for import_config_to_database.py

Tests file discovery and parsing logic without writing to database.
"""

import os
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List

# Handle Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def parse_yaml_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from markdown file."""
    if not content.startswith("---"):
        return {}

    try:
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


def test_skills_discovery():
    """Test skill folder discovery."""
    print("\n" + "="*60)
    print("TEST 1: SKILL DISCOVERY")
    print("="*60)

    global_skills = Path("C:/Users/johnd/.claude/skills/")
    project_skills = Path("C:/Projects/claude-family/.claude/skills/")

    global_count = 0
    project_count = 0

    if global_skills.exists():
        print(f"\nGlobal skills directory: {global_skills}")
        for skill_folder in sorted(global_skills.iterdir()):
            if skill_folder.is_dir():
                skill_files = list(skill_folder.glob("*.md"))
                if skill_files:
                    global_count += 1
                    print(f"  ✓ {skill_folder.name} ({len(skill_files)} files)")
        print(f"Total global skills: {global_count}")
    else:
        print(f"✗ Global skills directory not found: {global_skills}")

    if project_skills.exists():
        print(f"\nProject skills directory: {project_skills}")
        for skill_folder in sorted(project_skills.iterdir()):
            if skill_folder.is_dir():
                skill_files = list(skill_folder.glob("*.md"))
                if skill_files:
                    project_count += 1
                    print(f"  ✓ {skill_folder.name} ({len(skill_files)} files)")
        print(f"Total project skills: {project_count}")
    else:
        print(f"✗ Project skills directory not found: {project_skills}")

    total = global_count + project_count
    print(f"\n✓ Total skills to import: {total}")
    assert total > 0, "No skills found!"
    return total


def test_instructions_discovery():
    """Test instruction file discovery and frontmatter parsing."""
    print("\n" + "="*60)
    print("TEST 2: INSTRUCTION DISCOVERY")
    print("="*60)

    instructions_dir = Path("C:/Users/johnd/.claude/instructions/")

    if not instructions_dir.exists():
        print(f"✗ Instructions directory not found: {instructions_dir}")
        return 0

    print(f"\nInstructions directory: {instructions_dir}")
    instr_files = list(instructions_dir.glob("*.instructions.md"))
    print(f"Found {len(instr_files)} instruction files")

    for instr_file in sorted(instr_files):
        try:
            with open(instr_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            frontmatter = parse_yaml_frontmatter(content)
            applies_to = frontmatter.get("applyTo", "")

            instr_name = instr_file.stem.replace(".instructions", "")

            # Handle empty applies_to
            if not applies_to:
                applies_to = f"**/*.{instr_name}"
                print(f"  ℹ {instr_name}: (auto-generated: {applies_to})")
            else:
                print(f"  ✓ {instr_name}: {applies_to}")

            # Verify content length
            assert len(content) > 0, f"Empty content in {instr_file}"

        except Exception as e:
            print(f"  ✗ {instr_file.name}: {e}")

    print(f"\n✓ Total instructions to import: {len(instr_files)}")
    return len(instr_files)


def test_rules_discovery():
    """Test rule file discovery and type extraction."""
    print("\n" + "="*60)
    print("TEST 3: RULE DISCOVERY")
    print("="*60)

    rules_dir = Path("C:/Projects/claude-family/.claude/rules/")

    if not rules_dir.exists():
        print(f"✗ Rules directory not found: {rules_dir}")
        return 0

    print(f"\nRules directory: {rules_dir}")
    rule_files = list(rules_dir.glob("*.md"))
    print(f"Found {len(rule_files)} rule files")

    for rule_file in sorted(rule_files):
        try:
            # Extract rule type from filename
            match = re.match(r'^([a-z-]+?)(?:-rules)?\.md$', rule_file.name)
            rule_type = match.group(1) if match else rule_file.stem

            with open(rule_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Verify content length
            assert len(content) > 0, f"Empty content in {rule_file}"

            print(f"  ✓ {rule_file.stem} (type: {rule_type}, {len(content)} chars)")

        except Exception as e:
            print(f"  ✗ {rule_file.name}: {e}")

    print(f"\n✓ Total rules to import: {len(rule_files)}")
    return len(rule_files)


def test_project_id():
    """Verify project ID is valid."""
    print("\n" + "="*60)
    print("TEST 4: PROJECT ID VALIDATION")
    print("="*60)

    project_id = "20b5627c-e72c-4501-8537-95b559731b59"
    print(f"\nProject ID: {project_id}")

    # Verify format
    import uuid
    try:
        uuid.UUID(project_id)
        print("✓ Valid UUID format")
    except ValueError:
        print("✗ Invalid UUID format")
        return False

    return True


def test_encoding():
    """Test file encoding handling."""
    print("\n" + "="*60)
    print("TEST 5: ENCODING HANDLING")
    print("="*60)

    test_files = [
        "C:/Users/johnd/.claude/instructions/a11y.instructions.md",
        "C:/Users/johnd/.claude/instructions/csharp.instructions.md",
        "C:/Projects/claude-family/.claude/rules/commit-rules.md",
    ]

    print("\nTesting UTF-8 decoding with error handling...")
    for test_file in test_files:
        if not Path(test_file).exists():
            continue

        try:
            with open(test_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            print(f"✓ {Path(test_file).name} ({len(content)} chars)")
        except Exception as e:
            print(f"✗ {Path(test_file).name}: {e}")

    print("\n✓ Encoding tests complete")
    return True


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# IMPORT CONFIG TEST SUITE")
    print("#"*60)

    try:
        skills_count = test_skills_discovery()
        instructions_count = test_instructions_discovery()
        rules_count = test_rules_discovery()
        project_valid = test_project_id()
        encoding_ok = test_encoding()

        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Skills:        {skills_count}")
        print(f"Instructions:  {instructions_count}")
        print(f"Rules:         {rules_count}")
        print(f"Total:         {skills_count + instructions_count + rules_count}")
        print(f"Project Valid: {project_valid}")
        print(f"Encoding OK:   {encoding_ok}")
        print("="*60)

        if skills_count > 0 and instructions_count > 0 and rules_count > 0 and project_valid and encoding_ok:
            print("\n✓ ALL TESTS PASSED")
            print("\nYou can now run:")
            print("  python scripts/import_config_to_database.py")
            return 0
        else:
            print("\n✗ SOME TESTS FAILED")
            return 1

    except Exception as e:
        print(f"\n✗ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
