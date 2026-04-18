#!/usr/bin/env python3
"""
sync_project.py - Unified project configuration deployment

Replaces: generate_project_settings.py, generate_mcp_config.py, deploy_project_configs.py,
          shared folder copy operations.

Database is source of truth. This script projects DB state into Claude Code's expected
file locations. Uses 3-layer merge: config_templates -> project_type_configs ->
workspaces.startup_config.

Called from:
  - start-claude.bat (on every project launch)
  - SessionStart hook (self-healing)
  - Manual: python scripts/sync_project.py [project-path]

Flags:
  --dry-run         Show what would change without writing files
  --component       Deploy only one component: settings, mcp, skills, commands, rules, agents, claude_md, global_claude_md
  --no-interactive  Skip user prompts (for hook/automated calls)
  [path-or-name]    Project path or project name (defaults to cwd)
"""

import argparse
import hashlib
import json
import logging
import os
import platform
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure scripts/ dir is on path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, setup_hook_logging

logger = setup_hook_logging("sync_project")

# ---------------------------------------------------------------------------
# Valid Claude Code hook event types (as of v2.1.113, 2026-04-18)
# ---------------------------------------------------------------------------
VALID_HOOK_TYPES = {
    "PreToolUse", "PostToolUse", "PostToolUseFailure",
    "UserPromptSubmit", "PermissionRequest", "PermissionDenied",
    "SessionStart", "SessionEnd",
    "Stop", "StopFailure", "SubagentStart", "SubagentStop",
    "PreCompact", "PostCompact", "Notification",
    "InstructionsLoaded", "TaskCompleted", "TaskCreated",
    "CwdChanged", "FileChanged",
    "ConfigChange", "TeammateIdle", "Elicitation", "ElicitationResult",
    "WorktreeCreate", "WorktreeRemove",
}

# Agents source directory (global ~/.claude/agents/)
GLOBAL_AGENTS_DIR = Path.home() / ".claude" / "agents"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row) -> Dict:
    """Normalize a DB row to a plain dict for both psycopg v2 and v3."""
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    # psycopg2 RealDictRow supports dict() directly; fallback for anything else
    try:
        return dict(row)
    except Exception:
        return {}


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Recursive dict merge. override wins for scalars; lists are deduped and appended."""
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            existing_json = {
                json.dumps(item, sort_keys=True)
                for item in result[key]
                if isinstance(item, dict)
            }
            for item in value:
                if isinstance(item, dict):
                    item_json = json.dumps(item, sort_keys=True)
                    if item_json not in existing_json:
                        result[key].append(item)
                        existing_json.add(item_json)
                else:
                    if item not in result[key]:
                        result[key].append(item)
        else:
            result[key] = value
    return result


def validate_hooks(hooks_config: Dict) -> Dict:
    """Remove unrecognised hook event types and warn."""
    if not hooks_config:
        return hooks_config
    invalid = set(hooks_config.keys()) - VALID_HOOK_TYPES
    if invalid:
        logger.warning("Removing invalid hook types: %s", invalid)
        for key in invalid:
            del hooks_config[key]
    return hooks_config


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically via a .tmp sibling file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


# ---------------------------------------------------------------------------
# npx → node resolution (adapted from generate_mcp_config.py)
# ---------------------------------------------------------------------------

def _get_node_path() -> str:
    if platform.system() == "Windows":
        for candidate in [
            Path(os.environ.get("ProgramFiles", "")) / "nodejs" / "node.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "fnm_multishells" / "node.exe",
        ]:
            if candidate.exists():
                return str(candidate)
    return "node"


def _find_global_npm_entry_point(package_name: str) -> Optional[str]:
    npm_prefix = os.environ.get("APPDATA", "")
    if not npm_prefix:
        return None
    global_modules = Path(npm_prefix) / "npm" / "node_modules"
    pkg_dir = global_modules / package_name.replace("/", os.sep)
    if not pkg_dir.exists():
        return None
    pkg_json = pkg_dir / "package.json"
    if not pkg_json.exists():
        return None
    try:
        pkg_data = json.loads(pkg_json.read_text(encoding="utf-8"))
        bin_entry = pkg_data.get("bin", {})
        if isinstance(bin_entry, str):
            entry = bin_entry
        elif isinstance(bin_entry, dict):
            entry = next(iter(bin_entry.values()), None)
        else:
            entry = None
        if not entry:
            entry = pkg_data.get("main")
        if entry:
            full_path = pkg_dir / entry
            if full_path.exists():
                return str(full_path.resolve())
    except Exception as exc:
        logger.debug("Failed to read package.json for %s: %s", package_name, exc)
    return None


def resolve_server_command(server_name: str, server_config: Dict) -> Dict:
    """Resolve npx commands to direct node paths where possible (eliminates cmd.exe shim)."""
    command = server_config.get("command", "")
    args = server_config.get("args", [])

    is_cmd_wrapped = command == "cmd" and len(args) >= 3 and args[0] == "/c" and args[1] == "npx"
    is_raw_npx = command == "npx"

    if not is_raw_npx and not is_cmd_wrapped:
        return server_config

    npx_args = args[2:] if is_cmd_wrapped else list(args)

    package_name: Optional[str] = None
    extra_args: List[str] = []
    for arg in npx_args:
        if arg == "-y":
            continue
        elif package_name is None and not arg.startswith("-"):
            package_name = arg
        else:
            extra_args.append(arg)

    if not package_name:
        logger.warning("Could not determine package name for server '%s'", server_name)
        return server_config

    # Strip @version suffix for lookup
    lookup_name = package_name.split("@latest")[0]
    if lookup_name.startswith("@") and "@" in lookup_name[1:]:
        lookup_name = "@" + lookup_name[1:].split("@", 1)[0]

    entry_point = _find_global_npm_entry_point(lookup_name)
    if entry_point:
        result: Dict = {
            "type": server_config.get("type", "stdio"),
            "command": _get_node_path(),
            "args": [entry_point] + extra_args,
        }
        if "env" in server_config:
            result["env"] = server_config["env"]
        logger.info("Resolved %s: npx %s -> node %s", server_name, package_name, entry_point)
        return result

    # Fallback: wrap with cmd /c npx on Windows for raw npx commands
    if platform.system() == "Windows" and is_raw_npx:
        has_dash_y = "-y" in args
        result = {
            "type": server_config.get("type", "stdio"),
            "command": "cmd",
            "args": ["/c", "npx"] + ([] if has_dash_y else ["-y"]) + args,
        }
        if "env" in server_config:
            result["env"] = server_config["env"]
        logger.info("Fallback cmd wrapper for %s (not globally installed)", server_name)
        return result

    return server_config


# ---------------------------------------------------------------------------
# DB query functions
# ---------------------------------------------------------------------------

def get_project_info(conn, project_path: str) -> Optional[Dict]:
    """Query claude.workspaces for project info by path."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT project_name, project_type, startup_config, project_id::text
            FROM claude.workspaces
            WHERE project_path = %s AND is_active = true
            """,
            (project_path,),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None
    except Exception as exc:
        logger.error("get_project_info failed: %s", exc)
        return None


def get_project_info_by_name(conn, project_name: str) -> Optional[Dict]:
    """Query claude.workspaces for project info by name (fallback when path not found)."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT project_name, project_type, startup_config, project_path, project_id::text
            FROM claude.workspaces
            WHERE project_name = %s AND is_active = true
            """,
            (project_name,),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None
    except Exception as exc:
        logger.error("get_project_info_by_name failed: %s", exc)
        return None


def get_base_template(conn) -> Optional[Dict]:
    """Get hooks-base config from claude.config_templates."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT content FROM claude.config_templates WHERE template_name = 'hooks-base'"
        )
        row = cur.fetchone()
        if row:
            data = _row_to_dict(row)
            return data.get("content")
        return None
    except Exception as exc:
        logger.error("get_base_template failed: %s", exc)
        return None


def get_type_defaults(conn, project_type: str) -> Optional[Dict]:
    """Get project type defaults from claude.project_type_configs."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT default_mcp_servers, default_skills, default_instructions
            FROM claude.project_type_configs
            WHERE project_type = %s
            """,
            (project_type,),
        )
        row = cur.fetchone()
        if row:
            data = _row_to_dict(row)
            return {
                "mcp_servers": data.get("default_mcp_servers") or [],
                "skills": data.get("default_skills") or [],
                "instructions": data.get("default_instructions") or [],
            }
        return None
    except Exception as exc:
        logger.error("get_type_defaults failed: %s", exc)
        return None


def get_mcp_templates(conn) -> Dict[str, Dict]:
    """Load all mcp-* templates from claude.config_templates."""
    templates: Dict[str, Dict] = {}
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT template_name, content FROM claude.config_templates WHERE template_name LIKE 'mcp-%'"
        )
        for row in cur.fetchall():
            data = _row_to_dict(row)
            name = data.get("template_name", "")
            content = data.get("content") or {}
            # Strip the 'mcp-' prefix to get the server name key
            server_key = name[4:] if name.startswith("mcp-") else name
            templates[server_key] = content
    except Exception as exc:
        logger.error("get_mcp_templates failed: %s", exc)
    return templates


def get_scoped_skills(conn, project_type: str, project_name: str, project_id: str = "") -> List[Dict]:
    """Query skills scoped to global, this project type, or this project (by name or id)."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, content, scope, scope_ref, description, file_pattern
            FROM claude.skills
            WHERE is_active = true
              AND (
                scope = 'global'
                OR (scope = 'project_type' AND scope_ref = %s)
                OR (scope = 'project' AND (scope_ref = %s OR scope_ref = %s))
              )
            """,
            (project_type, project_name, project_id),
        )
        return [_row_to_dict(row) for row in cur.fetchall()]
    except Exception as exc:
        logger.error("get_scoped_skills failed: %s", exc)
        return []


def get_scoped_rules(conn, project_type: str, project_name: str, project_id: str = "") -> List[Dict]:
    """Query rules scoped to global, this project type, or this project (by name or id)."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, content, scope, scope_ref
            FROM claude.rules
            WHERE is_active = true
              AND (
                scope = 'global'
                OR (scope = 'project_type' AND scope_ref = %s)
                OR (scope = 'project' AND (scope_ref = %s OR scope_ref = %s))
              )
            """,
            (project_type, project_name, project_id),
        )
        return [_row_to_dict(row) for row in cur.fetchall()]
    except Exception as exc:
        logger.error("get_scoped_rules failed: %s", exc)
        return []


def get_claude_md_profile(conn, project_name: str) -> Optional[Dict]:
    """Query claude.profiles for CLAUDE.md content."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT config FROM claude.profiles
            WHERE name = %s AND is_active = true
            """,
            (project_name,),
        )
        row = cur.fetchone()
        if row:
            data = _row_to_dict(row)
            return data.get("config")
        return None
    except Exception as exc:
        logger.error("get_claude_md_profile failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Deployment functions
# ---------------------------------------------------------------------------

class DeployResult:
    """Track per-component deployment outcome."""

    def __init__(self, component: str):
        self.component = component
        self.status = "SKIP"   # OK | SKIP | WARN | FAIL
        self.detail = ""

    def ok(self, detail: str = "") -> "DeployResult":
        self.status = "OK"
        self.detail = detail
        return self

    def skip(self, detail: str = "") -> "DeployResult":
        self.status = "SKIP"
        self.detail = detail
        return self

    def warn(self, detail: str = "") -> "DeployResult":
        self.status = "WARN"
        self.detail = detail
        return self

    def fail(self, detail: str = "") -> "DeployResult":
        self.status = "FAIL"
        self.detail = detail
        return self

    def __str__(self) -> str:
        icon = {"OK": "[OK]", "SKIP": "[SKIP]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[self.status]
        base = f"  {icon} {self.component}"
        return f"{base}: {self.detail}" if self.detail else base


def deploy_settings(
    conn,
    project_path: str,
    project_info: Dict,
    *,
    dry_run: bool = False,
) -> DeployResult:
    """Generate .claude/settings.local.json using 3-layer deep merge."""
    result = DeployResult("settings.local.json")
    project_name = project_info.get("project_name", "")
    project_type = project_info.get("project_type", "infrastructure")

    # Layer 1: base template
    base = get_base_template(conn) or {}

    # Layer 2: project type defaults (only settings-relevant keys)
    type_defaults = get_type_defaults(conn, project_type) or {}
    # project_type_configs contributes skill/instruction lists to settings
    type_layer: Dict = {}
    if type_defaults.get("skills"):
        type_layer["skills"] = type_defaults["skills"]
    if type_defaults.get("instructions"):
        type_layer["instructions"] = type_defaults["instructions"]

    # Layer 3: workspace startup_config
    startup = project_info.get("startup_config") or {}

    merged = deep_merge(base, type_layer)
    merged = deep_merge(merged, startup)

    # Preserve existing permissions block
    settings_path = Path(project_path) / ".claude" / "settings.local.json"
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text(encoding="utf-8"))
            if "permissions" in existing:
                merged["permissions"] = existing["permissions"]
        except Exception as exc:
            logger.warning("Could not read existing settings.local.json: %s", exc)

    # Ensure permissions structure
    if "permissions" not in merged:
        merged["permissions"] = {"allow": [], "deny": [], "ask": []}

    # Validate hooks
    if "hooks" in merged:
        merged["hooks"] = validate_hooks(merged["hooks"])

    hook_count = sum(len(v) for v in merged.get("hooks", {}).values())
    hook_types = len(merged.get("hooks", {}))
    detail = f"{hook_types} hook types, {hook_count} handlers"

    if dry_run:
        return result.ok(f"[dry-run] would write: {detail}")

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _atomic_write(settings_path, json.dumps(merged, indent=2, ensure_ascii=False))

        # Remove legacy hooks.json if it exists
        legacy = settings_path.parent / "hooks.json"
        if legacy.exists():
            legacy.unlink()
            logger.info("Removed legacy hooks.json (hooks now in settings.local.json)")

        logger.info("Wrote settings.local.json for %s (%s)", project_name, detail)
        return result.ok(detail)
    except Exception as exc:
        logger.error("deploy_settings write failed: %s", exc)
        return result.fail(str(exc))


def deploy_mcp(
    conn,
    project_path: str,
    project_info: Dict,
    *,
    dry_run: bool = False,
) -> DeployResult:
    """Generate .mcp.json using 3-layer merge with npx resolution."""
    result = DeployResult(".mcp.json")
    project_name = project_info.get("project_name", "")
    project_type = project_info.get("project_type", "infrastructure")
    startup = project_info.get("startup_config") or {}

    # Layer 1+2: type defaults filter which templates to include
    type_defaults = get_type_defaults(conn, project_type) or {}
    default_servers: List[str] = type_defaults.get("mcp_servers") or []

    all_templates = get_mcp_templates(conn)

    merged_configs: Dict[str, Dict] = {}
    for server_name in default_servers:
        tmpl = all_templates.get(server_name)
        if tmpl:
            merged_configs[server_name] = dict(tmpl)
            logger.debug("Layer 1+2: Added MCP server '%s' from template", server_name)
        else:
            logger.warning("No mcp-%s template found in config_templates", server_name)

    # Layer 3: workspace mcp_configs overlay
    workspace_mcp: Dict = startup.get("mcp_configs") or {}
    for server_name, server_cfg in workspace_mcp.items():
        merged_configs[server_name] = dict(server_cfg)
        logger.debug("Layer 3: Added/overrode MCP server '%s' from workspace config", server_name)

    # Apply enabledMcpjsonServers filter to workspace-specific servers only
    enabled_filter: List[str] = startup.get("enabledMcpjsonServers") or []
    if enabled_filter and workspace_mcp:
        for ws_name in list(merged_configs.keys()):
            if ws_name in workspace_mcp and ws_name not in enabled_filter:
                del merged_configs[ws_name]
                logger.info("Filtered workspace server '%s' (not in enabledMcpjsonServers)", ws_name)

    if not merged_configs:
        return result.skip("no MCP servers configured")

    # Resolve npx -> node and ensure type field
    resolved: Dict[str, Dict] = {}
    for server_name, server_cfg in merged_configs.items():
        cfg = resolve_server_command(server_name, deepcopy(server_cfg))
        if "type" not in cfg:
            cfg["type"] = "stdio"
        resolved[server_name] = cfg

    mcp_output = {"mcpServers": resolved}
    detail = f"{len(resolved)} servers: {', '.join(resolved.keys())}"

    if dry_run:
        return result.ok(f"[dry-run] would write: {detail}")

    mcp_path = Path(project_path) / ".mcp.json"
    try:
        _atomic_write(mcp_path, json.dumps(mcp_output, indent=2, ensure_ascii=False))
        logger.info("Wrote .mcp.json for %s (%s)", project_name, detail)
        return result.ok(detail)
    except Exception as exc:
        logger.error("deploy_mcp write failed: %s", exc)
        return result.fail(str(exc))


def inject_paths_frontmatter(content: str, file_pattern: Optional[str]) -> str:
    """Inject `paths:` into YAML frontmatter from DB file_pattern column (v2.1.90+ skill scoping).

    If file_pattern is empty or content already has `paths:`, returns content unchanged.
    Otherwise appends `paths: "<pattern>"` inside the frontmatter block.
    """
    if not file_pattern:
        return content
    if not content.startswith("---\n"):
        return content
    end_idx = content.find("\n---\n", 4)
    if end_idx == -1:
        return content
    frontmatter = content[4:end_idx]
    rest = content[end_idx + 5:]
    # Already has a paths: line? leave alone.
    for line in frontmatter.splitlines():
        if line.strip().startswith("paths:"):
            return content
    # Quote if pattern has special YAML chars
    needs_quote = any(c in file_pattern for c in ":*|{}[],&")
    value = f'"{file_pattern}"' if needs_quote else file_pattern
    new_frontmatter = frontmatter.rstrip() + f"\npaths: {value}\n"
    return f"---\n{new_frontmatter}---\n{rest}"


def deploy_skills(
    conn,
    project_path: str,
    project_info: Dict,
    *,
    dry_run: bool = False,
) -> DeployResult:
    """Deploy skill files to .claude/skills/{name}/SKILL.md."""
    result = DeployResult("Skills")
    project_name = project_info.get("project_name", "")
    project_type = project_info.get("project_type", "infrastructure")

    project_id = project_info.get("project_id", "")
    skills = get_scoped_skills(conn, project_type, project_name, project_id)
    if not skills:
        return result.skip("none in DB")

    skills_dir = Path(project_path) / ".claude" / "skills"
    count = 0
    failed: List[str] = []

    for skill in skills:
        name = skill.get("name", "").strip()
        content = skill.get("content", "") or ""
        scope = skill.get("scope", "global")
        file_pattern = skill.get("file_pattern")
        if not name or not content:
            logger.debug("Skipping skill with missing name or content")
            continue
        # Skip global skills in per-project deploy — they go to ~/.claude/skills/
        # Deploying them to .claude/skills/ causes Claude Code to show duplicates
        if scope == "global":
            continue

        skill_dir = skills_dir / name
        skill_file = skill_dir / "SKILL.md"

        if dry_run:
            count += 1
            continue

        try:
            skill_dir.mkdir(parents=True, exist_ok=True)
            _atomic_write(skill_file, inject_paths_frontmatter(content, file_pattern))
            count += 1
            logger.debug("Wrote skill: %s", name)
        except Exception as exc:
            logger.error("Failed to write skill '%s': %s", name, exc)
            failed.append(name)

    if failed:
        return result.warn(f"{count} deployed, {len(failed)} failed: {failed}")
    if dry_run:
        return result.ok(f"[dry-run] would deploy {count} skills")
    # Also deploy global skills to ~/.claude/skills/
    global_result = deploy_global_skills(conn, dry_run=dry_run)
    if global_result.status == "OK":
        logger.info("Global skills: %s", global_result.detail)

    return result.ok(f"{count} deployed") if count else result.skip("none matched scope")


def deploy_global_skills(conn, *, dry_run: bool = False) -> DeployResult:
    """Deploy global-scope skills to ~/.claude/skills/{name}/SKILL.md."""
    result = DeployResult("Global Skills")
    global_dir = Path.home() / ".claude" / "skills"
    count = 0
    failed: List[str] = []

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name, content, file_pattern FROM claude.skills "
            "WHERE is_active = true AND scope = 'global' AND content IS NOT NULL AND content != ''"
        )
        rows = [_row_to_dict(row) for row in cur.fetchall()]
    except Exception as exc:
        return result.warn(f"Query failed: {exc}")

    for row in rows:
        name = row.get("name", "").strip()
        content = row.get("content", "") or ""
        file_pattern = row.get("file_pattern")
        if not name or not content:
            continue

        skill_dir = global_dir / name
        skill_file = skill_dir / "SKILL.md"

        if dry_run:
            count += 1
            continue

        try:
            skill_dir.mkdir(parents=True, exist_ok=True)
            _atomic_write(skill_file, inject_paths_frontmatter(content, file_pattern))
            count += 1
            logger.debug("Wrote global skill: %s", name)
        except Exception as exc:
            logger.error("Failed to write global skill '%s': %s", name, exc)
            failed.append(name)

    if failed:
        return result.warn(f"{count} deployed, {len(failed)} failed: {failed}")
    if dry_run:
        return result.ok(f"[dry-run] would deploy {count} global skills")
    return result.ok(f"{count} deployed") if count else result.skip("none in DB")


def deploy_commands(
    conn,
    project_path: str,
    project_info: Dict,
    *,
    dry_run: bool = False,
) -> DeployResult:
    """Deploy command files from DB (claude.skills WHERE scope='command') to .claude/commands/{name}.md."""
    result = DeployResult("Commands")

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, content
            FROM claude.skills
            WHERE is_active = true AND scope = 'command'
            ORDER BY name
            """,
        )
        commands = [_row_to_dict(row) for row in cur.fetchall()]
    except Exception as exc:
        logger.error("Failed to query commands from DB: %s", exc)
        return result.skip("DB query failed")

    if not commands:
        return result.skip("none in DB")

    if dry_run:
        return result.ok(f"[dry-run] would deploy {len(commands)} commands")

    commands_dir = Path(project_path) / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    failed: List[str] = []
    for cmd in commands:
        name = cmd.get("name", "")
        content = cmd.get("content", "")
        dst = commands_dir / f"{name}.md"
        try:
            _atomic_write(dst, content)
            count += 1
        except Exception as exc:
            logger.error("Failed to write command '%s': %s", name, exc)
            failed.append(name)

    if failed:
        return result.warn(f"{count} deployed, {len(failed)} failed")
    return result.ok(f"{count} deployed")


def deploy_rules(
    conn,
    project_path: str,
    project_info: Dict,
    *,
    dry_run: bool = False,
) -> DeployResult:
    """Deploy rule files to .claude/rules/{name}.md."""
    result = DeployResult("Rules")
    project_name = project_info.get("project_name", "")
    project_type = project_info.get("project_type", "infrastructure")

    project_id = project_info.get("project_id", "")
    rules = get_scoped_rules(conn, project_type, project_name, project_id)
    if not rules:
        return result.skip("none in DB")

    rules_dir = Path(project_path) / ".claude" / "rules"
    count = 0
    failed: List[str] = []

    for rule in rules:
        name = rule.get("name", "").strip()
        content = rule.get("content", "") or ""
        if not name or not content:
            logger.debug("Skipping rule with missing name or content")
            continue

        rule_file = rules_dir / f"{name}.md"

        if dry_run:
            count += 1
            continue

        try:
            rules_dir.mkdir(parents=True, exist_ok=True)
            _atomic_write(rule_file, content)
            count += 1
            logger.debug("Wrote rule: %s", name)
        except Exception as exc:
            logger.error("Failed to write rule '%s': %s", name, exc)
            failed.append(name)

    if failed:
        return result.warn(f"{count} deployed, {len(failed)} failed: {failed}")
    if dry_run:
        return result.ok(f"[dry-run] would deploy {count} rules")
    return result.ok(f"{count} deployed") if count else result.skip("none matched scope")


def deploy_agents(
    conn,
    project_path: str,
    project_info: Dict,
    *,
    dry_run: bool = False,
) -> DeployResult:
    """Deploy agent definition files from DB (claude.skills WHERE scope='agent') to .claude/agents/{name}.md."""
    result = DeployResult("Agents")

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, content
            FROM claude.skills
            WHERE is_active = true AND scope = 'agent'
            ORDER BY name
            """,
        )
        agents = [_row_to_dict(row) for row in cur.fetchall()]
    except Exception as exc:
        logger.error("Failed to query agents from DB: %s", exc)
        return result.skip("DB query failed")

    if not agents:
        return result.skip("none in DB")

    if dry_run:
        return result.ok(f"[dry-run] would deploy {len(agents)} agents")

    agents_dir = Path(project_path) / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    failed: List[str] = []
    for agent in agents:
        name = agent.get("name", "")
        content = agent.get("content", "")
        dst = agents_dir / f"{name}.md"
        try:
            _atomic_write(dst, content)
            count += 1
        except Exception as exc:
            logger.error("Failed to write agent '%s': %s", name, exc)
            failed.append(name)

    if failed:
        return result.warn(f"{count} deployed, {len(failed)} failed")
    return result.ok(f"{count} deployed")


def sync_claude_md(
    conn,
    project_path: str,
    project_info: Dict,
    *,
    dry_run: bool = False,
    interactive: bool = False,
) -> DeployResult:
    """Deploy CLAUDE.md from DB profiles to disk. DB is source of truth.

    One-way push: DB → disk. To change CLAUDE.md, use config_manage(action="update_section")
    which updates the DB. This function then deploys the DB content to the file.
    """
    result = DeployResult("CLAUDE.md")
    project_name = project_info.get("project_name", "")

    claude_md_path = Path(project_path) / "CLAUDE.md"

    profile_config = get_claude_md_profile(conn, project_name)
    if not profile_config:
        return result.skip("no DB profile found")

    db_content = profile_config.get("behavior", "") if isinstance(profile_config, dict) else ""
    if not db_content:
        return result.skip("profile has no behavior content")

    db_hash = hashlib.md5(db_content.encode("utf-8")).hexdigest()[:8]

    # Check if file exists and is already in sync
    if claude_md_path.exists():
        try:
            file_content = claude_md_path.read_text(encoding="utf-8")
            file_hash = hashlib.md5(file_content.encode("utf-8")).hexdigest()[:8]
            if file_hash == db_hash:
                return result.ok("in sync with DB")
        except Exception as exc:
            return result.warn(f"could not read CLAUDE.md: {exc}")

    # Deploy DB content to disk
    if dry_run:
        return result.ok(f"would deploy from DB (db={db_hash})")

    try:
        claude_md_path.write_text(db_content, encoding="utf-8")
        return result.ok(f"deployed from DB (hash={db_hash})")
    except Exception as exc:
        return result.warn(f"failed to write CLAUDE.md: {exc}")


def sync_global_claude_md(conn, *, dry_run: bool = False) -> DeployResult:
    """Deploy global ~/.claude/CLAUDE.md from the 'global' profile. DB → disk only."""
    result = DeployResult("Global CLAUDE.md")

    global_md_path = Path.home() / ".claude" / "CLAUDE.md"

    profile_config = get_claude_md_profile(conn, "global")
    if not profile_config:
        return result.skip("no 'global' profile found")

    db_content = profile_config.get("behavior", "") if isinstance(profile_config, dict) else ""
    if not db_content:
        return result.skip("global profile has no behavior content")

    db_hash = hashlib.md5(db_content.encode("utf-8")).hexdigest()[:8]

    # Check if file is already in sync
    if global_md_path.exists():
        try:
            file_content = global_md_path.read_text(encoding="utf-8")
            file_hash = hashlib.md5(file_content.encode("utf-8")).hexdigest()[:8]
            if file_hash == db_hash:
                return result.ok("in sync with DB")
        except Exception as exc:
            return result.warn(f"could not read global CLAUDE.md: {exc}")

    if dry_run:
        return result.ok(f"would deploy global from DB (db={db_hash})")

    try:
        global_md_path.parent.mkdir(parents=True, exist_ok=True)
        global_md_path.write_text(db_content, encoding="utf-8")
        return result.ok(f"deployed global from DB (hash={db_hash})")
    except Exception as exc:
        return result.warn(f"failed to write global CLAUDE.md: {exc}")


# ---------------------------------------------------------------------------
# Project resolution
# ---------------------------------------------------------------------------

def resolve_project(conn, arg: str) -> Tuple[Optional[Dict], str]:
    """Resolve a path-or-name argument to (project_info, resolved_path).

    Returns (None, "") if not found.
    """
    # Try as directory path first
    if os.path.isdir(arg):
        resolved_path = os.path.abspath(arg)
        info = get_project_info(conn, resolved_path)
        if info:
            return info, resolved_path
        # Fallback: match by directory name
        project_name = os.path.basename(resolved_path)
        info = get_project_info_by_name(conn, project_name)
        if info:
            return info, resolved_path

    # Try as project name
    info = get_project_info_by_name(conn, arg)
    if info:
        db_path = info.get("project_path", "")
        return info, db_path if db_path else os.getcwd()

    # Last resort: use cwd, infer name from dirname
    cwd = os.getcwd()
    info = get_project_info(conn, cwd)
    if info:
        return info, cwd
    project_name = os.path.basename(cwd)
    info = get_project_info_by_name(conn, project_name)
    if info:
        return info, cwd

    return None, cwd


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_COMPONENTS = ["settings", "mcp", "skills", "commands", "rules", "agents", "claude_md", "global_claude_md"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync project configuration from database to filesystem.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Project path or project name (default: current working directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing any files",
    )
    parser.add_argument(
        "--component",
        choices=ALL_COMPONENTS,
        default=None,
        help="Deploy only one component",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Skip user prompts (for hook/automated calls)",
    )
    args = parser.parse_args()

    interactive = not args.no_interactive
    dry_run = args.dry_run
    components = [args.component] if args.component else ALL_COMPONENTS

    # Connect to DB
    conn = get_db_connection()
    if conn is None:
        print("[WARN] Database unavailable — cannot sync project configuration")
        logger.warning("sync_project: DB unavailable, skipping")
        return 1

    try:
        # Resolve project
        target = args.target or os.getcwd()
        project_info, project_path = resolve_project(conn, target)

        if project_info is None:
            project_name = os.path.basename(os.path.abspath(target))
            print(
                f"[WARN] Project '{project_name}' not found in claude.workspaces "
                f"(path: {target}). Is it registered in the DB?"
            )
            logger.warning("sync_project: project not found for target '%s'", target)
            return 1

        project_name = project_info.get("project_name", os.path.basename(project_path))
        project_type = project_info.get("project_type", "infrastructure")

        if dry_run:
            print(f"[DRY-RUN] Project: {project_name} ({project_type})")
        else:
            print(f"[SYNC] Project: {project_name} ({project_type})")

        # Dispatch per component
        results: List[DeployResult] = []

        component_map = {
            "settings": lambda: deploy_settings(
                conn, project_path, project_info, dry_run=dry_run
            ),
            "mcp": lambda: deploy_mcp(
                conn, project_path, project_info, dry_run=dry_run
            ),
            "skills": lambda: deploy_skills(
                conn, project_path, project_info, dry_run=dry_run
            ),
            "commands": lambda: deploy_commands(
                conn, project_path, project_info, dry_run=dry_run
            ),
            "rules": lambda: deploy_rules(
                conn, project_path, project_info, dry_run=dry_run
            ),
            "agents": lambda: deploy_agents(
                conn, project_path, project_info, dry_run=dry_run
            ),
            "claude_md": lambda: sync_claude_md(
                conn, project_path, project_info,
                dry_run=dry_run, interactive=interactive,
            ),
            "global_claude_md": lambda: sync_global_claude_md(
                conn, dry_run=dry_run,
            ),
        }

        for component in components:
            fn = component_map.get(component)
            if fn is None:
                continue
            try:
                r = fn()
            except Exception as exc:
                r = DeployResult(component).fail(str(exc))
                logger.error("Component '%s' raised: %s", component, exc, exc_info=True)
            results.append(r)
            print(str(r))

        # Summary exit code: fail if any FAIL result
        has_failures = any(r.status == "FAIL" for r in results)
        return 1 if has_failures else 0

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
