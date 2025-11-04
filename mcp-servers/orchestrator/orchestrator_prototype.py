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

        # Resolve paths
        mcp_config_path = self.base_dir / spec['mcp_config']
        workspace_path = Path(workspace_dir).resolve()

        # Load MCP servers for logging
        mcp_servers = []
        try:
            with open(mcp_config_path, 'r') as f:
                mcp_config = json.load(f)
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

        # Execute
        start_time = datetime.now()
        result = await self._execute_agent(cmd, task, timeout, spec)
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
        cmd = [
            self.claude_executable,
            '--model', spec['model'],
            '--mcp-config', str(mcp_config_path),
            '--strict-mcp-config',  # Ignore global configs
            '--add-dir', str(workspace_path),  # Workspace jail
            '--print',  # Output to stdout
        ]

        # Add system prompt if specified
        if 'system_prompt' in spec:
            cmd.extend(['--system-prompt', spec['system_prompt']])

        # Add permission mode (prioritize explicit permission_mode, fallback to read_only check)
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
