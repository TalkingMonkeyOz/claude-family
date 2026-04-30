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
