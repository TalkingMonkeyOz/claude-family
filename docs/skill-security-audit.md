---
projects:
- claude-family
tags:
- security
- audit
- skills
---

# Skill Security Audit

## Current State: What Validation Exists

### 1. `update_config()` in server_v2.py (lines 3702-3916)

The function performs only structural/parameter validation:

- Checks `component_name` is provided (non-empty string)
- Checks `content` is provided (non-empty string)
- Validates `component_type` is one of: skill, rule, instruction, claude_md (via Literal type)
- Resolves `scope` and `scope_ref` for project-scoped components
- Creates version snapshots before updates (audit trail)
- Writes an `audit_log` entry for each create/update

**No content scanning whatsoever.** The `content` parameter is stored and deployed to disk verbatim. Any string passes validation.

### 2. `standards_validator.py` Hook (PreToolUse)

The hook blocks direct file edits to DB-deployed components:

| Path Pattern | Blocked |
|---|---|
| `.claude/skills/*/SKILL.md` | Yes — redirects to `update_config()` |
| `.claude/rules/*.md` | Yes — redirects to `update_config()` |
| `.claude/agents/*.md` | Yes — redirects to `update_config()` |
| `.claude/commands/*.md` | Yes — redirects to `update_config()` |
| `.claude/instructions/*.md` | Yes — redirects to `update_config()` |
| `CLAUDE.md` | Yes — redirects to `update_claude_md()` |
| `settings.local.json`, `.mcp.json` | Yes — DB-generated |

This enforcement is solid: Claude instances cannot bypass `update_config()` by writing files directly. However, `update_config()` itself has no content validation, so the enforcement just redirects to an unvalidated gate.

### 3. Knowledge Entry (9022dfb2-8937-4c31-b34a-90464c5cb764)

Confirms the finding: "Skill creation has zero content validation -- `!command` injection, allowed-tools escalation, and scope escalation are all possible. This is LOW risk internally but HIGH risk for any customer-facing product."

## Gaps: What Is Missing

### Gap 1: No Dangerous Pattern Scanning

`update_config()` does not scan content for:

- **Command injection**: Backtick-wrapped shell commands (e.g., `` !`rm -rf /` ``) that could be executed if the skill content is interpreted
- **Bash code blocks with destructive commands**: `rm -rf`, `del /s`, `format`, `DROP TABLE` inside skill instructions
- **Allowed-tools escalation**: Skills can include `allowedTools` YAML frontmatter that grants access to tools the project config does not permit
- **Scope escalation**: A project-scoped skill could instruct Claude to modify global configs, write to other projects' directories, or alter its own rules
- **Prompt injection**: Skills are injected into context; malicious content could override system instructions (e.g., "Ignore all previous instructions...")
- **Sensitive data patterns**: API keys, passwords, connection strings embedded in skill content

### Gap 2: No Scope Boundary Enforcement

- Any Claude instance can call `update_config()` with `scope='global'` to create skills visible to ALL projects
- No check that the calling project has permission to create/modify global-scoped components
- No check that a project-scoped skill only references its own project's resources

### Gap 3: No Content Size Limits

- `standards_validator.py` enforces line limits on direct file writes, but `update_config()` bypasses this entirely since it writes files directly via `open()`, not through the Write tool
- A skill of unlimited size could be created and deployed

### Gap 4: No Diff Review for Updates

- Updates to existing skills store the old version but do not surface a diff for review
- A subtle malicious change to an existing skill would not be flagged

### Gap 5: Agent Bypass

- Spawned agents have `disableAllHooks: true` per MEMORY.md
- If an agent calls `update_config()` via MCP, the audit_log captures it, but no content validation occurs at the MCP layer either

## Recommended Fixes

### Fix 1: Content Scanner in `update_config()` (High Priority)

Add a validation function before the DB write at line 3785 (before CREATE path) and line 3847 (before UPDATE path):

```python
DANGEROUS_PATTERNS = [
    (r'!\`[^`]+\`', 'Command injection via backtick execution'),
    (r'(?i)ignore\s+(all\s+)?previous\s+instructions', 'Prompt injection attempt'),
    (r'(?i)allowedTools\s*:', 'Tool escalation via allowedTools frontmatter'),
    (r'(?i)(rm\s+-rf|del\s+/[sq]|format\s+[a-z]:)', 'Destructive shell command'),
    (r'(?i)DROP\s+(TABLE|DATABASE|SCHEMA)', 'Destructive SQL command'),
    (r'(?i)(sk-[a-zA-Z0-9]{20,}|password\s*[:=]\s*\S+)', 'Embedded secret/credential'),
    (r'(?i)disableAllHooks', 'Hook bypass attempt'),
]

def validate_config_content(content: str, component_type: str) -> Optional[str]:
    """Returns error message if dangerous patterns found, None if clean."""
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, content):
            return f"Content blocked: {description}"
    return None
```

Call it before INSERT/UPDATE and return `{"success": False, "error": msg}` if it fires.

### Fix 2: Scope Permission Check (Medium Priority)

Add a check that the calling project matches the scope:

```python
if scope == "global" and project != "claude-family":
    return {"success": False, "error": "Only claude-family can create global-scoped components"}
```

This restricts global skill creation to the infrastructure project only. Other projects can create project-scoped skills.

### Fix 3: Content Size Limit (Low Priority)

Add a line count check mirroring `standards_validator.py` limits:

```python
MAX_SKILL_LINES = 300
line_count = content.count('\n') + 1
if line_count > MAX_SKILL_LINES:
    return {"success": False, "error": f"Content exceeds {MAX_SKILL_LINES} line limit ({line_count} lines)"}
```

### Fix 4: Diff Logging for Updates (Low Priority)

Before updating, compute and log a summary diff:

```python
import difflib
diff = list(difflib.unified_diff(
    old_content.splitlines(), content.splitlines(),
    lineterm='', n=3
))
# Store diff summary in audit_log.change_reason or a new column
```

### Fix 5: Rate Limiting (Future)

Track `update_config()` calls per session and flag anomalous bursts (e.g., more than 10 config changes in a single session).

## Risk Assessment

| Threat | Current Risk | With Fixes |
|---|---|---|
| Internal misuse (Claude instance) | Low | Minimal |
| Customer-facing product | High | Medium |
| Supply chain (compromised MCP) | High | Medium |
| Accidental destructive content | Medium | Low |

---
**Version**: 1.0
**Created**: 2026-03-18
**Updated**: 2026-03-18
**Location**: docs/skill-security-audit.md
