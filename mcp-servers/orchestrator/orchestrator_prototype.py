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
from typing import Dict, Any, Optional, Set
import subprocess
from datetime import datetime
import shutil
import time

# Optional database logging
try:
    from db_logger import AgentLogger
    DB_LOGGING_AVAILABLE = True
except ImportError:
    DB_LOGGING_AVAILABLE = False
    AgentLogger = None


class AgentOrchestrator:
    """Manages spawning and communication with Claude agents."""

    # Safeguard constants
    MAX_CONCURRENT_SPAWNS = 6  # Maximum agents running simultaneously
    MIN_SPAWN_DELAY_SECONDS = 2.0  # Minimum delay between spawns
    MAX_RETRIES = 2  # Max retry attempts for failed spawns
    RETRY_DELAY_SECONDS = 5.0  # Delay before retry

    def __init__(self, specs_path: str = "agent_specs.json", enable_db_logging: bool = True):
        """Initialize orchestrator with agent specifications."""
        self.base_dir = Path(__file__).parent
        self.specs_path = self.base_dir / specs_path
        self.agent_specs = self._load_specs()
        self.claude_executable = self._find_claude_executable()

        # Spawn safeguards
        self._spawn_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_SPAWNS)
        self._last_spawn_time: float = 0
        self._active_spawns: Set[str] = set()  # Track active agent session IDs
        self._spawn_lock = asyncio.Lock()  # Protect spawn timing

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

    def reload_specs(self) -> Dict[str, Any]:
        """Reload agent specs from disk (hot-reload for config changes).

        Call this after modifying agent_specs.json to pick up changes
        without restarting the MCP server.

        Returns:
            Dict with reload status and agent count
        """
        old_count = len(self.agent_specs.get('agent_types', {}))
        self.agent_specs = self._load_specs()
        new_count = len(self.agent_specs.get('agent_types', {}))

        # Log the reload
        print(f"INFO: Reloaded agent specs. Agents: {old_count} -> {new_count}", file=sys.stderr)

        return {
            "reloaded": True,
            "previous_agent_count": old_count,
            "current_agent_count": new_count,
            "specs_path": str(self.specs_path),
            "agent_types": list(self.agent_specs['agent_types'].keys())
        }

    def get_agent_spec(self, agent_type: str) -> Dict[str, Any]:
        """Get specification for a specific agent type."""
        if agent_type not in self.agent_specs['agent_types']:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Available: {list(self.agent_specs['agent_types'].keys())}"
            )
        return self.agent_specs['agent_types'][agent_type]

    # =========================================================================
    # Spawn Safeguards
    # =========================================================================

    def validate_mcp_config(self, agent_type: str) -> tuple[bool, str]:
        """
        Validate MCP config exists and is valid JSON before spawning.

        Returns:
            (is_valid, error_message)
        """
        spec = self.get_agent_spec(agent_type)
        mcp_config_path = self.base_dir / spec['mcp_config']

        if not mcp_config_path.exists():
            return False, f"MCP config not found: {mcp_config_path}"

        try:
            with open(mcp_config_path, 'r') as f:
                config = json.load(f)

            if 'mcpServers' not in config:
                return False, f"Invalid MCP config: missing 'mcpServers' key"

            return True, ""
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON in MCP config: {e}"
        except Exception as e:
            return False, f"Error reading MCP config: {e}"

    async def _enforce_spawn_delay(self):
        """Ensure minimum delay between spawns to prevent resource contention."""
        async with self._spawn_lock:
            now = time.time()
            elapsed = now - self._last_spawn_time
            if elapsed < self.MIN_SPAWN_DELAY_SECONDS:
                delay = self.MIN_SPAWN_DELAY_SECONDS - elapsed
                print(f"DEBUG: Enforcing spawn delay of {delay:.1f}s", file=sys.stderr)
                await asyncio.sleep(delay)
            self._last_spawn_time = time.time()

    def get_active_spawn_count(self) -> int:
        """Get number of currently active spawns."""
        return len(self._active_spawns)

    def get_spawn_status(self) -> Dict[str, Any]:
        """Get current spawn safeguard status."""
        return {
            "active_spawns": len(self._active_spawns),
            "max_concurrent": self.MAX_CONCURRENT_SPAWNS,
            "available_slots": self.MAX_CONCURRENT_SPAWNS - len(self._active_spawns),
            "min_spawn_delay_seconds": self.MIN_SPAWN_DELAY_SECONDS,
            "active_session_ids": list(self._active_spawns)
        }

    async def spawn_agent(
        self,
        agent_type: str,
        task: str,
        workspace_dir: str,
        timeout: Optional[int] = None,
        skip_safeguards: bool = False
    ) -> Dict[str, Any]:
        """
        Spawn a Claude agent with isolated configuration.

        Args:
            agent_type: Type of agent (e.g., 'coder-haiku', 'reviewer-sonnet')
            task: Task description for the agent
            workspace_dir: Directory to jail the agent to
            timeout: Max execution time in seconds (default: from spec)
            skip_safeguards: If True, skip concurrency/delay safeguards (use carefully)

        Returns:
            Dict with 'success', 'output', 'error', 'cost_estimate'
        """
        spec = self.get_agent_spec(agent_type)

        # Check if this is a local Ollama model
        if spec.get('local_model', False):
            return await self._spawn_local_agent(spec, task, timeout)

        # =====================================================================
        # SAFEGUARD 1: Validate MCP config before attempting spawn
        # =====================================================================
        is_valid, error_msg = self.validate_mcp_config(agent_type)
        if not is_valid:
            return {
                "status": "error",
                "success": False,
                "output": "",
                "error": f"Pre-spawn validation failed: {error_msg}",
                "agent_type": agent_type,
                "safeguard": "mcp_config_validation"
            }

        # Generate a tracking ID for this spawn
        import uuid
        spawn_id = str(uuid.uuid4())[:8]

        if not skip_safeguards:
            # =================================================================
            # SAFEGUARD 2: Enforce minimum delay between spawns
            # =================================================================
            await self._enforce_spawn_delay()

            # =================================================================
            # SAFEGUARD 3: Limit concurrent spawns with semaphore
            # =================================================================
            print(f"DEBUG: [{spawn_id}] Waiting for spawn slot ({self.get_active_spawn_count()}/{self.MAX_CONCURRENT_SPAWNS} active)", file=sys.stderr)

        # Acquire semaphore (will block if at max concurrent spawns)
        async with self._spawn_semaphore:
            # Track this spawn
            self._active_spawns.add(spawn_id)
            print(f"DEBUG: [{spawn_id}] Acquired spawn slot for {agent_type}", file=sys.stderr)

            try:
                result = await self._do_spawn(agent_type, task, workspace_dir, timeout, spec, spawn_id)
                return result
            finally:
                # Always remove from active spawns when done
                self._active_spawns.discard(spawn_id)
                print(f"DEBUG: [{spawn_id}] Released spawn slot ({self.get_active_spawn_count()}/{self.MAX_CONCURRENT_SPAWNS} active)", file=sys.stderr)

    async def _do_spawn(
        self,
        agent_type: str,
        task: str,
        workspace_dir: str,
        timeout: Optional[int],
        spec: Dict[str, Any],
        spawn_id: str
    ) -> Dict[str, Any]:
        """Internal spawn implementation (called after safeguards pass)."""

        # Resolve paths
        mcp_config_path = self.base_dir / spec['mcp_config']
        workspace_path = Path(workspace_dir).resolve()

        # Create unique agent workspace per spawn to avoid MCP config conflicts
        # Claude Code loads .mcp.json from the project directory, so we need
        # to copy the agent's MCP config there
        agent_workspace = Path("C:/claude/agent-workspaces") / spawn_id
        agent_workspace.mkdir(parents=True, exist_ok=True)

        # Load and process MCP config
        mcp_servers = []
        mcp_config_str = ""
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
        except Exception as e:
            print(f"DEBUG: [{spawn_id}] Error loading MCP config: {e}", file=sys.stderr)

        # Copy agent's MCP config to workspace as .mcp.json
        # This ensures Claude Code loads the agent-specific MCP servers
        try:
            agent_mcp_json = agent_workspace / ".mcp.json"
            with open(agent_mcp_json, 'w') as f:
                f.write(mcp_config_str)
            print(f"DEBUG: [{spawn_id}] Wrote MCP config to {agent_mcp_json}", file=sys.stderr)

            # Also create .claude/settings.local.json with disableAllHooks
            claude_dir = agent_workspace / ".claude"
            claude_dir.mkdir(exist_ok=True)
            settings_path = claude_dir / "settings.local.json"
            with open(settings_path, 'w') as f:
                json.dump({
                    "disableAllHooks": True,
                    "permissions": {"allow": ["mcp__*"], "deny": [], "ask": []}
                }, f)
        except Exception as e:
            print(f"DEBUG: [{spawn_id}] Error setting up workspace: {e}", file=sys.stderr)

        # Log spawn event to database
        session_id = None
        if self.db_logger:
            # Get parent session ID from environment (set by session startup hook)
            import os
            parent_session_id = os.environ.get('CLAUDE_SESSION_ID')

            session_id = self.db_logger.log_spawn(
                agent_type=agent_type,
                task=task,
                workspace_dir=str(workspace_path),
                model=spec['model'],
                mcp_servers=mcp_servers,
                parent_session_id=parent_session_id
            )

        # Build Claude Code command
        cmd = self._build_command(spec, agent_workspace, workspace_path)

        # Debug: print command being executed
        print(f"DEBUG: [{spawn_id}] Spawning {agent_type} agent", file=sys.stderr)
        print(f"DEBUG: [{spawn_id}] Command: {' '.join(str(c) for c in cmd)[:100]}...", file=sys.stderr)

        # Set timeout with validation
        spec_timeout = spec['recommended_timeout_seconds']
        if timeout is not None and timeout != spec_timeout:
            # User explicitly overriding timeout - validate and warn
            if timeout < spec_timeout * 0.5:
                print(f"⚠️  WARNING: [{spawn_id}] {agent_type} timeout override {timeout}s is <50% of spec {spec_timeout}s",
                      file=sys.stderr)
            elif timeout > spec_timeout * 2:
                print(f"⚠️  WARNING: [{spawn_id}] {agent_type} timeout override {timeout}s is >200% of spec {spec_timeout}s",
                      file=sys.stderr)
            print(f"INFO: [{spawn_id}] Using timeout override: {timeout}s (spec: {spec_timeout}s)", file=sys.stderr)

        timeout = timeout or spec_timeout

        # Get context injection from database-driven rules
        injected_context = ""
        try:
            # Add base_dir to path to import server module
            sys.path.insert(0, str(self.base_dir))
            from server import get_context_for_task

            context_result = get_context_for_task(
                task=task,
                file_patterns=None,  # Could extract from task
                agent_type=agent_type
            )
            if context_result.get('context'):
                injected_context = f"""
=== CODING STANDARDS (from context_rules) ===
{context_result['context']}
=== END STANDARDS ===

"""
                print(f"DEBUG: [{spawn_id}] Injected context from rules: {context_result.get('rules_matched', [])}", file=sys.stderr)
        except Exception as e:
            print(f"DEBUG: [{spawn_id}] Context injection skipped: {e}", file=sys.stderr)

        # Build coordination protocol for agent awareness
        # Use actual session_id from DB (full UUID), not spawn_id (8-char fragment)
        agent_session_id = session_id if session_id else spawn_id
        coordination_protocol = f"""
=== COORDINATION PROTOCOL ===
You are an agent session spawned by parent session.
Your agent_session_id for status reporting: {agent_session_id}

Every 5-7 tool calls, you should:
1. Report your status if the orchestrator MCP is available:
   mcp__orchestrator__update_agent_status(
     session_id="{agent_session_id}",
     agent_type="{agent_type}",
     current_status="working",
     activity="<what you're doing>",
     progress_pct=<0-100>
   )
2. Check for commands from boss:
   mcp__orchestrator__check_agent_commands(session_id="{agent_session_id}")
   - If ABORT: Stop immediately
   - If REDIRECT: Adjust your task based on payload
   - If INJECT: Add payload.context to your understanding
=== END PROTOCOL ===

"""

        # Prepend workspace context to task so agent knows where to work
        # Agent accesses files via filesystem MCP, not local filesystem
        task_with_context = f"""{coordination_protocol}{injected_context}WORKSPACE: {workspace_path}
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
            # Also finalize agent_status to 'completed' or 'failed'
            self.db_logger.finalize_agent_status(
                session_id,
                success=result.get('success', False),
                final_activity=f"Task {'completed' if result.get('success') else 'failed'}"
            )

        # Cleanup temp agent workspace
        try:
            shutil.rmtree(agent_workspace)
            print(f"DEBUG: [{spawn_id}] Cleaned up workspace {agent_workspace}", file=sys.stderr)
        except Exception as e:
            print(f"DEBUG: [{spawn_id}] Failed to cleanup workspace: {e}", file=sys.stderr)

        return result

    def _build_command(
        self,
        spec: Dict[str, Any],
        agent_workspace: Path,
        workspace_path: Path
    ) -> list:
        """Build the Claude Code CLI command."""
        # Agent workspace contains .mcp.json with agent-specific MCP servers
        # Claude Code will load this as the project MCP config
        cmd = [
            self.claude_executable,
            '--model', spec['model'],
            '--add-dir', str(agent_workspace),  # Workspace with agent's .mcp.json
            '--print',  # Output to stdout
        ]

        # Add beta headers if specified (enables features like 1M context, interleaved thinking)
        # Note: Requires API key authentication
        if 'betas' in spec and spec['betas']:
            cmd.extend(['--betas'] + spec['betas'])

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
            if platform.system() == 'Windows' and self.claude_executable.lower().endswith('.cmd'):
                # Convert command list to shell string with proper escaping
                def escape_arg(arg):
                    arg_str = str(arg)
                    # If arg contains newlines, spaces, or special chars, quote and escape it
                    if '\n' in arg_str or ' ' in arg_str or '"' in arg_str:
                        # Replace newlines with spaces, escape internal quotes
                        arg_str = arg_str.replace('\n', ' ').replace('"', '\\"')
                        return f'"{arg_str}"'
                    return arg_str

                cmd_str = ' '.join(escape_arg(arg) for arg in cmd)
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
                # Agent timed out - forcefully terminate
                print(f"⚠️  Agent timeout reached ({timeout}s) - terminating process", file=sys.stderr)

                # Try graceful termination first
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    # Process didn't terminate gracefully, force kill
                    print(f"⚠️  Process didn't terminate gracefully - force killing", file=sys.stderr)
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
                # Local agent timed out - forcefully terminate
                print(f"⚠️  Local agent timeout reached ({timeout}s) - terminating process", file=sys.stderr)

                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    print(f"⚠️  Process didn't terminate gracefully - force killing", file=sys.stderr)
                    proc.kill()
                    await proc.wait()

                execution_time = (datetime.now() - start_time).total_seconds()
                return {
                    'success': False,
                    'output': None,
                    'error': f'Local agent timed out after {timeout} seconds',
                    'stderr': None,
                    'agent_type': f"local-{ollama_model}",
                    'execution_time_seconds': execution_time,  # Use actual time, not timeout value
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
            # Get parent session ID from environment (set by session startup hook)
            import os
            parent_session_id = os.environ.get('CLAUDE_SESSION_ID')

            self.db_logger.log_async_spawn(
                task_id=task_id,
                agent_type=agent_type,
                task=task,
                workspace_dir=workspace_dir,
                callback_project=callback_project,
                parent_session_id=parent_session_id
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
