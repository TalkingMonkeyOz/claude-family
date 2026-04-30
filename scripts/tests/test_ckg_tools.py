"""Integration-style tests for CKG MCP tool functions.

Covers FB401 (TOC envelope, no truncation, section_id drilldown) and
FB405 (barrel response shape) by exercising the actual server_v2
tool functions against a small fixture project. Tests are skipped
(not failed) when the DATABASE_URI / postgres are unavailable so a
local-only test run doesn't break.

The fixture is created and torn down via SQL — we don't index a real
filesystem; we directly populate claude.code_symbols and
claude.code_references with the shapes the tool functions need to see.
"""
import json
import os
import sys
import uuid

import pytest

# Skip the whole module if DATABASE_URI isn't set or psycopg isn't installed.
DATABASE_URI = os.environ.get("DATABASE_URI") or os.environ.get(
    "POSTGRES_CONNECTION_STRING"
)
if not DATABASE_URI:
    pytest.skip(
        "DATABASE_URI not set — skipping live CKG tool tests",
        allow_module_level=True,
    )

try:
    import psycopg  # noqa: F401
except ImportError:
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        pytest.skip(
            "neither psycopg nor psycopg2 available", allow_module_level=True
        )

# Make server_v2 importable (it lives under mcp-servers/project-tools).
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "mcp-servers", "project-tools"))
sys.path.insert(0, os.path.join(REPO, "scripts"))

# Import lazily so the skip above takes effect first.
import server_v2  # noqa: E402

# Fixture project — random suffix so re-running doesn't collide.
FIXTURE_PROJECT = f"fb401_test_{uuid.uuid4().hex[:8]}"


def _conn():
    return server_v2.get_db_connection()


@pytest.fixture(scope="module")
def fixture_project():
    """Create a project with a known shape, yield its name, drop on teardown."""
    conn = _conn()
    cur = conn.cursor()

    # Create project. claude.projects.project_id has a default; we
    # generate ours so we can scope cleanup precisely.
    project_id = str(uuid.uuid4())
    try:
        cur.execute(
            """
            INSERT INTO claude.projects (project_id, project_name, status, created_at)
            VALUES (%s, %s, 'active', now())
            """,
            (project_id, FIXTURE_PROJECT),
        )
    except Exception:
        # Some installs have additional NOT NULL columns; fall back to a
        # narrow insert with whatever defaults exist.
        conn.rollback()
        cur.execute(
            "INSERT INTO claude.projects (project_id, project_name) VALUES (%s, %s)",
            (project_id, FIXTURE_PROJECT),
        )
    conn.commit()

    # Build a small structure:
    #   smallfile.py — 5 symbols (under threshold; full response)
    #   bigfile.py   — 50 symbols (over threshold; TOC response)
    #   barrel.ts    — 0 user symbols + 1 module symbol + 2 re_exports refs
    # Use OS-native paths so _resolve_ckg_file_path's normpath roundtrip
    # matches what's in the DB (Windows uses backslashes).
    file_path_small = os.path.normpath(os.path.normpath("C:/test/smallfile.py"))
    file_path_big = os.path.normpath(os.path.normpath("C:/test/bigfile.py"))
    file_path_barrel = os.path.normpath(os.path.normpath("C:/test/barrel.ts"))

    sym_rows = []

    # Small file: 5 module-level functions.
    for i in range(5):
        sym_rows.append((
            str(uuid.uuid4()), project_id, f"smallfn_{i}", "function",
            file_path_small, 10 + i, 12 + i, "module", "public",
            f"def smallfn_{i}()", None, "deadbeef" * 8, "python",
        ))

    # Big file: 50 module-level functions.
    big_root_ids = []
    for i in range(50):
        sid = str(uuid.uuid4())
        big_root_ids.append(sid)
        sym_rows.append((
            sid, project_id, f"bigfn_{i}", "function",
            file_path_big, 10 + i, 12 + i, "module", "public",
            f"def bigfn_{i}()", None, "deadbeef" * 8, "python",
        ))

    # Barrel: 1 synthetic module symbol.
    barrel_module_id = str(uuid.uuid4())
    sym_rows.append((
        barrel_module_id, project_id, "barrel", "module",
        file_path_barrel, 1, 1, "module", "public",
        "// barrel module barrel", None, "deadbeef" * 8, "typescript",
    ))

    cur.executemany(
        """
        INSERT INTO claude.code_symbols
            (symbol_id, project_id, name, kind, file_path,
             line_number, end_line, scope, visibility,
             signature, parent_symbol_id, file_hash, language,
             last_indexed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """,
        sym_rows,
    )

    # Barrel re_exports refs.
    rex_rows = [
        (str(uuid.uuid4()), barrel_module_id, None, "./foo:*", "re_exports"),
        (str(uuid.uuid4()), barrel_module_id, None, "./baz:foo", "re_exports"),
        (str(uuid.uuid4()), barrel_module_id, None, "./baz:bar", "re_exports"),
    ]
    cur.executemany(
        """
        INSERT INTO claude.code_references
            (ref_id, from_symbol_id, to_symbol_id, to_symbol_name, ref_type)
        VALUES (%s, %s, %s, %s, %s)
        """,
        rex_rows,
    )
    conn.commit()
    conn.close()

    yield FIXTURE_PROJECT

    # Teardown: cascade-friendly explicit deletes.
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM claude.code_references WHERE from_symbol_id IN "
        "(SELECT symbol_id FROM claude.code_symbols WHERE project_id = %s)",
        (project_id,),
    )
    cur.execute("DELETE FROM claude.code_symbols WHERE project_id = %s", (project_id,))
    cur.execute("DELETE FROM claude.projects WHERE project_id = %s", (project_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# FB401 — TOC envelope, no truncation, section_id drilldown
# ---------------------------------------------------------------------------


class TestModuleMapTOCEnvelope:
    def test_project_default_returns_toc(self, fixture_project):
        result = server_v2.get_module_map(project=fixture_project)
        assert result["success"]
        assert result["scope"] == "project"
        assert result["files_count"] == 3
        assert isinstance(result["files"], list)
        # Every file gets a section_id for drill-down (FB401).
        for f in result["files"]:
            assert "section_id" in f
            assert "symbol_count" in f
        # The breadcrumb hint must be present.
        assert "fetch_section" in result

    def test_project_envelope_under_5kb(self, fixture_project):
        # The whole point of FB401 — the project default must NOT dump
        # symbol arrays. With 56 symbols across 3 files this is trivially
        # small, but the assertion is the structural one: no symbol_list,
        # no per-file symbol detail in the default envelope.
        result = server_v2.get_module_map(project=fixture_project)
        size = len(json.dumps(result, default=str))
        assert size < 5_000, f"FB401 envelope too large: {size} bytes"
        for f in result["files"]:
            # Default project envelope must NOT include per-file symbol arrays.
            assert "symbols" not in f
            assert "symbol_list" not in f

    def test_project_section_id_drills_into_file(self, fixture_project):
        toc = server_v2.get_module_map(project=fixture_project)
        # Find the small file's section_id.
        small = next(f for f in toc["files"] if f["file_path"].endswith(os.path.basename("smallfile.py")))
        sid = small["section_id"]
        drilled = server_v2.get_module_map(project=fixture_project, section_id=sid)
        assert drilled["success"], f"drill failed: {drilled.get('error')}"
        assert drilled["scope"] == "file"
        assert drilled["file_path"].endswith(os.path.basename("smallfile.py"))
        # Small file under threshold → full response with all 5 symbols.
        assert drilled["symbol_count"] == 5
        names = {s["name"] for s in drilled["symbols"]}
        assert names == {f"smallfn_{i}" for i in range(5)}

    def test_no_data_lost_via_drilldown(self, fixture_project):
        # FB401 — every symbol must be reachable. Drill into bigfile and
        # confirm we can reach all 50 root symbols, either directly (full
        # response) or via TOC + per-symbol section_id.
        toc = server_v2.get_module_map(project=fixture_project)
        big = next(f for f in toc["files"] if f["file_path"].endswith(os.path.basename("bigfile.py")))
        drilled = server_v2.get_module_map(project=fixture_project, section_id=big["section_id"])
        assert drilled["symbol_count"] == 50
        # Big file is over threshold → TOC of top-level items, each with
        # its own section_id. Verify each top-level entry has a section_id.
        for s in drilled["symbols"]:
            assert "section_id" in s, f"missing section_id on {s.get('name')}"
        # Drill into one symbol — should return that subtree only.
        first = drilled["symbols"][0]
        sub = server_v2.get_module_map(
            project=fixture_project,
            file_path=drilled["file_path"],
            section_id=first["section_id"],
        )
        assert sub["success"]
        assert len(sub["symbols"]) == 1
        assert sub["symbols"][0]["name"] == first["name"]

    def test_small_file_returns_full_response(self, fixture_project):
        # File-scope with <= 30 symbols returns full hierarchy directly,
        # no TOC. This preserves the existing per-file response shape.
        result = server_v2.get_module_map(
            project=fixture_project, file_path=os.path.normpath("C:/test/smallfile.py")
        )
        assert result["success"]
        assert result["scope"] == "file"
        assert result["symbol_count"] == 5
        # No TOC artefacts on the small-file path.
        assert "fetch_section" not in result
        for s in result["symbols"]:
            assert "children" in s

    def test_bigfile_default_returns_toc(self, fixture_project):
        # File-scope with > 30 symbols returns a TOC of top-level items.
        result = server_v2.get_module_map(
            project=fixture_project, file_path=os.path.normpath("C:/test/bigfile.py")
        )
        assert result["success"]
        assert result["scope"] == "file"
        assert result["symbol_count"] == 50
        assert "fetch_section" in result
        for s in result["symbols"]:
            # TOC entries carry section_id for drill-down.
            assert "section_id" in s
            # And no nested children structure (kept lean).
            assert "children" not in s


# ---------------------------------------------------------------------------
# FB405 — Barrel response
# ---------------------------------------------------------------------------


class TestModuleMapBarrelResponse:
    def test_barrel_kind_returned(self, fixture_project):
        result = server_v2.get_module_map(
            project=fixture_project, file_path=os.path.normpath("C:/test/barrel.ts")
        )
        assert result["success"]
        assert result["kind"] == "barrel", (
            f"FB405 — expected kind='barrel'; got {result.get('kind')}"
        )
        assert result["symbols"] == []
        rex = result["re_exports"]
        # Two paths: ./foo (star) and ./baz (named).
        paths = {r["path"] for r in rex}
        assert paths == {"./foo", "./baz"}
        foo = next(r for r in rex if r["path"] == "./foo")
        baz = next(r for r in rex if r["path"] == "./baz")
        assert foo.get("star") is True
        assert set(baz.get("names", [])) == {"foo", "bar"}
