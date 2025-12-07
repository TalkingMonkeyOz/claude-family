#!/usr/bin/env python3
"""
Sandbox Runner - Execute Claude agents in Docker containers

Provides isolated execution environment where agents can run with full permissions
safely, as they're contained within Docker.

Usage:
    from sandbox_runner import SandboxRunner
    
    runner = SandboxRunner()
    result = await runner.run_sandboxed("coder-haiku", "Write hello world", "C:/Projects/test")
"""

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class SandboxRunner:
    """Manages Docker-based sandboxed Claude agent execution."""
    
    def __init__(self, image_name: str = "claude-sandbox:latest"):
        self.image_name = image_name
        self.gui_image_name = "claude-sandbox-gui:latest"
        self.base_dir = Path(__file__).parent.parent.parent / "docker" / "claude-sandbox"
        
    def _check_docker(self) -> bool:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_image_exists(self, image: str) -> bool:
        """Check if Docker image exists locally."""
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    async def build_image(self, gui: bool = False) -> Dict[str, Any]:
        """Build the sandbox Docker image."""
        dockerfile = "Dockerfile.gui" if gui else "Dockerfile"
        image = self.gui_image_name if gui else self.image_name
        
        cmd = [
            "docker", "build",
            "-f", str(self.base_dir / dockerfile),
            "-t", image,
            str(self.base_dir)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        return {
            "success": proc.returncode == 0,
            "image": image,
            "output": stdout.decode() if stdout else None,
            "error": stderr.decode() if stderr else None
        }
    
    async def run_sandboxed(
        self,
        task: str,
        workspace_path: str,
        timeout: int = 300,
        gui: bool = False,
        model: str = "claude-sonnet-4-20250514"
    ) -> Dict[str, Any]:
        """
        Run a Claude agent in a sandboxed Docker container.
        
        Args:
            task: The task description for the agent
            workspace_path: Path to mount as /workspace in container
            timeout: Maximum execution time in seconds
            gui: If True, use GUI image with Computer Use support
            model: Claude model to use
            
        Returns:
            Dict with success, output, error, execution_time
        """
        # Verify Docker is available
        if not self._check_docker():
            return {
                "success": False,
                "error": "Docker is not running or not installed",
                "output": None
            }
        
        # Select image
        image = self.gui_image_name if gui else self.image_name
        
        # Check if image exists, build if not
        if not self._check_image_exists(image):
            print(f"Building {image}...")
            build_result = await self.build_image(gui=gui)
            if not build_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to build image: {build_result['error']}",
                    "output": None
                }
        
        # Get API key from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "ANTHROPIC_API_KEY environment variable not set",
                "output": None
            }
        
        # Convert Windows path to Docker-compatible format
        workspace = Path(workspace_path).resolve()
        docker_workspace = str(workspace).replace("\\", "/")
        
        # Build Docker run command
        cmd = [
            "docker", "run",
            "--rm",  # Remove container after exit
            "-e", f"ANTHROPIC_API_KEY={api_key}",
            "-e", f"CLAUDE_MODEL={model}",
            "-v", f"{docker_workspace}:/workspace:rw",
            "--memory", "4g",
            "--cpus", "2",
        ]
        
        # Add port mapping for GUI
        if gui:
            cmd.extend(["-p", "6080:6080"])
        
        cmd.append(image)
        
        # Execute
        start_time = datetime.now()
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send task to stdin
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=task.encode()),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "success": False,
                    "error": f"Agent timed out after {timeout} seconds",
                    "output": None,
                    "execution_time": timeout
                }
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": proc.returncode == 0,
                "output": stdout.decode() if stdout else None,
                "error": stderr.decode() if stderr and proc.returncode != 0 else None,
                "execution_time": execution_time,
                "sandboxed": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to run container: {str(e)}",
                "output": None
            }
    
    async def run_with_computer_use(
        self,
        task: str,
        workspace_path: str,
        timeout: int = 600,
        port: int = 6080
    ) -> Dict[str, Any]:
        """
        Run agent with Computer Use (GUI) support.
        
        Opens a virtual display accessible at http://localhost:{port}
        Agent can take screenshots, click, and interact with GUI.
        """
        return await self.run_sandboxed(
            task=task,
            workspace_path=workspace_path,
            timeout=timeout,
            gui=True
        )


# CLI for testing
async def main():
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python sandbox_runner.py <workspace_path> <task>")
        print("Example: python sandbox_runner.py C:/Projects/test 'Create a hello.py file'")
        sys.exit(1)
    
    workspace = sys.argv[1]
    task = " ".join(sys.argv[2:])
    
    runner = SandboxRunner()
    
    print(f"Running sandboxed agent...")
    print(f"Workspace: {workspace}")
    print(f"Task: {task}")
    print("-" * 50)
    
    result = await runner.run_sandboxed(task, workspace)
    
    if result["success"]:
        print("SUCCESS!")
        print(result["output"])
    else:
        print("FAILED!")
        print(result["error"])
    
    print(f"\nExecution time: {result.get('execution_time', 'N/A')} seconds")


if __name__ == "__main__":
    asyncio.run(main())
