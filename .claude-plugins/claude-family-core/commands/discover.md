---
description: Discover available features, processes, commands, and knowledge in Claude Family
---

# Feature Discovery

This command helps you discover what capabilities are available in the Claude Family system.

## Step 1: Query Available Processes

List all registered processes that Claude can follow:

```sql
SELECT
  pr.process_name,
  pr.category,
  pr.description,
  pr.enforcement,
  pr.sop_ref,
  pr.command_ref
FROM claude.process_registry pr
WHERE pr.is_active = true
ORDER BY pr.category, pr.process_name;
```

## Step 2: Query Available Commands

List all slash commands across plugins:

```bash
# Find all command files
find ~/.claude-plugins -name "*.md" -path "*/commands/*" -exec basename {} .md \;
```

Common commands:
- `/session-start` - Initialize a new session
- `/session-end` - End session with state persistence
- `/inbox-check` - Check messages from other Claude instances
- `/broadcast` - Send message to all instances
- `/team-status` - View active Claude family members
- `/discover` - This command (feature discovery)
- `/store-test` - Store a test definition
- `/run-tests` - Run stored tests
- `/test-first` - Start TDD mode

## Step 3: Query Knowledge Base

View what patterns and gotchas are stored:

```sql
SELECT
  sk.pattern_name,
  sk.knowledge_type,
  sk.applies_to,
  sk.confidence_score
FROM claude_family.shared_knowledge sk
WHERE sk.is_active = true
ORDER BY sk.knowledge_type, sk.pattern_name;
```

## Step 4: Query Available Agent Types

```sql
SELECT
  at.agent_type_name,
  at.description,
  at.cost_tier,
  at.capabilities
FROM claude.agent_types at
WHERE at.is_active = true
ORDER BY at.cost_tier, at.agent_type_name;
```

Or use orchestrator:
```
mcp__orchestrator__list_agent_types()
```

## Step 5: Display Discovery Dashboard

```
CLAUDE FAMILY FEATURE DISCOVERY

REGISTERED PROCESSES:
┌───────────────────────┬──────────────┬─────────────────────────────────────────┐
│ Process Name          │ Category     │ Description                             │
├───────────────────────┼──────────────┼─────────────────────────────────────────┤
│ session-start         │ workflow     │ Initialize and log new session          │
│ session-end           │ workflow     │ End session with state persistence      │
│ code-review           │ development  │ Code review with quality checks         │
│ testing               │ development  │ Run test suite and analyze results      │
│ knowledge-capture     │ learning     │ Store patterns and gotchas              │
└───────────────────────┴──────────────┴─────────────────────────────────────────┘

AVAILABLE COMMANDS:
- Session: /session-start, /session-end
- Communication: /inbox-check, /broadcast, /team-status
- Development: /test-first, /store-test, /run-tests
- Discovery: /discover (this command)

KNOWLEDGE BASE:
- Patterns stored: X
- Gotchas stored: Y
- Most recent: "Pattern Name" (date)

AGENT TYPES AVAILABLE:
- coder-haiku: Fast code generation ($)
- reviewer-sonnet: Thorough code review ($$)
- architect-opus: Complex architecture ($$$)
```

## How It Works

1. **Process Detection**: When you type a prompt, `process_router.py` detects matching processes
2. **Standards Injection**: Relevant coding standards are auto-injected
3. **Knowledge Injection**: Patterns from `shared_knowledge` are injected
4. **Todo Suggestion**: Workflow steps are suggested for TodoWrite

## Adding New Features

To add a new process:
```sql
INSERT INTO claude.process_registry (process_name, category, description, enforcement)
VALUES ('my-process', 'development', 'Description here', 'suggested');
```

To add knowledge:
```sql
INSERT INTO claude_family.shared_knowledge (pattern_name, description, applies_to, gotchas)
VALUES ('My Pattern', 'How to use it', 'When to use it', 'Watch out for...');
```
