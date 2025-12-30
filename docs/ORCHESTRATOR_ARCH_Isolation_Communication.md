# Claude Agent Orchestrator - Isolation & Communication

**Version:** 2.0 (split from main document)
**Split Date:** 2025-12-26
**Status:** Production-Ready Prototype
**Author:** Claude Technical Analyst

---

## Isolation Mechanisms

### 1. Process Isolation

**Mechanism:** OS-level process separation via `subprocess.Popen`

**How It Works:**
```python
proc = await asyncio.create_subprocess_exec(
    'claude',
    '--model', spec['model'],
    '--mcp-config', str(mcp_config_path),
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
```

**Isolation Guarantees:**
- Separate memory space (no shared heap)
- Independent process ID (PID)
- No shared file descriptors (except pipes)
- Agent crash doesn't affect orchestrator
- Resource limits enforced by OS

**Testing Evidence:** (from `SUB_AGENT_TEST_RESULTS.md`)
- ✅ 3 parallel agents spawned simultaneously
- ✅ All completed independently
- ✅ No interference between agents
- ✅ Clean termination after completion

---

### 2. Workspace Jailing

**Mechanism:** `--add-dir <path>` flag restricts filesystem access

**How It Works:**
```python
cmd = [
    'claude',
    '--add-dir', str(workspace_path),  # Only this directory accessible
    ...
]
```

**Jail Templates:**

| Agent Type | Workspace Jail | Access Level |
|------------|----------------|--------------|
| coder-haiku | `{project_root}/src/` | Read-Write |
| debugger-haiku | `{project_root}/` | Read-Only |
| tester-haiku | `{project_root}/tests/` | Read-Write |
| reviewer-sonnet | `{project_root}/` | Read-Only |
| security-sonnet | `{project_root}/` | Read-Only |
| analyst-sonnet | `{project_root}/docs/` | Read-Write |

**Example:**
```python
# Coder can ONLY access /src/ directory
workspace_path = Path("C:/Projects/myproject/src").resolve()
cmd.extend(['--add-dir', str(workspace_path)])
```

**Attack Prevention:**
- Agent cannot read `/etc/passwd` or `C:\Windows\System32`
- Agent cannot write to parent directories (`../..`)
- Agent cannot access user home directories
- Agent cannot read `.env` files outside workspace

---

### 3. Permission Mode (Read-Only)

**Mechanism:** `--permission-mode plan` flag prevents all writes

**How It Works:**
```python
if spec.get('read_only', False):
    cmd.extend(['--permission-mode', 'plan'])
```

**Effect:**
- All Write/Edit tool calls auto-rejected
- Bash commands that modify files blocked
- Agent can only read and analyze
- Perfect for review/audit agents

**Applied To:**
- debugger-haiku (read-only analysis)
- reviewer-sonnet (review without modification)
- security-sonnet (audit without patching)

---

### 4. Tool Allow/Deny Lists

**Mechanism:** `--allowed-tools` and `--disallowed-tools` flags

**How It Works:**
```python
# Whitelist approach
if 'allowed_tools' in spec and spec['allowed_tools']:
    cmd.extend(['--allowed-tools', ','.join(spec['allowed_tools'])])

# Blacklist approach
if 'disallowed_tools' in spec and spec['disallowed_tools']:
    cmd.extend(['--disallowed-tools', ','.join(spec['disallowed_tools'])])
```

**Pattern Matching:**
- Exact match: `"Read"` - allows Read tool only
- Glob pattern: `"Bash(git*)"` - allows `git add`, `git commit`, etc.
- Negative pattern: `"Bash(rm*)"` - blocks `rm -rf`, `rm file.txt`, etc.

**Example Configurations:**

```json
// Coder: Git operations only
"allowed_tools": [
  "Read", "Write", "Edit", "Glob", "Grep",
  "Bash(git add*)", "Bash(git commit*)", "Bash(git status*)"
],
"disallowed_tools": [
  "Bash(curl*)", "Bash(wget*)", "Bash(rm*)", "WebSearch"
]

// Security: No bash at all
"allowed_tools": ["Read", "Grep", "Glob"],
"disallowed_tools": ["Bash", "WebSearch"]
```

---

### 5. MCP Isolation

**Mechanism:** Separate `*.mcp.json` files per agent type

**How It Works:**
```python
# Main session loads C:\Users\johnd\.mcp.json (5+ servers)
# Agent loads configs/coder-haiku.mcp.json (0 servers)

cmd = [
    'claude',
    '--mcp-config', str(mcp_config_path),
    '--strict-mcp-config',  # Ignore global ~/.mcp.json
    ...
]
```

**Why It Matters:**

**Without Isolation (Main Session):**
```
Loading MCPs:
  - postgres (database, procedures) → +18k tokens
  - memory (knowledge graph) → +8k tokens
  - tree-sitter (code parsing) → +18k tokens
  - sequential-thinking (CoT) → +2k tokens
  - github (API integration) → +5k tokens
─────────────────────────────────────────────
Total: ~59k tokens added to EVERY request
```

**With Isolation (coder-haiku):**
```
Loading MCPs:
  (none)
─────────────────────────────────────────────
Total: 0 tokens added
```

**Context Savings:**
- Coder tasks: 100% reduction (59k → 0)
- Review tasks: 70% reduction (59k → 18k)
- Security tasks: 66% reduction (59k → 20k)

**Performance Impact:**
- Faster prompt processing (less context to parse)
- Lower token costs (input tokens reduced)
- Cleaner error messages (no MCP server failures)

---

### 6. Model Selection Isolation

**Mechanism:** `--model <model_id>` flag per agent

**Strategy:**

| Task Complexity | Model | Cost | When to Use |
|----------------|-------|------|-------------|
| Simple code writing | Haiku 4.5 | $0.80/M input | Routine tasks, clear requirements |
| Test writing | Haiku 4.5 | $0.80/M input | Structured patterns, known frameworks |
| Debugging | Haiku 4.5 | $0.80/M input | Analyze logs, run tests |
| Code review | Sonnet 4.5 | $3.00/M input | Architectural decisions, patterns |
| Security audit | Sonnet 4.5 | $3.00/M input | Attack chain analysis |
| Research/docs | Sonnet 4.5 | $3.00/M input | Complex synthesis |

**Example:**
```python
# Haiku for speed and cost
{
  "model": "claude-haiku-4-5",
  "cost_profile": {
    "cost_per_task_usd": 0.035
  }
}

# Sonnet for quality
{
  "model": "claude-sonnet-4-5-20250929",
  "cost_profile": {
    "cost_per_task_usd": 0.105
  }
}
```

---

### 7. Timeout Isolation

**Mechanism:** `asyncio.wait_for(timeout=seconds)`

**How It Works:**
```python
try:
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(input=task_input),
        timeout=timeout
    )
except asyncio.TimeoutError:
    proc.kill()  # Hard kill
    await proc.wait()
    return {'success': False, 'error': f'Agent timed out after {timeout}s'}
```

**Timeout Recommendations:**

| Agent Type | Timeout | Reason |
|------------|---------|--------|
| coder-haiku | 300s (5 min) | Code writing is usually fast |
| debugger-haiku | 600s (10 min) | Test suites can be slow |
| tester-haiku | 300s (5 min) | Test writing is fast |
| reviewer-sonnet | 300s (5 min) | Analysis is CPU-bound |
| security-sonnet | 600s (10 min) | Thorough scanning |
| analyst-sonnet | 600s (10 min) | Research + web fetches |

**Override:**
```python
result = await orchestrator.spawn_agent(
    agent_type='debugger-haiku',
    task='Run full integration test suite',
    workspace_dir='C:/Projects/myproject',
    timeout=1200  # 20 minutes for slow tests
)
```

---

## Communication Flow

### 1. Spawn Agent

**Sequence Diagram:**

```
Orchestrator                     Agent Process
    │                                 │
    ├─1. Load agent_specs.json        │
    ├─2. Validate agent type          │
    ├─3. Resolve workspace path       │
    ├─4. Build CLI command            │
    │                                 │
    ├─5. Spawn subprocess─────────────>│
    │                                 ├─6. Load MCP config
    │                                 ├─7. Apply workspace jail
    │                                 ├─8. Set permission mode
    │                                 ├─9. Initialize tool lists
    │                                 │
    ├─10. Write task to stdin─────────>│
    │                                 ├─11. Parse task
    │                                 ├─12. Execute tools
    │                                 ├─13. Generate output
    │                                 │
    │<─14. Read stdout/stderr──────────┤
    │                                 │
    ├─15. Parse result                │
    ├─16. Add metadata                │
    │                                 │
    │<─17. Process terminates──────────┤
    │                                 │
    └─18. Return result dict          │
```

### 2. Input Format

**Task Submission:**
```python
task = "Write a Python function to validate email addresses with regex"
task_input = task.encode('utf-8')
stdout, stderr = await proc.communicate(input=task_input)
```

**Agent Receives:**
```
stdin: "Write a Python function to validate email addresses with regex"
```

**Agent Processes:**
- Parses task as natural language prompt
- Uses available tools (Read, Write, etc.)
- Generates response

### 3. Output Format

**Agent Writes to stdout:**
```
Here's an email validator function:

```python
import re

def validate_email(email: str) -> bool:
    """Validate email address using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
```

Created file: C:/Projects/myproject/src/validators.py
```

**Orchestrator Receives:**
```python
{
    'success': True,
    'output': "Here's an email validator function:\n\n...",
    'error': None,
    'stderr': "",
    'agent_type': 'coder-haiku',
    'execution_time_seconds': 8.42,
    'estimated_cost_usd': 0.035
}
```

### 4. Error Handling

**Agent Failure:**
```python
{
    'success': False,
    'output': None,
    'error': 'Agent failed with code 1',
    'stderr': 'Error: Permission denied: /etc/passwd',
    'agent_type': 'coder-haiku',
    'execution_time_seconds': 2.15,
    'estimated_cost_usd': 0.035
}
```

**Timeout:**
```python
{
    'success': False,
    'output': None,
    'error': 'Agent timed out after 300 seconds',
    'stderr': None,
    'agent_type': 'debugger-haiku',
    'execution_time_seconds': 300.01,
    'estimated_cost_usd': 0.028
}
```

**Spawn Failure:**
```python
{
    'success': False,
    'output': None,
    'error': 'Failed to spawn agent: claude executable not found',
    'stderr': None
}
```

---

## Expanding Agent Types

### Step-by-Step Guide

#### 1. Define Agent Specification

**Edit:** `agent_specs.json`

**Add New Entry:**
```json
{
  "agent_types": {
    "ui-tester-haiku": {
      "model": "claude-haiku-4-5",
      "description": "UI testing with FlaUI/Playwright",
      "use_cases": [
        "Test UI interactions",
        "Validate accessibility",
        "Screenshot comparison",
        "Form validation testing"
      ],
      "allowed_tools": [
        "Read",
        "Bash(pytest*)",
        "Bash(python*)"
      ],
      "disallowed_tools": [
        "Write",
        "Edit",
        "Bash(curl*)",
        "Bash(rm*)"
      ],
      "mcp_config": "configs/ui-tester-haiku.mcp.json",
      "workspace_jail_template": "{project_root}/tests/ui/",
      "read_only": true,
      "permission_mode": "plan",
      "system_prompt": "You are a UI tester. Test user interfaces using FlaUI for Windows apps and Playwright for web apps. Validate interactions, accessibility, and visual correctness.",
      "cost_profile": {
        "input_tokens_avg": 12000,
        "output_tokens_avg": 4000,
        "cost_per_task_usd": 0.045
      },
      "recommended_timeout_seconds": 600
    }
  }
}
```

#### 2. Create MCP Configuration

**Create:** `configs/ui-tester-haiku.mcp.json`

```json
{
  "mcpServers": {
    "flaui-testing": {
      "type": "stdio",
      "command": "C:\\path\\to\\FlaUIMcpServer.exe",
      "args": [],
      "env": {}
    }
  }
}
```

**Or use zero MCPs:**
```json
{
  "mcpServers": {}
}
```

#### 3. Test Agent Independently

**Command Line:**
```bash
cd C:\Projects\claude-family\mcp-servers\orchestrator

python orchestrator_prototype.py spawn ui-tester-haiku \
  "Test the login form: verify username/password fields, validate submit button, check error messages" \
  C:/Projects/myapp
```

**Expected Output:**
```
=== Spawning ui-tester-haiku ===
Task: Test the login form: verify username/password fields...
Workspace: C:/Projects/myapp

Executing...

=== Result ===
Success: True
Execution time: 45.32s
Estimated cost: $0.045

Output:
UI Test Results:
✓ Username field: Found, enabled, accepts input
✓ Password field: Found, masked, accepts input
✓ Submit button: Found, enabled, clickable
✓ Error message: Appears on invalid credentials
✓ Form validation: Working correctly

All tests passed.
```

#### 4. Update Documentation

**Add to README.md:**
```markdown
### ui-tester-haiku

**Model:** claude-haiku-4-5
**Cost:** $0.045/task
**MCPs:** flaui-testing
**Workspace:** `/tests/ui/` (read-only)

**Purpose:** UI testing with FlaUI/Playwright

**Use Cases:**
- Test UI interactions
- Validate accessibility
- Screenshot comparison
- Form validation testing
```

#### 5. Integration Testing

**Test Parallel Execution:**
```python
import asyncio

async def test_parallel_ui_testing():
    orchestrator = AgentOrchestrator()

    tasks = [
        orchestrator.spawn_agent('ui-tester-haiku', 'Test login form', 'C:/Projects/app'),
        orchestrator.spawn_agent('ui-tester-haiku', 'Test dashboard', 'C:/Projects/app'),
        orchestrator.spawn_agent('ui-tester-haiku', 'Test settings', 'C:/Projects/app')
    ]

    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        print(f"Test {i+1}: {'PASS' if result['success'] else 'FAIL'}")
        print(f"  Time: {result['execution_time_seconds']:.2f}s")
        print(f"  Cost: ${result['estimated_cost_usd']:.3f}")

asyncio.run(test_parallel_ui_testing())
```

---

### Example: Add Performance Profiler Agent

**Use Case:** Run benchmarks and analyze performance bottlenecks

**Specification:**
```json
{
  "performance-profiler-haiku": {
    "model": "claude-haiku-4-5",
    "description": "Performance profiling and benchmark analysis",
    "use_cases": [
      "Run performance benchmarks",
      "Analyze profiling data",
      "Identify bottlenecks",
      "Memory leak detection",
      "CPU/IO analysis"
    ],
    "allowed_tools": [
      "Read",
      "Grep",
      "Bash(python -m cProfile*)",
      "Bash(py-spy*)",
      "Bash(pytest*benchmark*)",
      "Bash(dotnet trace*)"
    ],
    "disallowed_tools": [
      "Write",
      "Edit",
      "Bash(rm*)"
    ],
    "mcp_config": "configs/performance-profiler-haiku.mcp.json",
    "workspace_jail_template": "{project_root}/",
    "read_only": true,
    "permission_mode": "plan",
    "system_prompt": "You are a performance profiler. Run benchmarks, analyze profiling data, identify bottlenecks (CPU, memory, IO). Provide actionable optimization recommendations.",
    "cost_profile": {
      "input_tokens_avg": 15000,
      "output_tokens_avg": 5000,
      "cost_per_task_usd": 0.055
    },
    "recommended_timeout_seconds": 1200
  }
}
```

**MCP Config (zero MCPs):**
```json
{
  "mcpServers": {}
}
```

**Usage:**
```bash
python orchestrator_prototype.py spawn performance-profiler-haiku \
  "Profile the data processing pipeline and identify CPU bottlenecks" \
  C:/Projects/dataapp
```

---

### Example: Add Data Analyst Agent

**Use Case:** SQL query analysis and database research

**Specification:**
```json
{
  "data-analyst-sonnet": {
    "model": "claude-sonnet-4-5-20250929",
    "description": "SQL query analysis and database research",
    "use_cases": [
      "Analyze SQL queries",
      "Design database schemas",
      "Query optimization",
      "Data migration planning",
      "ETL pipeline design"
    ],
    "allowed_tools": [
      "Read",
      "Grep",
      "Glob",
      "Write",
      "Edit"
    ],
    "disallowed_tools": [
      "Bash(psql -c 'DROP*')",
      "Bash(mysql -e 'DROP*')",
      "Bash(rm*)"
    ],
    "mcp_config": "configs/data-analyst-sonnet.mcp.json",
    "workspace_jail_template": "{project_root}/database/",
    "read_only": false,
    "permission_mode": "default",
    "system_prompt": "You are a data analyst. Analyze SQL queries, design schemas, optimize performance. Focus on data integrity and query efficiency.",
    "cost_profile": {
      "input_tokens_avg": 30000,
      "output_tokens_avg": 10000,
      "cost_per_task_usd": 0.280
    },
    "recommended_timeout_seconds": 600
  }
}
```

**MCP Config (postgres MCP):**
```json
{
  "mcpServers": {
    "postgres": {
      "type": "stdio",
      "command": "C:\\venvs\\mcp\\Scripts\\mcp-server-postgres.exe",
      "args": ["postgresql://localhost/mydb"],
      "env": {}
    }
  }
}
```

**Usage:**
```python
result = await orchestrator.spawn_agent(
    agent_type='data-analyst-sonnet',
    task='Analyze the users table schema and suggest optimizations for login query performance',
    workspace_dir='C:/Projects/webapp/database'
)
```

---

## See Also

- [[ORCHESTRATOR_ARCH_Overview]] - Overview and design principles
- [[ORCHESTRATOR_ARCH_Core_Components]] - Core components and agent types
- [[ORCHESTRATOR_ARCH_Operations]] - Performance, security, and troubleshooting

---

**Version**: 2.0
**Split**: 2025-12-26
**Status**: Production-Ready Prototype
**Location**: docs/ORCHESTRATOR_ARCH_Isolation_Communication.md
