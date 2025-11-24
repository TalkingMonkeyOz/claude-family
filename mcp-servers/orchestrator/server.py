#!/usr/bin/env python3
"""
Claude Agent Orchestrator - Full MCP Server

Exposes agent spawning capabilities via MCP protocol.

Tools:
- spawn_agent: Spawn an isolated Claude agent
- list_agent_types: List available agent types
- get_agent_status: Check if background agent is running (future)
- kill_agent: Terminate a running agent (future)
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Import our orchestrator
from orchestrator_prototype import AgentOrchestrator


# Initialize MCP server
app = Server("claude-orchestrator")

# Initialize orchestrator
orchestrator = AgentOrchestrator()


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="spawn_agent",
            description=(
                "Spawn an isolated Claude Code agent with specialized MCP configuration. "
                "Returns the agent's output after completion. "
                "Available agent types: coder-haiku, debugger-haiku, tester-haiku, "
                "reviewer-sonnet, security-sonnet, analyst-sonnet."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "enum": list(orchestrator.agent_specs['agent_types'].keys()),
                        "description": "Type of agent to spawn"
                    },
                    "task": {
                        "type": "string",
                        "description": "Task description for the agent"
                    },
                    "workspace_dir": {
                        "type": "string",
                        "description": "Workspace directory (agent will be jailed to this path)"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Optional timeout in seconds (default: from agent spec)",
                        "minimum": 1,
                        "maximum": 600
                    }
                },
                "required": ["agent_type", "task", "workspace_dir"]
            }
        ),
        Tool(
            name="list_agent_types",
            description=(
                "List all available agent types with descriptions, costs, and capabilities."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""

    if name == "spawn_agent":
        return await handle_spawn_agent(arguments)

    elif name == "list_agent_types":
        return await handle_list_agent_types()

    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_spawn_agent(arguments: dict) -> List[TextContent]:
    """Handle spawn_agent tool call."""
    agent_type = arguments['agent_type']
    task = arguments['task']
    workspace_dir = arguments['workspace_dir']
    timeout = arguments.get('timeout')

    # Spawn the agent
    result = await orchestrator.spawn_agent(
        agent_type=agent_type,
        task=task,
        workspace_dir=workspace_dir,
        timeout=timeout
    )

    # Format response
    if result['success']:
        response = {
            "status": "success",
            "agent_type": result['agent_type'],
            "execution_time_seconds": result['execution_time_seconds'],
            "estimated_cost_usd": result['estimated_cost_usd'],
            "output": result['output']
        }
        response_text = json.dumps(response, indent=2)
    else:
        response = {
            "status": "failed",
            "agent_type": result['agent_type'],
            "execution_time_seconds": result['execution_time_seconds'],
            "error": result['error'],
            "stderr": result['stderr']
        }
        response_text = json.dumps(response, indent=2)

    return [TextContent(type="text", text=response_text)]


async def handle_list_agent_types() -> List[TextContent]:
    """Handle list_agent_types tool call."""
    agent_types_info = []

    for agent_type, spec in orchestrator.agent_specs['agent_types'].items():
        info = {
            "agent_type": agent_type,
            "description": spec['description'],
            "model": spec['model'],
            "cost_per_task_usd": spec['cost_profile']['cost_per_task_usd'],
            "read_only": spec.get('read_only', False),
            "use_cases": spec.get('use_cases', []),
            "mcp_servers": []
        }

        # Load MCP config to show which MCPs are loaded
        mcp_config_path = orchestrator.base_dir / spec['mcp_config']
        try:
            with open(mcp_config_path, 'r') as f:
                mcp_config = json.load(f)
                info['mcp_servers'] = list(mcp_config.get('mcpServers', {}).keys())
        except:
            pass

        agent_types_info.append(info)

    response_text = json.dumps(agent_types_info, indent=2)
    return [TextContent(type="text", text=response_text)]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
