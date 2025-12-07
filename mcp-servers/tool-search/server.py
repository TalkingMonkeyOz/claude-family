#!/usr/bin/env python3
"""
Tool Search MCP Server

Provides on-demand tool discovery to reduce context token usage.
Instead of loading all tool schemas upfront, agents can search for tools by description.

Expected impact: 85% reduction in tool schema tokens (from ~10K to ~2K)

Usage:
    python server.py
"""

import json
import re
from pathlib import Path
from typing import Any, Optional
from collections import defaultdict

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: mcp package not installed. Run: pip install mcp")
    raise

# Initialize MCP server
mcp = FastMCP("tool-search")

# Load tool index
INDEX_FILE = Path(__file__).parent / "tool_index.json"


def load_index() -> dict:
    """Load tool index from JSON file."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r') as f:
            return json.load(f)
    return {"tools": {}}


def build_keyword_index(tools: dict) -> dict:
    """Build inverted index from keywords to tools."""
    keyword_to_tools = defaultdict(list)
    for tool_id, tool_info in tools.items():
        for keyword in tool_info.get("keywords", []):
            keyword_to_tools[keyword.lower()].append(tool_id)
        # Also index the tool name itself
        keyword_to_tools[tool_id.lower()].append(tool_id)
    return dict(keyword_to_tools)


# Global index
TOOL_INDEX = load_index()
KEYWORD_INDEX = build_keyword_index(TOOL_INDEX.get("tools", {}))


def search_tools(query: str, limit: int = 5) -> list:
    """Search for tools matching query using keyword matching."""
    query_terms = query.lower().split()
    scores = defaultdict(int)

    for term in query_terms:
        # Exact keyword match
        if term in KEYWORD_INDEX:
            for tool_id in KEYWORD_INDEX[term]:
                scores[tool_id] += 10

        # Partial keyword match
        for keyword, tool_ids in KEYWORD_INDEX.items():
            if term in keyword or keyword in term:
                for tool_id in tool_ids:
                    scores[tool_id] += 5

    # Sort by score descending
    sorted_tools = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [tool_id for tool_id, score in sorted_tools[:limit] if score > 0]


@mcp.tool()
def find_tool(query: str, limit: int = 3) -> dict:
    """
    Search for MCP tools by description or keywords.

    Use this to discover tools on-demand instead of loading all schemas upfront.

    Args:
        query: Natural language description of what you want to do
               Examples: "query database", "read file", "spawn agent", "search memory"
        limit: Maximum number of results (default 3)

    Returns:
        Dict with matching tools and their schemas
    """
    matching_ids = search_tools(query, limit)

    if not matching_ids:
        return {
            "found": False,
            "message": f"No tools found matching '{query}'",
            "suggestions": ["database", "file", "memory", "agent", "python", "thinking"]
        }

    tools = TOOL_INDEX.get("tools", {})
    results = []

    for tool_id in matching_ids:
        if tool_id in tools:
            tool_info = tools[tool_id]
            results.append({
                "tool_name": tool_info.get("tool"),
                "server": tool_info.get("server"),
                "description": tool_info.get("description"),
                "schema": tool_info.get("schema"),
                "example": tool_info.get("example")
            })

    return {"found": True, "count": len(results), "query": query, "tools": results}


@mcp.tool()
def list_tool_categories() -> dict:
    """List all available tool categories for discovery."""
    tools = TOOL_INDEX.get("tools", {})
    categories = defaultdict(list)

    for tool_id, tool_info in tools.items():
        server = tool_info.get("server", "unknown")
        categories[server].append({
            "id": tool_id,
            "tool": tool_info.get("tool"),
            "description": tool_info.get("description", "")[:100]
        })

    return {
        "categories": dict(categories),
        "total_tools": len(tools),
        "usage": "Use find_tool(query) to get full schema for any tool"
    }


@mcp.tool()
def get_tool_schema(tool_name: str) -> dict:
    """Get the full schema for a specific tool by name."""
    tools = TOOL_INDEX.get("tools", {})

    for tool_id, tool_info in tools.items():
        if tool_info.get("tool") == tool_name:
            return {"found": True, "tool": tool_info}

    if tool_name in tools:
        return {"found": True, "tool": tools[tool_name]}

    return {"found": False, "message": f"Tool '{tool_name}' not found"}


def main():
    """Run the MCP server."""
    print(f"Tool Search MCP Server starting...")
    print(f"Indexed {len(TOOL_INDEX.get('tools', {}))} tools")
    mcp.run()


if __name__ == "__main__":
    main()
