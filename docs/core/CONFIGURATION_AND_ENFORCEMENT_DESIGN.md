# Configuration & Self-Enforcement Design

**Created**: 2025-12-16
**Purpose**: Document configuration hierarchy, self-enforcing hooks, and best practices storage

---

## 1. Configuration Tree (Complete Hierarchy)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    CLAUDE CODE CONFIGURATION HIERARCHY                         ║
║                        (Highest to Lowest Priority)                           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  ┌─────────────────────────────────────────────────────────────────────────┐  ║
║  │ TIER 1: ENTERPRISE (Organization-wide)                                   │  ║
║  │                                                                          │  ║
║  │ Windows: C:\Program Files\ClaudeCode\                                    │  ║
║  │   ├── managed-settings.json    # Enterprise policies (cannot override)  │  ║
║  │   ├── managed-mcp.json         # Approved MCP servers                   │  ║
║  │   └── CLAUDE.md                # Company-wide instructions              │  ║
║  │                                                                          │  ║
║  │ Purpose: IT-controlled policies, compliance, approved tools              │  ║
║  └─────────────────────────────────────────────────────────────────────────┘  ║
║                                    │                                          ║
║                                    ▼                                          ║
║  ┌─────────────────────────────────────────────────────────────────────────┐  ║
║  │ TIER 2: USER GLOBAL (~/.claude/)                                         │  ║
║  │                                                                          │  ║
║  │ ~/.claude/                                                               │  ║
║  │   ├── CLAUDE.md                # Personal global instructions           │  ║
║  │   ├── settings.json            # Global permissions, hooks              │  ║
║  │   ├── mcp.json                 # Global MCP servers                     │  ║
║  │   ├── commands/                # Global slash commands                  │  ║
║  │   │   └── *.md                                                          │  ║
║  │   ├── skills/                  # Global skills                          │  ║
║  │   │   └── *.md                                                          │  ║
║  │   └── agents/                  # Global custom agents                   │  ║
║  │       └── *.md                                                          │  ║
║  │                                                                          │  ║
║  │ Purpose: Personal preferences across ALL projects                        │  ║
║  └─────────────────────────────────────────────────────────────────────────┘  ║
║                                    │                                          ║
║                                    ▼                                          ║
║  ┌─────────────────────────────────────────────────────────────────────────┐  ║
║  │ TIER 3: PROJECT SHARED (.claude/ in repo)                                │  ║
║  │                                                                          │  ║
║  │ project-root/                                                            │  ║
║  │   ├── CLAUDE.md                # Main project instructions (SHORT!)     │  ║
║  │   ├── .mcp.json                # Project MCP servers                    │  ║
║  │   │                                                                      │  ║
║  │   └── .claude/                                                           │  ║
║  │       ├── settings.json        # Team permissions, hooks                │  ║
║  │       ├── hooks.json           # Project hooks (merged with settings)   │  ║
║  │       │                                                                  │  ║
║  │       ├── rules/               # AUTO-LOADED modular standards          │  ║
║  │       │   ├── development.md   # Code style, naming                     │  ║
║  │       │   ├── testing.md       # TDD, coverage                          │  ║
║  │       │   ├── database.md      # Schema, queries                        │  ║
║  │       │   ├── api.md           # REST standards                         │  ║
║  │       │   └── ui.md            # Component standards                    │  ║
║  │       │                                                                  │  ║
║  │       ├── commands/            # Project slash commands                 │  ║
║  │       │   └── *.md                                                       │  ║
║  │       │                                                                  │  ║
║  │       └── agents/              # Project custom agents                  │  ║
║  │           └── *.md                                                       │  ║
║  │                                                                          │  ║
║  │ Purpose: Team-shared standards, committed to git                         │  ║
║  └─────────────────────────────────────────────────────────────────────────┘  ║
║                                    │                                          ║
║                                    ▼                                          ║
║  ┌─────────────────────────────────────────────────────────────────────────┐  ║
║  │ TIER 4: PROJECT LOCAL (Personal, gitignored)                             │  ║
║  │                                                                          │  ║
║  │ project-root/                                                            │  ║
║  │   ├── CLAUDE.local.md          # Personal project prefs (auto-gitignored)│  ║
║  │   │                                                                      │  ║
║  │   └── .claude/                                                           │  ║
║  │       └── settings.local.json  # Personal permissions (auto-gitignored) │  ║
║  │                                                                          │  ║
║  │ Purpose: Individual customization without affecting team                 │  ║
║  └─────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Memory System (CLAUDE.md Hierarchy)

### Loading Order (All files loaded, higher overrides lower)

```
1. Enterprise: C:\Program Files\ClaudeCode\CLAUDE.md
2. User Global: ~/.claude/CLAUDE.md
3. Parent Directories: ../CLAUDE.md, ../../CLAUDE.md (recursive up)
4. Project Root: ./CLAUDE.md
5. Project .claude: ./.claude/CLAUDE.md
6. Project Rules: ./.claude/rules/*.md (AUTO-DISCOVERED)
7. User Local: ./CLAUDE.local.md
```

### @Import Syntax

Files can import additional content:

```markdown
# CLAUDE.md

## Standards
@.claude/rules/development.md
@.claude/rules/testing.md

## Project Docs
@docs/ARCHITECTURE.md
@docs/DATABASE_SCHEMA.md

## Personal Prefs
@~/.claude/my-preferences.md
```

### Path-Specific Rules (YAML Frontmatter)

```markdown
---
paths: src/api/**/*.ts
---

# API Development Rules
Only applies to TypeScript files in src/api/
```

---

## 3. Current Hooks Analysis

### What We Have Now:

| Hook | Trigger | Purpose | Status |
|------|---------|---------|--------|
| UserPromptSubmit | Every prompt | Process router, standards injection | ✅ Working |
| SessionStart | Session begins | Auto-log, load state | ✅ Working |
| SessionEnd | Session ends | Doc update check, reminder | ✅ Working |
| PreToolUse (Write/Edit) | File writes | CLAUDE.md validation | ✅ Working |
| PreToolUse (postgres) | DB operations | Column registry validation | ✅ Working |
| PostToolUse (mcp__*) | MCP calls | Usage logging | ✅ Working |
| PreCommit | Before commit | Level 1 tests | ✅ Working |

### What's MISSING (Critical):

| Hook | Purpose | Why Needed |
|------|---------|------------|
| **Stop** | End of Claude response | Counter-based periodic checks |
| **SubagentStop** | End of subagent response | Agent completion tracking |
| PostToolUse (Write/Edit) | Code change tracking | Test enforcement |

---

## 4. Self-Enforcing Hooks Design

### The Problem

> "I'll forget to use /test-first, so will you"

Slash commands require conscious invocation. We need **automatic enforcement**.

### Solution: Counter-Based Stop Hook

```python
# scripts/stop_hook_enforcer.py

import json
import sys
import os
from pathlib import Path

STATE_FILE = Path.home() / ".claude" / "state" / "enforcement_state.json"

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "interaction_count": 0,
        "code_files_changed": [],
        "test_files_touched": False,
        "last_claude_md_check": 0,
        "last_inbox_check": 0,
        "last_git_check": 0
    }

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

def main():
    input_data = json.load(sys.stdin)

    # Check for infinite loop prevention
    if input_data.get("stop_hook_active"):
        sys.exit(0)

    state = load_state()
    state["interaction_count"] += 1
    count = state["interaction_count"]

    reminders = []

    # Every 5 interactions: Git status check
    if count - state["last_git_check"] >= 5:
        # Would check git status here
        state["last_git_check"] = count
        reminders.append("Consider committing if you have significant changes")

    # Every 10 interactions: Inbox check
    if count - state["last_inbox_check"] >= 10:
        state["last_inbox_check"] = count
        reminders.append("Check /inbox-check for messages from other Claude instances")

    # Every 20 interactions: CLAUDE.md refresh
    if count - state["last_claude_md_check"] >= 20:
        state["last_claude_md_check"] = count
        reminders.append("Re-read CLAUDE.md to refresh project context")

    # Code changed without tests
    if state["code_files_changed"] and not state["test_files_touched"]:
        reminders.append("⚠️ CODE CHANGED WITHOUT TESTS - Consider running tests")

    save_state(state)

    if reminders:
        output = {
            "systemMessage": "PERIODIC REMINDERS:\n- " + "\n- ".join(reminders)
        }
        print(json.dumps(output))

    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Hook Configuration to Add

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"C:/Projects/claude-family/scripts/stop_hook_enforcer.py\"",
            "timeout": 5,
            "description": "Counter-based periodic reminders and enforcement"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python \"C:/Projects/claude-family/scripts/track_code_changes.py\"",
            "timeout": 3,
            "description": "Track code changes for test enforcement"
          }
        ]
      }
    ]
  }
}
```

### Enforcement Schedule

| Trigger | Check | Action |
|---------|-------|--------|
| Every 5 responses | Git status | Remind if many uncommitted files |
| Every 10 responses | Inbox | Check for pending messages |
| Every 20 responses | CLAUDE.md | Re-inject key rules |
| On code change | Test tracking | Flag for test requirement |
| On Stop + code flag | Test check | Warn if no tests touched |
| On SessionEnd | Summary | Auto-save TODO_NEXT_SESSION.md |

---

## 5. Best Practices Storage Strategy

### Current Problem

- Standards docs are **too long** (100+ lines each)
- CLAUDE.md is **verbose**
- No use of **@import** syntax
- No use of **.claude/rules/** auto-discovery

### Anthropic's Recommendation

> "Keep CLAUDE.md concise. Use imports for detailed content."
> ".claude/rules/*.md files are automatically discovered and loaded."

### Proposed Structure

```
project-root/
├── CLAUDE.md                    # SHORT (50 lines max)
│
├── .claude/
│   ├── settings.json
│   ├── hooks.json
│   │
│   ├── rules/                   # AUTO-LOADED by Claude
│   │   ├── development.md       # 30 lines - key rules only
│   │   ├── testing.md           # 20 lines - TDD essentials
│   │   ├── database.md          # 25 lines - schema rules
│   │   ├── api.md               # 25 lines - REST essentials
│   │   └── ui.md                # 25 lines - component rules
│   │
│   └── commands/
│       └── *.md
│
└── docs/
    └── standards/               # FULL docs (linked from rules/)
        ├── DEVELOPMENT_STANDARDS.md
        ├── TESTING_STANDARDS.md
        └── ...
```

### Short Rules Format Example

```markdown
# .claude/rules/testing.md

## Test Requirements
- ALWAYS write tests for new code
- Tests MUST pass before commit
- Minimum coverage: 70%

## TDD Pattern
1. Write test → 2. Verify failure → 3. Implement → 4. Refactor

## Full Guide
See @docs/standards/TESTING_STANDARDS.md for complete guide
```

---

## 6. Git Integration Assessment

### Question: "Does Git add value or too much complexity?"

**Answer: HIGH VALUE, LOW COMPLEXITY if done right**

### Value vs Complexity Matrix

| Feature | Value | Complexity | Verdict |
|---------|-------|------------|---------|
| Feature branches | HIGH | LOW | ✅ KEEP |
| Pre-commit hooks | HIGH | LOW | ✅ KEEP |
| Commit message format | MEDIUM | LOW | ✅ KEEP |
| Git worktrees | HIGH | MEDIUM | ⚡ OPTIONAL |
| Auto PR creation | MEDIUM | LOW | ⚡ NICE-TO-HAVE |
| Complex rebasing | LOW | HIGH | ❌ AVOID |
| Multiple remotes | LOW | HIGH | ❌ AVOID |

### Recommended Git Integration

1. **Feature branches**: `feature/`, `fix/`, `docs/`
2. **Pre-commit hook**: Type check + lint + basic tests
3. **Commit format**: Conventional commits (enforced by hook)
4. **Stop hook**: Remind to commit after many file changes

### Git-Aware Hooks

```python
# In stop_hook_enforcer.py

import subprocess

def check_git_status():
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True
    )
    changed_files = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

    if changed_files > 10:
        return f"⚠️ {changed_files} uncommitted files - consider committing"
    return None
```

---

## 7. Agent List Update (Including ATO)

### Agents to KEEP

| Agent | Use Case | Model | Notes |
|-------|----------|-------|-------|
| coder-haiku | General coding | Haiku | High usage |
| python-coder-haiku | Python specific | Haiku | High usage |
| reviewer-sonnet | Code review | Sonnet | Quality gate |
| web-tester-haiku | E2E testing | Haiku | Playwright |
| architect-opus | Planning | Opus | Complex design |
| researcher-opus | Research | Opus | Investigation |
| **ux-tax-screen-analyzer** | **ATO tax screens** | **Haiku** | **KEEP - specialist** |

### Agents to ARCHIVE (until needed)

- security-sonnet
- analyst-sonnet
- planner-sonnet
- lightweight-haiku
- nextjs-tester-haiku
- screenshot-tester-haiku
- research-coordinator-sonnet

---

## 8. Mapping Anthropic Processes to Our System

### Anthropic's Core Loop

```
Gather Context → Take Action → Verify Work → Repeat
```

### Our Implementation Mapping

| Anthropic Concept | Our Implementation | Enforcement |
|-------------------|-------------------|-------------|
| **Explore phase** | Task(Explore) agent | Manual trigger |
| **Plan phase** | EnterPlanMode tool | Manual trigger |
| **Code phase** | Direct coding | Always active |
| **Verify phase** | **MISSING** | **Add Stop hook** |
| **Commit phase** | Git commit | Pre-commit hook |
| **Extended thinking** | "ultrathink" keyword | Doc in CLAUDE.md |
| **TDD workflow** | /test-first command | **Auto-enforce via Stop hook** |
| **Context persistence** | TODO_NEXT_SESSION.md | **Auto-save on SessionEnd** |
| **Multi-agent** | Orchestrator | Working |
| **CLAUDE.md concise** | Current: verbose | **Refactor to .claude/rules/** |

### Gap Analysis & Fixes

| Gap | Fix | Priority |
|-----|-----|----------|
| No verification phase | Add Stop hook with test check | HIGH |
| TDD not enforced | Track code changes, warn if no tests | HIGH |
| Context not auto-saved | SessionEnd hook saves TODO | MEDIUM |
| CLAUDE.md too long | Migrate to .claude/rules/ | MEDIUM |
| No periodic reminders | Counter-based Stop hook | HIGH |

---

## 9. Implementation Checklist

### Phase 1: Critical Hooks (This Week)

- [ ] Create `scripts/stop_hook_enforcer.py`
- [ ] Create `scripts/track_code_changes.py`
- [ ] Add Stop hook to hooks.json
- [ ] Add PostToolUse(Write|Edit) hook for tracking
- [ ] Create state file structure

### Phase 2: Documentation Refactor (Next Week)

- [ ] Create .claude/rules/ directory
- [ ] Split standards into short rule files
- [ ] Update CLAUDE.md to 50 lines max
- [ ] Add @imports to detailed docs
- [ ] Test auto-discovery of rules/

### Phase 3: Testing & Validation

- [ ] Test all hooks work correctly
- [ ] Test counter-based reminders fire
- [ ] Test code change tracking
- [ ] Test SessionEnd auto-save
- [ ] Document all hooks in HOOKS_REFERENCE.md

---

## 10. Files to Create/Modify

### New Files

1. `scripts/stop_hook_enforcer.py` - Counter-based periodic enforcement
2. `scripts/track_code_changes.py` - Track Write/Edit for test requirement
3. `.claude/rules/development.md` - Short dev rules
4. `.claude/rules/testing.md` - Short test rules
5. `.claude/rules/database.md` - Short DB rules
6. `.claude/rules/api.md` - Short API rules
7. `.claude/rules/ui.md` - Short UI rules
8. `docs/HOOKS_REFERENCE.md` - Complete hooks documentation

### Files to Modify

1. `.claude/hooks.json` - Add Stop and PostToolUse hooks
2. `CLAUDE.md` - Shorten to 50 lines, add @imports
3. `docs/SYSTEM_IMPROVEMENT_PLAN_2025-12.md` - Update with these findings

---

## 11. Knowledge Retrieval System

### The Problem

> "I need you to write a new importer for Nimbus importing shifts.
> Ahh let me check what knowledge I have on API shifts..."

Currently, Claude doesn't automatically retrieve relevant knowledge from the database.
You have **161 knowledge entries** including rich Nimbus API documentation, but it's not being used!

### Existing Nimbus Knowledge (Example)

| Title | Category | Confidence |
|-------|----------|------------|
| Nimbus ScheduleShift Time Fields | nimbus-api | 4/10 |
| Nimbus REST CRUD Pattern | nimbus-rest-api | 10/10 |
| Nimbus OData Field Naming | Nimbus API | 10/10 |
| Nimbus UserSDK Batch Import | Nimbus UserSDK | 10/10 |
| ScheduleShift GET idorfilter | nimbus-api | 3/10 |

### Solution: Knowledge-Aware Hook

Enhance UserPromptSubmit hook to automatically query relevant knowledge:

```
USER: "Write shift importer for Nimbus"
         │
         ▼
┌────────────────────────────────────────────┐
│      KNOWLEDGE RETRIEVAL HOOK              │
│                                            │
│  1. Extract keywords: [nimbus, shift]      │
│  2. Query claude.knowledge                 │
│  3. Find 5 most relevant entries           │
│  4. Inject as <relevant-knowledge>         │
│                                            │
└────────────────────────────────────────────┘
         │
         ▼
CLAUDE RECEIVES:
  - Original prompt
  - <process-guidance> workflow steps
  - <relevant-knowledge> API docs, patterns
  - <standards-guidance> checklists
```

### Implementation

**Keyword Extraction:**
```python
def extract_keywords(prompt: str) -> list[str]:
    entity_keywords = {
        'nimbus', 'shift', 'schedule', 'user', 'import',
        'api', 'odata', 'rest', 'employment', 'ato', 'tax'
    }
    words = re.split(r'[\s,.:;!?()]+', prompt.lower())
    return [w for w in words if w in entity_keywords]
```

**Knowledge Query:**
```sql
SELECT title, description, knowledge_type, confidence_level
FROM claude.knowledge
WHERE (
    title ILIKE ANY(ARRAY['%nimbus%', '%shift%'])
    OR description ILIKE ANY(ARRAY['%nimbus%', '%shift%'])
    OR knowledge_category ILIKE ANY(ARRAY['%nimbus%', '%shift%'])
)
ORDER BY confidence_level DESC, times_applied DESC
LIMIT 5;
```

**Context Injection:**
```xml
<relevant-knowledge>
The following documented patterns may be relevant:

### Nimbus ScheduleShift Time Fields (api-reference)
Category: nimbus-api | Confidence: 4/10
API only needs LOCAL times - UTC is auto-calculated...

### Nimbus REST CRUD Pattern (api-reference)
Category: nimbus-rest-api | Confidence: 10/10
POST handles both create and update operations...
</relevant-knowledge>
```

### Knowledge Storage Strategy

| Knowledge Type | Where to Store | How Accessed |
|----------------|----------------|--------------|
| API docs (Nimbus, ATO) | claude.knowledge | Auto-retrieve hook |
| Code patterns | claude.knowledge | Auto-retrieve hook |
| Project standards | .claude/rules/*.md | Auto-loaded by Claude |
| Session context | TODO_NEXT_SESSION.md | Loaded on start |
| Quick commands | CLAUDE.md | Always visible |

### Adding New Knowledge

Create `/knowledge-add` slash command:

```markdown
# /knowledge-add

Capture new knowledge for the knowledge base.

INSERT INTO claude.knowledge (
    knowledge_type,       -- api-reference, pattern, best-practice, gotcha
    knowledge_category,   -- nimbus-api, ato-api, database
    title,                -- Short searchable name
    description,          -- Full details with examples
    applies_to_projects,  -- ['nimbus-import'] or NULL for all
    confidence_level      -- 1-10 based on validation
) VALUES (...);
```

### Track Usage (times_applied)

Add tracking to see which knowledge is actually useful:
- When knowledge is injected AND Claude uses it → increment times_applied
- Helps rank knowledge by actual value
- Prune low-usage entries over time

---

## 12. Master Implementation Checklist

### Immediate (This Week)

- [ ] **Stop Hook**: Create `scripts/stop_hook_enforcer.py` with counters
- [ ] **Code Tracking**: Create `scripts/track_code_changes.py`
- [ ] **Knowledge Hook**: Add knowledge retrieval to `process_router.py`
- [ ] **Update hooks.json**: Add Stop, PostToolUse(Write|Edit) hooks

### Short-Term (Next Week)

- [ ] **Refactor CLAUDE.md**: Shorten to 50 lines, use .claude/rules/
- [ ] **Create Rules**: Split standards into .claude/rules/*.md
- [ ] **Normalize Knowledge**: Fix category inconsistencies in DB
- [ ] **Add /knowledge-add**: Slash command for capturing learnings

### Medium-Term (Week 3-4)

- [ ] **Full Regression Test**: Test all agents, hooks, configs
- [ ] **Documentation**: Complete HOOKS_REFERENCE.md
- [ ] **Cleanup**: Archive unused directories and tables
- [ ] **Metrics Dashboard**: Track hook effectiveness

---

**Version**: 1.1
**Created**: 2025-12-16
**Updated**: 2025-12-16 (Added knowledge retrieval, implementation checklist)
**Location**: C:\Projects\claude-family\docs\CONFIGURATION_AND_ENFORCEMENT_DESIGN.md
