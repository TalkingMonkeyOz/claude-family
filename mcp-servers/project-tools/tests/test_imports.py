"""Import smoke tests.

Catches regressions like the latent `Tuple` import that broke server startup
in a non-obvious way (from the 2026-04-23 handoff). A test that simply
imports both server modules is enough to catch an entire class of bug.
"""
import importlib

import pytest


def test_server_imports():
    """server.py must import cleanly — all type annotations resolvable."""
    mod = importlib.import_module("server")
    assert hasattr(mod, "tool_remember"), "tool_remember missing from server.py"


def test_server_v2_imports():
    """server_v2.py (live FastMCP server) must import cleanly."""
    mod = importlib.import_module("server_v2")
    assert hasattr(mod, "remember"), "remember MCP tool missing from server_v2.py"
    assert hasattr(mod, "read"), "read MCP tool missing from server_v2.py"


def test_core_tools_registered():
    """The consolidated core tools must all be registered in server_v2."""
    mod = importlib.import_module("server_v2")
    required = [
        "remember",
        "recall_memories",
        "workfile_store",
        "workfile_read",
        "read",
        "entity_store",
        "entity_read",
        "start_session",
        "end_session",
        "get_work_context",
    ]
    missing = [name for name in required if not hasattr(mod, name)]
    assert not missing, f"Missing consolidated tools: {missing}"
