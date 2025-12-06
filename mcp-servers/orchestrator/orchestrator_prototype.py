#!/usr/bin/env python3
"""
Claude Agent Orchestrator - Prototype

Spawns isolated Claude Code instances with specialized MCP configurations.

Usage:
    python orchestrator_prototype.py spawn coder-haiku "Write a Python email validator" C:/Projects/myproject

Features:
    - Isolated Claude processes with dedicated MCP configs
    - Workspace jailing for security
    - Model selection (Haiku vs Sonnet)
    - Stdin/stdout communication
    - Process lifecycle management
"""

import asyncio
import json
import sys
import os
import platform
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
from datetime import datetime
import shutil

# Optional database logging
try:
    from db_logger import AgentLogger
    DB_LOGGING_AVAILABLE = True
except ImportError:
    DB_LOGGING_AVAILABLE = False
    AgentLogger = None


class AgentOrchestrator:
    """Manages spawning and communication with Claude agents."""

    def __init__(self, specs_path: str = "agent_specs.json", enable_db_logging: bool = True):
        """Initialize orchestrator with agent specifications."""
        self.base_dir = Path(__file__).parent
        self.specs_path = self.base_dir / specs_path
        self.agent_specs = self._load_specs()
        self.claude_executable = self._find_claude_executable()

        # Initialize database logger if available
        self.db_logger = None
        if enable_db_logging and DB_LOGGING_AVAILABLE:
            try:
                self.db_logger = AgentLogger()
            except Exception as e:
                print(f"WARNING: Database logging disabled: {e}", file=sys.stderr)

    def _find_claude_executable(self) -> str:
        """Find Claude Code executable path (handles Windows .cmd files)."""
        # Try to find claude in PATH
        claude_path = shutil.which('claude')

        if claude_path:
            return claude_path

        # On Windows, explicitly check for claude.cmd
        if platform.system() == 'Windows':
            claude_cmd = shutil.which('claude.cmd')
            if claude_cmd:
                return claude_cmd

            # Fallback to common npm global location on Windows
            npm_global = Path(os.environ.get('APPDATA', '')) / 'npm' / 'claude.cmd'
            if npm_global.exists():
                return str(npm_global)

        # Fallback to just 'claude' and let subprocess handle it
        return 'claude'

    def _load_specs(self) -> Dict[str, Any]:
        """Load agent specifications from JSON."""
        with open(self.specs_path, 'r') as f:
            return json.load(f)

    def get_agent_spec(self, agent_type: str) -> Dict[str, Any]:
        """Get specification for a specific agent type."""
        if agent_type not in self.agent_specs['agent_types']:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Available: {list(self.agent_specs['agent_types'].keys())}"
            )
        return self.agent_specs['agent_types'][agent_type]

    async def spawn_agent(
        self,
        agent_type: str,
        task: str,
        workspace_dir: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Spawn a Claude agent with isolated configuration.

        Args:
            agent_type: Type of agent (e.g., 'coder-haiku', 'reviewer-sonnet')
            task: Task description for the agent
            workspace_dir: Directory to jail the agent to
            timeout: Max execution time in seconds (default: from spec)

        Returns:
            Dict with 'success', 'output', 'error', 'cost_estimate'
        """
        spec = self.get_agent_spec(agent_type)

        # Check if this is a local Ollama model
        if spec.get('local_model', False):
            return await self._spawn_local_agent(spec, task, timeout)

        # Resolve paths
        mcp_config_path = self.base_dir / spec['mcp_config']
        workspace_path = Path(workspace_dir).resolve()

        # Load MCP servers for logging
        mcp_servers = []
        try:
            with open(mcp_config_path, 'r') as f:
                # Read as string first to replace {workspace_dir} placeholder
                mcp_config_str = f.read()
                # Replace {workspace_dir} with actual workspace path
                # Escape backslashes for JSON format
                escaped_workspace_path = str(workspace_path).replace('\\', '\\\\')
                mcp_config_str = mcp_config_str.replace('{workspace_dir}', escaped_workspace_path)
                mcp_config = json.loads(mcp_config_str)
                mcp_servers = list(mcp_config.get('mcpServers', {}).keys())
        except:
            pass

        # Log spawn event to database
        session_id = None
        if self.db_logger:
            session_id = self.db_logger.log_spawn(
                agent_type=agent_type,
                task=task,
                workspace_dir=str(workspace_path),
                model=spec['model'],
                mcp_servers=mcp_servers
            )

        # Build Claude Code command
        cmd = self._build_command(spec, mcp_config_path, workspace_path)

        # Set timeout
        timeout = timeout or spec['recommended_timeout_seconds']

        # Prepend workspace context to task so agent knows where to work
        # Agent accesses files via filesystem MCP, not local filesystem
        task_with_context = f"""WORKSPACE: {workspace_path}
Use the filesystem MCP tools (mcp__filesystem__*) to read and write files in this workspace.

TASK:
{task}"""

        # Execute
        start_time = datetime.now()
        result = await self._execute_agent(cmd, task_with_context, timeout, spec)
        execution_time = (datetime.now() - start_time).total_seconds()

        # Add metadata
        result['agent_type'] = agent_type
        result['execution_time_seconds'] = execution_time
        result['estimated_cost_usd'] = spec['cost_profile']['cost_per_task_usd']

        # Log completion to database
        if self.db_logger and session_id:
            self.db_logger.log_completion(session_id, result)

        return result

    def _build_command(
        self,
        spec: Dict[str, Any],
        mcp_config_path: Path,
        workspace_path: Path
    ) -> list:
        """Build the Claude Code CLI command."""
        # Use isolated agent workspace to avoid inheriting hooks/plugins from target project
        # The agent accesses the actual project files via filesystem MCP
        agent_workspace = Path("C:/claude/agent-workspaces")

        cmd = [
            self.claude_executable,
            '--model', spec['model'],
            '--mcp-config', str(mcp_config_path),
            '--add-dir', str(agent_workspace),  # Clean workspace with disableAllHooks
            '--print',  # Output to stdout
        ]

        # Add system prompt if specified
        if 'system_prompt' in spec:
            cmd.extend(['--system-prompt', spec['system_prompt']])

        # Add permission mode (prioritize explicit permission_mode, fallback to read_only check)
        # If skip_all_permissions is set, use --dangerously-skip-permissions for MCP tool access
        if spec.get('skip_all_permissions', False):
            cmd.append('--dangerously-skip-permissions')
        else:
            permission_mode = spec.get('permission_mode')
            if permission_mode and permission_mode != 'default':
                cmd.extend(['--permission-mode', permission_mode])
            elif spec.get('read_only', False):
                cmd.extend(['--permission-mode', 'plan'])

        # Add allowed tools (if specified)
        if 'allowed_tools' in spec and spec['allowed_tools']:
            cmd.extend(['--allowed-tools', ','.join(spec['allowed_tools'])])

        # Add disallowed tools (if specified)
        if 'disallowed_tools' in spec and spec['disallowed_tools']:
            cmd.extend(['--disallowed-tools', ','.join(spec['disallowed_tools'])])

        return cmd

    async def _execute_agent(
        self,
        cmd: list,
        task: str,
        timeout: int,
        spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute agent command and capture output."""
        try:
            # On Windows, use shell for .cmd files
            if platform.system() == 'Windows' and self.claude_executable.endswith('.cmd'):
                # Convert command list to shell string
                cmd_str = ' '.join(f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in cmd)
                proc = await asyncio.create_subprocess_shell(
                    cmd_str,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                # Unix or Windows with .exe
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

            # Send task to stdin
            task_input = task.encode('utf-8')

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=task_input),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    'success': False,
                    'output': None,
                    'error': f'Agent timed out after {timeout} seconds',
                    'stderr': None
                }

            # Process output
            output = stdout.decode('utf-8') if stdout else None
            error_output = stderr.decode('utf-8') if stderr else None

            return {
                'success': proc.returncode == 0,
                'output': output,
                'error': None if proc.returncode == 0 else f"Agent failed with code {proc.returncode}",
                'stderr': error_output
            }

        except Exception as e:
            return {
                'success': False,
                'output': None,
                'error': f'Failed to spawn agent: {str(e)}',
                'stderr': None
            }

    async def _spawn_local_agent(
        self,
        spec: Dict[str, Any],
        task: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Spawn a local Ollama agent instead of Claude.

        Args:
            spec: Agent specification with ollama_model field
            task: Task description
            timeout: Max execution time in seconds

        Returns:
            Dict with 'success', 'output', 'error', 'cost_estimate'
        """
        ollama_model = spec.get('ollama_model', 'deepseek-r1:14b')
        system_prompt = spec.get('system_prompt', '')
        timeout = timeout or spec.get('recommended_timeout_seconds', 120)

        # Build prompt with system context
        full_prompt = f"{system_prompt}\n\nTask: {task}" if system_prompt else task

        start_time = datetime.now()

        try:
            # Call Ollama directly via CLI
            cmd = ['ollama', 'run', ollama_model, full_prompt]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    'success': False,
                    'output': None,
                    'error': f'Local agent timed out after {timeout} seconds',
                    'stderr': None,
                    'agent_type': f"local-{ollama_model}",
                    'execution_time_seconds': timeout,
                    'estimated_cost_usd': 0.0
                }

            output = stdout.decode('utf-8') if stdout else None
            error_output = stderr.decode('utf-8') if stderr else None
            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                'success': proc.returncode == 0,
                'output': output,
                'error': None if proc.returncode == 0 else f"Ollama failed with code {proc.returncode}",
                'stderr': error_output,
                'agent_type': f"local-{ollama_model}",
                'execution_time_seconds': execution_time,
                'estimated_cost_usd': 0.0,
                'local_model': True,
                'performance': spec.get('performance_notes', {})
            }

        except Exception as e:
            return {
                'success': False,
                'output': None,
                'error': f'Failed to spawn local agent: {str(e)}',
                'stderr': None,
                'agent_type': f"local-{ollama_model}",
                'execution_time_seconds': (datetime.now() - start_time).total_seconds(),
                'estimated_cost_usd': 0.0
            }

    async def spawn_agent_async(
        self,
        agent_type: str,
        task: str,
        workspace_dir: str,
        callback_project: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Spawn a Claude agent asynchronously - returns immediately with task_id.

        The agent will report its result via the messaging system when complete.

        Args:
            agent_type: Type of agent (e.g., 'coder-haiku', 'reviewer-sonnet')
            task: Task description for the agent
            workspace_dir: Directory to jail the agent to
            callback_project: Project to notify on completion (via messaging)
            timeout: Max execution time in seconds (default: from spec)

        Returns:
            Dict with 'task_id', 'status', message about where results will be sent
        """
        import uuid

        spec = self.get_agent_spec(agent_type)
        task_id = str(uuid.uuid4())
        timeout = timeout or spec['recommended_timeout_seconds']

        # Log to async_tasks table
        if self.db_logger:
            self.db_logger.log_async_spawn(
                task_id=task_id,
                agent_type=agent_type,
                task=task,
                workspace_dir=workspace_dir,
                callback_project=callback_project
            )

        # Wrap task to include completion reporting instructions
        wrapped_task = f"""{task}

IMPORTANT: When you complete this task, send your result via the messaging system:

mcp__orchestrator__send_message(
    message_type="status_update",
    to_project="{callback_project or 'claude-family'}",
    subject="Async Task Complete: {task_id}",
    body="<your result summary here>"
)

Task ID for reference: {task_id}"""

        # Start the agent in background (fire and forget)
        asyncio.create_task(
            self._run_async_agent(task_id, agent_type, wrapped_task, workspace_dir, timeout, callback_project)
        )

        return {
            "task_id": task_id,
            "status": "spawned",
            "agent_type": agent_type,
            "callback_project": callback_project or "claude-family",
            "message": f"Agent spawned. Results will be sent to {callback_project or 'claude-family'} via messaging."
        }

    async def _run_async_agent(
        self,
        task_id: str,
        agent_type: str,
        task: str,
        workspace_dir: str,
        timeout: int,
        callback_project: Optional[str]
    ):
        """Background task that runs agent and updates status."""
        try:
            # Update status to running
            if self.db_logger:
                self.db_logger.update_async_task(task_id, status='running')

            # Run the agent (reuse existing spawn logic)
            result = await self.spawn_agent(agent_type, task, workspace_dir, timeout)

            # Update completion status
            if self.db_logger:
                if result['success']:
                    self.db_logger.update_async_task(
                        task_id,
                        status='completed',
                        result=result.get('output', '')[:5000]  # Truncate large outputs
                    )
                else:
                    self.db_logger.update_async_task(
                        task_id,
                        status='failed',
                        error=result.get('error', 'Unknown error')
                    )

        except Exception as e:
            if self.db_logger:
                self.db_logger.update_async_task(task_id, status='failed', error=str(e))

    def list_agent_types(self) -> Dict[str, str]:
        """List all available agent types with descriptions."""
        return {
            agent_type: spec['description']
            for agent_type, spec in self.agent_specs['agent_types'].items()
        }


async def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python orchestrator_prototype.py <command> [args]")
        print("\nCommands:")
        print("  list                                    - List available agent types")
        print("  spawn <agent_type> <task> <workspace>  - Spawn an agent")
        print("\nExample:")
        print('  python orchestrator_prototype.py spawn coder-haiku "Write email validator" C:/Projects/myproject')
        sys.exit(1)

    orchestrator = AgentOrchestrator()
    command = sys.argv[1]

    if command == 'list':
        print("\n=== Available Agent Types ===\n")
        for agent_type, description in orchestrator.list_agent_types().items():
            spec = orchestrator.get_agent_spec(agent_type)
            print(f"{agent_type}")
            print(f"  Description: {description}")
            print(f"  Model: {spec['model']}")
            print(f"  Cost: ${spec['cost_profile']['cost_per_task_usd']:.3f}/task")
            print(f"  Read-only: {spec.get('read_only', False)}")
            print()

    elif command == 'spawn':
        if len(sys.argv) < 5:
            print("Error: spawn requires <agent_type> <task> <workspace>")
            sys.exit(1)

        agent_type = sys.argv[2]
        task = sys.argv[3]
        workspace = sys.argv[4]

        print(f"\n=== Spawning {agent_type} ===")
        print(f"Task: {task}")
        print(f"Workspace: {workspace}")
        print(f"\nExecuting...\n")

        result = await orchestrator.spawn_agent(agent_type, task, workspace)

        print(f"\n=== Result ===")
        print(f"Success: {result['success']}")
        print(f"Execution time: {result['execution_time_seconds']:.2f}s")
        print(f"Estimated cost: ${result['estimated_cost_usd']:.3f}")

        if result['success']:
            # Handle Unicode output on Windows console
            try:
                print(f"\nOutput:\n{result['output']}")
            except UnicodeEncodeError:
                # Fallback: encode to utf-8 and write to stdout
                output_bytes = result['output'].encode('utf-8', errors='replace')
                sys.stdout.buffer.write(b"\nOutput:\n")
                sys.stdout.buffer.write(output_bytes)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.flush()
        else:
            print(f"\nError: {result['error']}")
            if result['stderr']:
                try:
                    print(f"\nStderr:\n{result['stderr']}")
                except UnicodeEncodeError:
                    sys.stdout.buffer.write(b"\nStderr:\n")
                    sys.stdout.buffer.write(result['stderr'].encode('utf-8', errors='replace'))
                    sys.stdout.buffer.write(b"\n")
                    sys.stdout.flush()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
