# /mc-spawn-worker

Spawn a new specialized agent worker via the orchestrator to handle a specific task.

## What This Does

Launches an isolated Claude Code agent with MCP configuration tailored to the task:
- Selects appropriate agent type (coder, tester, reviewer, debugger, etc.)
- Prompts for task description
- Specifies workspace directory
- Monitors agent execution via `mcp__orchestrator__spawn_agent()`

## Usage

```
/mc-spawn-worker
```

Interactive prompts will ask for:
1. **Agent Type** - Choose from available agents
2. **Task Description** - What should the agent do?
3. **Workspace Directory** - Where to run the task
4. **Timeout (optional)** - Max execution time in seconds

## Available Agent Types

### Quick/Lightweight (Haiku)
- `coder-haiku` - General code writing and implementation
- `python-coder-haiku` - Python-specific development
- `debugger-haiku` - Bug diagnosis and fixes
- `tester-haiku` - Test writing and execution
- `web-tester-haiku` - Web application testing
- `nextjs-tester-haiku` - Next.js specific testing
- `screenshot-tester-haiku` - Visual/UI testing

### Advanced (Sonnet)
- `reviewer-sonnet` - Code review and analysis
- `security-sonnet` - Security analysis and hardening
- `analyst-sonnet` - Data analysis and insights
- `planner-sonnet` - Architecture and planning
- `test-coordinator-sonnet` - Test coordination
- `review-coordinator-sonnet` - Review coordination
- `refactor-coordinator-sonnet` - Refactoring coordination
- `onboarding-coordinator-sonnet` - Onboarding tasks

### Specialized (Opus)
- `architect-opus` - System architecture design
- `security-opus` - Advanced security analysis
- `researcher-opus` - Research and investigation
- `agent-creator-sonnet` - Create custom agents
- `csharp-coder-haiku` - C# development
- `ux-tax-screen-analyzer` - UI/UX analysis

## Examples

### Spawn a code reviewer
```
Agent Type: reviewer-sonnet
Task: Review the authentication module in PR #123 for security issues
Workspace: C:\Projects\nimbus
Timeout: 300
```

### Spawn a bug debugger
```
Agent Type: debugger-haiku
Task: Debug the NullPointerException in UserService.java line 45
Workspace: C:\Projects\ato
Timeout: 600
```

### Spawn a test writer
```
Agent Type: tester-haiku
Task: Write unit tests for the new payment processing API
Workspace: C:\Projects\nimbus
Timeout: 600
```

## How It Works

1. Agent spawned in isolated subprocess
2. Has access to MCP tools configured for task type
3. Works within specified workspace directory
4. Returns results and output on completion
5. Takes 30 seconds to 5+ minutes depending on complexity

## Output

Agent execution output including:
- Task completion status
- Results/artifacts created
- Any errors encountered
- Summary statistics

## See Also

- `/mc-dashboard` - View active agents and sessions
- `/mc-analyze-sessions` - Analytics on completed agent work
- `/list-agent-types` - View all available agent types with details
