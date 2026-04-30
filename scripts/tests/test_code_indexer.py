"""Tests for scripts/code_indexer.py extractors.

Covers FB406 (Python @decorator def/class) and FB404 (TypeScript
object-literal const methods) along with regression coverage for the
existing baseline behaviour (plain def, plain class, arrow-function
const).

Tests parse code via tree-sitter directly and call the private
extractors. They are skipped (not failed) when tree_sitter_language_pack
is unavailable so a missing optional dep doesn't break unrelated
test runs.
"""
import os
import sys
import uuid

import pytest

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, SCRIPT_DIR)

# Skip the whole module if tree-sitter isn't available — the indexer
# itself fails open in that case.
ts_pack = pytest.importorskip("tree_sitter_language_pack")

import code_indexer as ci  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ID = str(uuid.uuid4())
FILE_HASH = "deadbeef" * 8  # 64-char placeholder


def _parse(language: str, source: str):
    parser = ts_pack.get_parser(language)
    src_bytes = source.encode("utf-8")
    return parser.parse(src_bytes), src_bytes


def _extract_py(source: str):
    tree, src_bytes = _parse("python", source)
    return ci._extract_python(tree, src_bytes, "test.py", PROJECT_ID, FILE_HASH)


def _extract_ts(source: str):
    tree, src_bytes = _parse("typescript", source)
    return ci._extract_typescript(
        tree, src_bytes, "test.ts", PROJECT_ID, FILE_HASH, "typescript"
    )


def _names(symbols, *, kind: str = None):
    if kind:
        return {s["name"] for s in symbols if s["kind"] == kind}
    return {s["name"] for s in symbols}


# ---------------------------------------------------------------------------
# FB406 — Python decorated_definition
# ---------------------------------------------------------------------------


class TestPythonDecoratedFunctions:
    def test_simple_decorated_function_extracted(self):
        # Bare decorator
        source = (
            "from functools import cache\n"
            "\n"
            "@cache\n"
            "def foo():\n"
            "    return 1\n"
        )
        symbols, _ = _extract_py(source)
        funcs = _names(symbols, kind="function")
        assert "foo" in funcs, f"@cache decorated function missing; got {funcs}"

    def test_decorator_with_args_extracted(self):
        # Decorator with call expression
        source = (
            "import click\n"
            "\n"
            "@click.command()\n"
            "def cli():\n"
            "    pass\n"
        )
        symbols, _ = _extract_py(source)
        funcs = _names(symbols, kind="function")
        assert "cli" in funcs, f"@click.command() decorated function missing; got {funcs}"

    def test_multiple_decorators_extracted(self):
        # Stacked decorators (the @mcp.tool() pattern that motivated FB406)
        source = (
            "@mcp.tool()\n"
            "@require_auth\n"
            "def tool_work_create(name: str) -> dict:\n"
            "    return {}\n"
        )
        symbols, _ = _extract_py(source)
        funcs = _names(symbols, kind="function")
        assert "tool_work_create" in funcs

    def test_decorated_method_extracted_and_linked_to_class(self):
        source = (
            "class Foo:\n"
            "    @staticmethod\n"
            "    def bar():\n"
            "        return 2\n"
            "\n"
            "    @classmethod\n"
            "    def baz(cls):\n"
            "        return 3\n"
        )
        symbols, _ = _extract_py(source)
        methods = [s for s in symbols if s["kind"] == "method"]
        names = {m["name"] for m in methods}
        assert {"bar", "baz"} <= names, (
            f"Decorated methods missing; got methods={names}"
        )
        # Both methods must be parented to Foo
        foo = next((s for s in symbols if s["kind"] == "class" and s["name"] == "Foo"), None)
        assert foo is not None
        for m in methods:
            assert m["parent_symbol_id"] == foo["symbol_id"], (
                f"Method {m['name']} not parented to Foo"
            )

    def test_decorated_class_extracted(self):
        source = (
            "@dataclass\n"
            "class Config:\n"
            "    name: str\n"
        )
        symbols, _ = _extract_py(source)
        classes = _names(symbols, kind="class")
        assert "Config" in classes


# ---------------------------------------------------------------------------
# Python regression — baseline behaviour intact
# ---------------------------------------------------------------------------


class TestPythonBaselineRegression:
    def test_plain_function_still_extracted(self):
        source = "def foo(x):\n    return x\n"
        symbols, _ = _extract_py(source)
        assert "foo" in _names(symbols, kind="function")

    def test_plain_class_with_method_still_extracted(self):
        source = (
            "class Foo:\n"
            "    def bar(self):\n"
            "        return 1\n"
        )
        symbols, _ = _extract_py(source)
        assert "Foo" in _names(symbols, kind="class")
        assert "bar" in _names(symbols, kind="method")

    def test_imports_still_collected_as_refs(self):
        source = "import os\nfrom pathlib import Path\n"
        _, refs = _extract_py(source)
        # Imports are emitted as refs with ref_type='imports'
        import_refs = {r["to_symbol_name"] for r in refs if r["ref_type"] == "imports"}
        assert import_refs, "import refs missing from baseline extraction"


# ---------------------------------------------------------------------------
# FB404 — TypeScript object-literal const
# ---------------------------------------------------------------------------


class TestTypeScriptObjectLiteralMethods:
    def test_object_literal_methods_extracted(self):
        source = (
            "export const adapter = {\n"
            "  fetch() { return 1 },\n"
            "  save(x) { return x },\n"
            "};\n"
        )
        symbols, _ = _extract_ts(source)
        methods = _names(symbols, kind="method")
        assert {"fetch", "save"} <= methods, (
            f"Object-literal methods missing; got methods={methods} all={_names(symbols)}"
        )

    def test_typed_object_literal_methods_extracted(self):
        # const with a type annotation — same shape as dashboardAdapter.ts
        source = (
            "export const dashboardAdapter: DashboardAdapter = {\n"
            "  loadData() { return null },\n"
            "  saveData(d) { return d },\n"
            "  refresh() { return true },\n"
            "  reset() { },\n"
            "};\n"
        )
        symbols, _ = _extract_ts(source)
        methods = _names(symbols, kind="method")
        assert {"loadData", "saveData", "refresh", "reset"} <= methods, (
            f"Typed-object-literal methods missing; got methods={methods}"
        )


# ---------------------------------------------------------------------------
# TypeScript regression — existing patterns intact
# ---------------------------------------------------------------------------


class TestTypeScriptBaselineRegression:
    def test_arrow_function_const_still_extracted(self):
        source = "export const Trading = () => null;\n"
        symbols, _ = _extract_ts(source)
        funcs = _names(symbols, kind="function")
        assert "Trading" in funcs, f"Arrow-function const missing; got {funcs}"

    def test_function_declaration_still_extracted(self):
        source = "export function add(a: number, b: number): number { return a + b; }\n"
        symbols, _ = _extract_ts(source)
        assert "add" in _names(symbols, kind="function")

    def test_class_with_method_still_extracted(self):
        source = (
            "export class Foo {\n"
            "  bar() { return 1 }\n"
            "}\n"
        )
        symbols, _ = _extract_ts(source)
        assert "Foo" in _names(symbols, kind="class")
        assert "bar" in _names(symbols, kind="method")

    def test_call_expression_const_still_extracted(self):
        source = "const router = createRouter({});\n"
        symbols, _ = _extract_ts(source)
        assert "router" in _names(symbols, kind="variable")


# ---------------------------------------------------------------------------
# FB405 — TypeScript barrel re-exports
# ---------------------------------------------------------------------------


class TestTypeScriptBarrelReExports:
    def test_export_star_creates_re_exports_ref(self):
        # Pure star re-export barrel.
        source = "export * from './foo';\n"
        symbols, refs = _extract_ts(source)
        rex = [r for r in refs if r["ref_type"] == "re_exports"]
        assert rex, f"expected re_exports refs; got refs={refs}"
        # Star is encoded as '<path>:*'
        names = {r["to_symbol_name"] for r in rex}
        assert "./foo:*" in names, f"missing star ref './foo:*'; got {names}"

    def test_named_export_creates_re_exports_refs(self):
        source = "export { foo, bar } from './baz';\n"
        symbols, refs = _extract_ts(source)
        rex = [r for r in refs if r["ref_type"] == "re_exports"]
        assert rex, "expected re_exports refs for named export"
        names = {r["to_symbol_name"] for r in rex}
        assert {"./baz:foo", "./baz:bar"} <= names, (
            f"named re_exports missing; got {names}"
        )

    def test_barrel_emits_synthetic_module_symbol(self):
        # The synthetic kind='module' symbol anchors re_exports refs (FK).
        source = "export * from './x';\nexport { foo } from './y';\n"
        symbols, refs = _extract_ts(source)
        modules = [s for s in symbols if s["kind"] == "module"]
        assert len(modules) == 1, f"expected 1 module anchor; got {len(modules)}"
        module_id = modules[0]["symbol_id"]
        rex = [r for r in refs if r["ref_type"] == "re_exports"]
        # All re_exports refs must originate from the synthetic module symbol.
        assert all(r["from_symbol_id"] == module_id for r in rex), (
            "re_exports refs must anchor on the synthetic module symbol"
        )

    def test_mixed_file_with_real_symbols_no_anchor(self):
        # File has real exports; no re-exports → no synthetic module symbol.
        source = "export function add(a: number, b: number) { return a + b; }\n"
        symbols, refs = _extract_ts(source)
        modules = [s for s in symbols if s["kind"] == "module"]
        assert not modules, "no synthetic module symbol when no re-exports"
        rex = [r for r in refs if r["ref_type"] == "re_exports"]
        assert not rex


# ---------------------------------------------------------------------------
# FB403 — Object-method dispatch: receiver expression captured in calls
# ---------------------------------------------------------------------------


class TestTypeScriptObjectMethodDispatch:
    def test_object_method_call_captures_receiver(self):
        # Inside an exported function, call userStore.fetch().
        source = (
            "export function loadUser() {\n"
            "  return userStore.fetch();\n"
            "}\n"
        )
        symbols, refs = _extract_ts(source)
        calls = [r for r in refs if r["ref_type"] == "calls"]
        names = {r["to_symbol_name"] for r in calls}
        # Pre-FB403 behaviour: only 'fetch'. Post-FB403: full receiver path.
        assert "userStore.fetch" in names, (
            f"FB403 — receiver expression not captured; got {names}"
        )

    def test_chained_member_call_captures_full_path(self):
        # Multi-segment receiver: a.b.c.method().
        source = (
            "export function outer() {\n"
            "  return services.user.fetch();\n"
            "}\n"
        )
        symbols, refs = _extract_ts(source)
        calls = [r for r in refs if r["ref_type"] == "calls"]
        names = {r["to_symbol_name"] for r in calls}
        assert "services.user.fetch" in names, (
            f"multi-segment receiver missing; got {names}"
        )

    def test_bare_function_call_unchanged(self):
        # Existing behaviour: bare foo() still records 'foo'.
        source = (
            "export function caller() {\n"
            "  return foo(1, 2);\n"
            "}\n"
        )
        symbols, refs = _extract_ts(source)
        calls = [r for r in refs if r["ref_type"] == "calls"]
        names = {r["to_symbol_name"] for r in calls}
        assert "foo" in names


# ---------------------------------------------------------------------------
# Drift events (claude.drift_events, target_kind='symbol')
# ---------------------------------------------------------------------------
#
# Live DB tests — exercise the full index_project flow against a temp
# fixture project and a temp directory of files. Skipped when DATABASE_URI
# is unset or psycopg isn't installed so a parser-only test run still
# passes.
#
# These tests use a fresh project per test so the drift_events the
# indexer writes can be queried without touching production data.


def _have_postgres() -> bool:
    """Probe for a working DB connection. Uses config.get_db_connection
    so it picks up DATABASE_URI / POSTGRES_PASSWORD via the same path
    the indexer uses."""
    try:
        import psycopg  # noqa: F401
    except ImportError:
        try:
            import psycopg2  # noqa: F401
        except ImportError:
            return False
    try:
        from config import get_db_connection  # noqa: WPS433
        conn = get_db_connection(strict=False)
        if conn is None:
            return False
        conn.close()
        return True
    except Exception:
        return False


_REQUIRES_DB = pytest.mark.skipif(
    not _have_postgres(),
    reason="postgres unavailable — skipping live drift tests",
)


@pytest.fixture
def drift_fixture_project(tmp_path):
    """
    Create an isolated project and source directory for drift tests.

    Yields (project_name, project_id, project_dir). On teardown, deletes
    drift_events, code_references, code_symbols, code_file_hashes, and
    the project row.
    """
    if not _have_postgres():
        pytest.skip("DB unavailable")
    # Lazy import — keeps the module importable when DB isn't.
    from config import get_db_connection  # noqa: WPS433

    project_name = f"drift_test_{uuid.uuid4().hex[:8]}"
    project_id = str(uuid.uuid4())
    project_dir = tmp_path / project_name
    project_dir.mkdir()

    conn = get_db_connection(strict=True)
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO claude.projects (project_id, project_name, status, created_at)
                    VALUES (%s, %s, 'active', now())
                    """,
                    (project_id, project_name),
                )
            except Exception:
                conn.rollback()
                with conn.cursor() as cur2:
                    cur2.execute(
                        "INSERT INTO claude.projects (project_id, project_name) VALUES (%s, %s)",
                        (project_id, project_name),
                    )
        conn.commit()
    finally:
        conn.close()

    yield project_name, project_id, project_dir

    # Teardown
    conn = get_db_connection(strict=True)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM claude.drift_events WHERE target_project = %s",
                (project_id,),
            )
            cur.execute(
                """
                DELETE FROM claude.code_references
                WHERE from_symbol_id IN (
                    SELECT symbol_id FROM claude.code_symbols WHERE project_id = %s
                )
                """,
                (project_id,),
            )
            cur.execute(
                "DELETE FROM claude.code_symbols WHERE project_id = %s",
                (project_id,),
            )
            cur.execute(
                "DELETE FROM claude.code_file_hashes WHERE project_id = %s",
                (project_id,),
            )
            cur.execute(
                "DELETE FROM claude.projects WHERE project_id = %s",
                (project_id,),
            )
        conn.commit()
    finally:
        conn.close()


def _count_drift_events(project_id: str, kind: str = None) -> int:
    """Count drift_events rows for a project (optionally filtered by kind)."""
    from config import get_db_connection  # noqa: WPS433
    conn = get_db_connection(strict=True)
    try:
        with conn.cursor() as cur:
            if kind:
                cur.execute(
                    """
                    SELECT COUNT(*) AS n FROM claude.drift_events
                    WHERE target_kind = 'symbol'
                      AND target_project = %s AND kind = %s
                    """,
                    (project_id, kind),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*) AS n FROM claude.drift_events
                    WHERE target_kind = 'symbol' AND target_project = %s
                    """,
                    (project_id,),
                )
            row = cur.fetchone()
            return int(row["n"])
    finally:
        conn.close()


def _fetch_drift_events(project_id: str) -> list[dict]:
    """Return all drift_events rows for a project (target_kind='symbol')."""
    from config import get_db_connection  # noqa: WPS433
    conn = get_db_connection(strict=True)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, target_id, kind, delta, detected_at
                FROM claude.drift_events
                WHERE target_kind = 'symbol' AND target_project = %s
                ORDER BY detected_at
                """,
                (project_id,),
            )
            return list(cur.fetchall())
    finally:
        conn.close()


@_REQUIRES_DB
class TestDriftEventEmission:
    """End-to-end drift detection in the indexer."""

    def test_signature_change_emits_drift_event(self, drift_fixture_project):
        # Given: a fixture project with a single Python file
        project_name, project_id, project_dir = drift_fixture_project
        f = project_dir / "module.py"
        f.write_text("def foo(x):\n    return x\n", encoding="utf-8")

        # First index: establishes the baseline. No drift expected
        # (fresh symbols don't fire events).
        ci.index_project(project_name, str(project_dir), force_full=False)
        baseline = _count_drift_events(project_id)
        assert baseline == 0, (
            f"fresh index should emit no drift events; got {baseline}"
        )

        # Edit the function signature
        f.write_text("def foo(x, y):\n    return x + y\n", encoding="utf-8")

        # Second index: should emit exactly one signature_change event
        ci.index_project(project_name, str(project_dir), force_full=False)
        events = _fetch_drift_events(project_id)
        sig_changes = [e for e in events if e["kind"] == "signature_change"]
        assert len(sig_changes) == 1, (
            f"expected 1 signature_change event for foo; got {len(sig_changes)} — "
            f"all events: {[(e['kind'], e['delta']) for e in events]}"
        )
        delta = sig_changes[0]["delta"]
        # delta is jsonb -> dict in psycopg's row factory
        assert "old_signature" in delta and "new_signature" in delta
        assert "x" in delta["old_signature"]
        assert "y" in delta["new_signature"]
        assert delta.get("name") == "foo"

    def test_unchanged_symbol_emits_no_drift_event(self, drift_fixture_project):
        project_name, project_id, project_dir = drift_fixture_project
        f = project_dir / "stable.py"
        f.write_text("def stable_fn(x):\n    return x * 2\n", encoding="utf-8")

        ci.index_project(project_name, str(project_dir), force_full=False)
        # Re-index without changing the file. With incremental mode the
        # file gets skipped on hash match — no drift either way. With
        # force_full the file is re-parsed; signature unchanged ⇒ no event.
        ci.index_project(project_name, str(project_dir), force_full=True)

        events = _fetch_drift_events(project_id)
        assert len(events) == 0, (
            f"unchanged code should emit no drift events; got "
            f"{[(e['kind'], e['delta']) for e in events]}"
        )

    def test_new_symbol_emits_no_drift_event(self, drift_fixture_project):
        project_name, project_id, project_dir = drift_fixture_project
        f = project_dir / "growing.py"
        f.write_text("def existing(x):\n    return x\n", encoding="utf-8")

        ci.index_project(project_name, str(project_dir), force_full=False)
        # Add a NEW function. The existing one is unchanged.
        f.write_text(
            "def existing(x):\n    return x\n"
            "def added_later(y):\n    return y * 3\n",
            encoding="utf-8",
        )
        ci.index_project(project_name, str(project_dir), force_full=False)

        events = _fetch_drift_events(project_id)
        assert len(events) == 0, (
            f"adding a new symbol must not emit drift events for it; got "
            f"{[(e['kind'], e['delta']) for e in events]}"
        )

    def test_stale_cleanup_emits_removed_drift_event(self, drift_fixture_project):
        project_name, project_id, project_dir = drift_fixture_project
        f = project_dir / "doomed.py"
        f.write_text(
            "def alpha(x):\n    return x\n"
            "def beta(y):\n    return y\n",
            encoding="utf-8",
        )

        ci.index_project(project_name, str(project_dir), force_full=False)
        baseline = _count_drift_events(project_id)
        assert baseline == 0

        # Delete the file from disk
        f.unlink()

        # Re-index — the file is no longer discovered, so cleanup_stale
        # picks it up and emits a removed event for each of its symbols.
        ci.index_project(project_name, str(project_dir), force_full=False)

        events = _fetch_drift_events(project_id)
        removed = [e for e in events if e["kind"] == "removed"]
        assert len(removed) >= 2, (
            f"expected at least 2 removed events (alpha + beta); got {len(removed)} — "
            f"all events: {[(e['kind'], e['delta']) for e in events]}"
        )
        names = {e["delta"].get("name") for e in removed}
        assert {"alpha", "beta"} <= names, (
            f"removed events should cover alpha and beta; got names={names}"
        )
        # All removed deltas must carry the stale_cleanup reason marker
        for e in removed:
            assert e["delta"].get("reason") == "stale_cleanup"

    def test_drift_emit_is_idempotent(self, drift_fixture_project):
        # Re-running the indexer on the same change MUST NOT duplicate
        # events. delta_hash + NOT EXISTS guard handles this.
        project_name, project_id, project_dir = drift_fixture_project
        f = project_dir / "idempotent.py"
        f.write_text("def fn(a):\n    return a\n", encoding="utf-8")

        ci.index_project(project_name, str(project_dir), force_full=False)
        # Change the signature
        f.write_text("def fn(a, b):\n    return a + b\n", encoding="utf-8")
        ci.index_project(project_name, str(project_dir), force_full=False)
        first_count = _count_drift_events(project_id, kind="signature_change")
        assert first_count == 1

        # Re-index with --full so the file is re-parsed even though
        # its hash matches. The drift event must NOT duplicate.
        ci.index_project(project_name, str(project_dir), force_full=True)
        second_count = _count_drift_events(project_id, kind="signature_change")
        assert second_count == 1, (
            f"drift event duplicated on re-run; first={first_count}, "
            f"second={second_count}"
        )
