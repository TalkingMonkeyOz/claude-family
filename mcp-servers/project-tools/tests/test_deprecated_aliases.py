"""FB330 regression: legacy tool aliases carry a `_deprecation` envelope.

Confirms the `deprecated_alias()` decorator injects the deprecation hint into
dict responses without altering success/data fields. Tests the decorator in
isolation — doesn't boot the full MCP server.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, SERVER_DIR)


def _import_decorator():
    """Import the decorator without triggering full server init side-effects.

    We execute just the decorator definition block by reading the source —
    the surrounding module has heavy imports we don't want in the test process.
    """
    import types
    mod = types.ModuleType('server_v2_partial')
    # Bootstrap minimal stub so decorator can be defined (it uses functools only)
    import functools as _ft
    mod.functools = _ft
    # Extract just the decorator + _DEPRECATED_ALIASES dict (bounded so we
    # don't drag in module globals like _ChannelState that need threading).
    with open(os.path.join(SERVER_DIR, 'server_v2.py'), encoding='utf-8') as f:
        src = f.read()
    start = src.find('_DEPRECATED_ALIASES: dict')
    # End marker: the Channel Messaging header that immediately follows the
    # decorator block. Stable anchor that doesn't drift as the file grows.
    end = src.find('# Channel Messaging', start)
    assert start > 0 and end > start, 'cannot locate decorator block'
    block = src[start:end]
    # Execute the block in a fresh namespace with functools available
    ns: dict = {'functools': _ft, '__builtins__': __builtins__}
    exec(block, ns)
    return ns['deprecated_alias'], ns['_DEPRECATED_ALIASES']


def test_decorator_injects_envelope():
    deprecated_alias, aliases = _import_decorator()

    @deprecated_alias("workfile_store(...)")
    def stash(component, title, content):
        return {"success": True, "workfile_id": "abc"}

    result = stash("comp", "title", "body")
    assert result["success"] is True
    assert result["workfile_id"] == "abc"
    assert "_deprecation" in result
    assert result["_deprecation"]["deprecated"] == "stash"
    assert result["_deprecation"]["renamed_to"] == "workfile_store(...)"
    assert "FB330" in result["_deprecation"]["notice"]


def test_non_dict_passthrough():
    deprecated_alias, _ = _import_decorator()

    @deprecated_alias("work_status(...)")
    def weirdly_returns_list():
        return [1, 2, 3]

    # Non-dict results pass through untouched
    assert weirdly_returns_list() == [1, 2, 3]


def test_alias_registry_populated():
    _, aliases = _import_decorator()
    # Known legacy aliases should be in the registry
    assert "stash" in aliases
    assert "catalog" in aliases
    assert "create_feedback" in aliases
    # Active tools shouldn't point to a new name
    assert aliases.get("recall_memories") is None
