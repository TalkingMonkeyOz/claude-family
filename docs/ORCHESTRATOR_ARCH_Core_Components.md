# Claude Agent Orchestrator - Core Components & Agent Types

**Version:** 2.0 (split from main document)
**Split Date:** 2025-12-26
**Status:** Production-Ready Prototype
**Author:** Claude Technical Analyst

---

## Core Components

### 1. AgentOrchestrator Class

**Location:** `orchestrator_prototype.py`

**Responsibilities:**
- Load agent specifications from JSON
- Build Claude CLI commands with proper isolation flags
- Spawn subprocess and manage lifecycle
- Capture stdout/stderr and parse results
- Track execution time and cost estimates

**Key Methods:**

```python
class AgentOrchestrator:
    def __init__(self, specs_path: str)
        # Load agent_specs.json and find claude executable

    async def spawn_agent(
        agent_type: str,
        task: str,
        workspace_dir: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]
        # Main entry point - spawns agent and returns result

    def _build_command(spec, mcp_config, workspace) -> list
        # Constructs CLI command with isolation flags

    async def _execute_agent(cmd, task, timeout, spec) -> Dict
        # Runs subprocess, handles I/O, captures output
```

**Critical Implementation Details:**

```python
# Windows-specific handling for .cmd files
if platform.system() == 'Windows' and self.claude_executable.endswith('.cmd'):
    proc = await asyncio.create_subprocess_shell(cmd_str, ...)
else:
    proc = await asyncio.create_subprocess_exec(*cmd, ...)

# Stdin task submission
task_input = task.encode('utf-8')
stdout, stderr = await asyncio.wait_for(
    proc.communicate(input=task_input),
    timeout=timeout
)
```

---

### 2. Agent Specifications (agent_specs.json)

**Structure:**

```json
{
  "description": "Claude Agent Orchestrator - Specialized agent type definitions",
  "version": "1.0.0",
  "agent_types": {
    "agent-name": {
      "model": "claude-haiku-4-5 | claude-sonnet-4-5-20250929",
      "description": "Agent purpose",
      "use_cases": ["list", "of", "scenarios"],
      "allowed_tools": ["Read", "Write", "Bash(git*)"],
      "disallowed_tools": ["Bash(curl*)", "Bash(rm*)"],
      "mcp_config": "configs/agent-name.mcp.json",
      "workspace_jail_template": "{project_root}/src/",
      "read_only": false,
      "system_prompt": "Agent identity and instructions",
      "cost_profile": {
        "input_tokens_avg": 10000,
        "output_tokens_avg": 5000,
        "cost_per_task_usd": 0.035
      },
      "recommended_timeout_seconds": 300
    }
  }
}
```

**Key Configuration Options:**

- `model`: Determines intelligence/cost tradeoff
- `allowed_tools`: Whitelist specific tools (e.g., `["Read", "Bash(pytest*)"]`)
- `disallowed_tools`: Blacklist dangerous operations (e.g., `["Bash(rm*)"]`)
- `mcp_config`: Path to isolated MCP configuration
- `workspace_jail_template`: Directory restriction template
- `read_only`: If true, sets `--permission-mode plan` (no writes)
- `system_prompt`: Identity prompt injected into agent

---

### 3. MCP Configuration Files

**Location:** `configs/*.mcp.json`

**Purpose:** Define which MCP servers each agent can access

**Examples:**

```json
// coder-haiku.mcp.json - Zero MCPs
{
  "mcpServers": {}
}

// reviewer-sonnet.mcp.json - Tree-sitter only
{
  "mcpServers": {
    "tree-sitter": {
      "type": "stdio",
      "command": "C:\\venvs\\mcp\\Scripts\\mcp-server-tree-sitter.exe",
      "args": [],
      "env": {}
    }
  }
}

// security-sonnet.mcp.json - Tree-sitter + Sequential Thinking
{
  "mcpServers": {
    "tree-sitter": { /* ... */ },
    "sequential-thinking": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
      "env": {}
    }
  }
}
```

**Context Impact:**

| Agent Type | MCP Servers | Context Tokens | % of Main Session |
|------------|-------------|----------------|-------------------|
| coder-haiku | 0 | ~0 | 0% |
| debugger-haiku | 0 | ~0 | 0% |
| tester-haiku | 0 | ~0 | 0% |
| reviewer-sonnet | 1 (tree-sitter) | ~18k | 30% |
| security-sonnet | 2 (tree-sitter + seq) | ~20k | 34% |
| analyst-sonnet | 2 (seq + memory) | ~15k | 25% |
| **Main Session** | 5+ servers | ~59k | 100% |

**Savings:** 66-100% context reduction per agent

---

## Agent Types

### 1. coder-haiku

**Model:** claude-haiku-4-5
**Cost:** $0.035/task
**MCPs:** None
**Workspace:** `/src/` (read-write)

**Purpose:** Fast code writing for new features and simple refactoring

**Use Cases:**
- Implement new functions/classes
- Simple refactoring
- Bug fixes (non-complex)
- Add logging/comments
- Format code

**Tool Access:**
- ✅ Read, Write, Edit, Glob, Grep
- ✅ Bash (git add/commit/status/diff only)
- ❌ Bash (curl, wget, rm, del)
- ❌ WebSearch, WebFetch

**System Prompt:**
> "You are a code writer. Write clean, well-tested code following project conventions. Focus on implementation, not architecture."

**Example Task:**
```python
await orchestrator.spawn_agent(
    agent_type='coder-haiku',
    task='Implement a Python function to validate email addresses with regex',
    workspace_dir='C:/Projects/myproject/src'
)
```

---

### 2. debugger-haiku

**Model:** claude-haiku-4-5
**Cost:** $0.028/task
**MCPs:** None
**Workspace:** `/` (read-only)

**Purpose:** Fast test execution and failure analysis

**Use Cases:**
- Run test suites
- Analyze test failures
- Debug simple issues
- Check build status
- Verify test coverage

**Tool Access:**
- ✅ Read, Grep
- ✅ Bash (pytest, npm test, dotnet test, python, node)
- ❌ Write, Edit
- ❌ Bash (curl, wget, rm)

**System Prompt:**
> "You are a debugger. Run tests, analyze failures, identify root causes. Read-only mode - do not modify code."

**Timeout:** 600 seconds (longer for slow test suites)

---

### 3. tester-haiku

**Model:** claude-haiku-4-5
**Cost:** $0.052/task
**MCPs:** None
**Workspace:** `/tests/` (read-write)

**Purpose:** Write unit and integration tests

**Use Cases:**
- Write unit tests
- Write integration tests
- Add test fixtures
- Mock/stub creation
- Test data generation

**Tool Access:**
- ✅ Read, Write, Edit, Grep
- ✅ Bash (pytest, npm test)
- ❌ Bash (curl, wget, rm)
- ❌ WebSearch

**System Prompt:**
> "You are a test writer. Write comprehensive, maintainable tests with good coverage. Follow testing best practices (AAA, Given-When-Then)."

---

### 4. reviewer-sonnet

**Model:** claude-sonnet-4-5-20250929
**Cost:** $0.105/task
**MCPs:** tree-sitter (code structure analysis)
**Workspace:** `/` (read-only)

**Purpose:** Code review and architectural analysis

**Use Cases:**
- Code review for PRs
- Architecture analysis
- Best practices validation
- Performance review
- Maintainability assessment

**Tool Access:**
- ✅ Read, Grep, Glob
- ❌ Write, Edit
- ❌ All Bash commands
- ❌ WebSearch

**System Prompt:**
> "You are a code reviewer. Analyze code for quality, maintainability, performance, and best practices. Provide constructive feedback. Never modify code."

**Why Sonnet:** Complex reasoning about architecture and patterns

---

### 5. security-sonnet

**Model:** claude-sonnet-4-5-20250929
**Cost:** $0.240/task
**MCPs:** tree-sitter + sequential-thinking
**Workspace:** `/` (read-only)

**Purpose:** Security audits and vulnerability scanning

**Use Cases:**
- Security vulnerability scanning
- OWASP Top 10 checks
- Sensitive data detection
- Authentication/authorization review
- Dependency vulnerability audit

**Tool Access:**
- ✅ Read, Grep, Glob
- ❌ Write, Edit
- ❌ All Bash commands
- ❌ WebSearch

**System Prompt:**
> "You are a security auditor. Scan for vulnerabilities (SQL injection, XSS, CSRF, insecure auth, etc.). Check for hardcoded secrets. Never modify code."

**Why Sequential-Thinking:** Complex attack chain analysis

**Timeout:** 600 seconds (thorough scanning takes time)

---

### 6. analyst-sonnet

**Model:** claude-sonnet-4-5-20250929
**Cost:** $0.300/task
**MCPs:** sequential-thinking + memory
**Workspace:** `/docs/` (read-write)

**Purpose:** Research, documentation, and architectural analysis

**Use Cases:**
- Codebase research
- Documentation writing
- Architecture design
- Technical specifications
- Migration planning

**Tool Access:**
- ✅ Read, Grep, Glob, Write, Edit
- ✅ WebSearch, WebFetch
- ❌ Bash (curl, wget, rm)

**System Prompt:**
> "You are a technical analyst. Research codebases, write comprehensive documentation, design architectures. Focus on clarity and completeness."

**Why Memory:** Maintain knowledge graph across research sessions

---

## See Also

- [[ORCHESTRATOR_ARCH_Overview]] - Overview and design principles
- [[ORCHESTRATOR_ARCH_Isolation_Communication]] - Isolation mechanisms and communication flow
- [[ORCHESTRATOR_ARCH_Operations]] - Performance, security, and troubleshooting

---

**Version**: 2.0
**Split**: 2025-12-26
**Status**: Production-Ready Prototype
**Location**: docs/ORCHESTRATOR_ARCH_Core_Components.md
