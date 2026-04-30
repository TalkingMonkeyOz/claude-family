#!/usr/bin/env python3
"""
Code Knowledge Graph Indexer — Parse and index project source files into PostgreSQL.

Walks a project directory, parses source files with tree-sitter, extracts symbols
(functions, classes, methods, etc.) and cross-references, and stores them in:
  - claude.code_symbols: symbol definitions with optional embeddings
  - claude.code_references: call/import/inheritance relationships between symbols

Supports Python, TypeScript, JavaScript, C#, and Rust via tree_sitter_language_pack.

Features:
  - Incremental indexing: SHA-256 hash comparison skips unchanged files
  - Batch embedding: via embedding_provider abstraction (FastEmbed or Voyage AI) in batches of 100
  - Stale cleanup: removes symbols for files no longer on disk
  - Cross-file reference resolution: links to_symbol_name → symbol_id post-index
  - Fail-open: parse errors and embedding failures are logged and skipped

Usage:
    python code_indexer.py <project_name> <project_path> [--full]

Options:
    --full    Force re-index all files (ignores hash cache)
"""

import argparse
import hashlib
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging — configure before any other imports that might log
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("code_indexer")

# ---------------------------------------------------------------------------
# Config / DB
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).parent))
from config import get_db_connection  # noqa: E402
from embedding_provider import embed_batch as _provider_embed_batch  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCLUDE_DIRS: set[str] = {
    "node_modules", ".git", "__pycache__", "bin", "obj",
    "target", "dist", ".venv", "venv", ".claude",
    "archive", "backups", "output", "logs", "test-results", "handoff",
}

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py":  "python",
    ".ts":  "typescript",
    ".tsx": "typescript",
    ".js":  "javascript",
    ".jsx": "javascript",
    ".cs":  "c_sharp",
    ".rs":  "rust",
}

EMBEDDING_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Data containers (plain dicts for easy batching)
# ---------------------------------------------------------------------------

def _new_symbol(
    *,
    symbol_id: str,
    project_id: str,
    name: str,
    kind: str,
    file_path: str,
    line_number: int,
    end_line: int,
    scope: str,
    visibility: str,
    signature: str,
    parent_symbol_id: Optional[str],
    file_hash: str,
    language: str,
) -> dict:
    return {
        "symbol_id": symbol_id,
        "project_id": project_id,
        "name": name,
        "kind": kind,
        "file_path": file_path,
        "line_number": line_number,
        "end_line": end_line,
        "scope": scope,
        "visibility": visibility,
        "signature": signature,
        "parent_symbol_id": parent_symbol_id,
        "file_hash": file_hash,
        "language": language,
    }


def _new_ref(
    *,
    from_symbol_id: str,
    to_symbol_id: Optional[str],
    to_symbol_name: str,
    ref_type: str,
) -> dict:
    return {
        "ref_id": str(uuid.uuid4()),
        "from_symbol_id": from_symbol_id,
        "to_symbol_id": to_symbol_id,
        "to_symbol_name": to_symbol_name,
        "ref_type": ref_type,
    }


# ---------------------------------------------------------------------------
# File utilities
# ---------------------------------------------------------------------------

def compute_sha256(path: Path) -> str:
    """Return hex SHA-256 of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def discover_files(project_path: Path) -> list[Path]:
    """Recursively collect source files, excluding known non-source directories."""
    results: list[Path] = []
    extensions = set(EXTENSION_TO_LANGUAGE.keys())

    def _walk(directory: Path) -> None:
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in EXCLUDE_DIRS or entry.name.startswith("."):
                    continue
                _walk(entry)
            elif entry.is_file() and entry.suffix in extensions:
                results.append(entry)

    _walk(project_path)
    return results


# ---------------------------------------------------------------------------
# Tree-sitter helpers
# ---------------------------------------------------------------------------

def _get_parser(language: str):
    """Return a tree-sitter parser for the given language name, or None."""
    try:
        from tree_sitter_language_pack import get_parser  # type: ignore
        return get_parser(language)
    except Exception as exc:
        logger.warning("No tree-sitter parser for %s: %s", language, exc)
        return None


def _node_text(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _child_by_type(node, *types: str):
    for child in node.children:
        if child.type in types:
            return child
    return None


def _children_by_type(node, *types: str):
    return [c for c in node.children if c.type in types]


# ---------------------------------------------------------------------------
# Language-specific extractors
# ---------------------------------------------------------------------------

# ---- Python -----------------------------------------------------------------

def _extract_python(
    tree,
    source_bytes: bytes,
    file_path: str,
    project_id: str,
    file_hash: str,
) -> tuple[list[dict], list[dict]]:
    """Extract Python symbols and references from a parsed tree-sitter tree."""
    symbols: list[dict] = []
    refs: list[dict] = []
    # name → symbol_id for parent resolution within this file
    class_ids: dict[str, str] = {}

    def _params(params_node) -> str:
        parts: list[str] = []
        for child in params_node.children:
            if child.type in ("identifier", "typed_parameter", "typed_default_parameter",
                               "default_parameter", "list_splat_pattern", "dictionary_splat_pattern"):
                parts.append(_node_text(child, source_bytes))
        return ", ".join(parts)

    def _decorators(node) -> list[str]:
        decs = []
        for child in node.children:
            if child.type == "decorator":
                decs.append(_node_text(child, source_bytes).lstrip("@").split("(")[0].strip())
        return decs

    def _process_node(node, parent_class_id: Optional[str] = None, scope: str = "module"):
        for child in node.children:
            if child.type == "decorated_definition":
                # @decorator wraps function_definition / class_definition.
                # Recurse into the wrapper so the inner def/class is processed;
                # _decorators(child.parent) on the inner node will then find the
                # enclosing decorated_definition and capture the decorator names.
                _process_node(child, parent_class_id=parent_class_id, scope=scope)
                continue
            if child.type == "class_definition":
                name_node = _child_by_type(child, "identifier")
                if not name_node:
                    continue
                cname = _node_text(name_node, source_bytes)
                bases_node = _child_by_type(child, "argument_list")
                bases_text = _node_text(bases_node, source_bytes).strip("()") if bases_node else ""
                sig = f"class {cname}({bases_text})" if bases_text else f"class {cname}"
                sym_id = str(uuid.uuid4())
                class_ids[cname] = sym_id
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=cname,
                    kind="class",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility="public" if not cname.startswith("_") else "private",
                    signature=sig,
                    parent_symbol_id=parent_class_id,
                    file_hash=file_hash,
                    language="python",
                ))
                # Extract inheritance refs
                if bases_node:
                    for base in bases_node.children:
                        if base.type in ("identifier", "attribute"):
                            refs.append(_new_ref(
                                from_symbol_id=sym_id,
                                to_symbol_id=None,
                                to_symbol_name=_node_text(base, source_bytes),
                                ref_type="extends",
                            ))
                # Recurse into class body
                body = _child_by_type(child, "block")
                if body:
                    _process_node(body, parent_class_id=sym_id, scope=cname)

            elif child.type == "function_definition":
                name_node = _child_by_type(child, "identifier")
                if not name_node:
                    continue
                fname = _node_text(name_node, source_bytes)
                params_node = _child_by_type(child, "parameters")
                params_text = _params(params_node) if params_node else ""
                ret_node = child.child_by_field_name("return_type")
                ret_text = (" -> " + _node_text(ret_node, source_bytes)) if ret_node else ""
                sig = f"def {fname}({params_text}){ret_text}"
                kind = "method" if parent_class_id else "function"
                decs = _decorators(child.parent) if child.parent else []
                vis = "private" if fname.startswith("_") and not fname.startswith("__") else "public"
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=fname,
                    kind=kind,
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=sig,
                    parent_symbol_id=parent_class_id,
                    file_hash=file_hash,
                    language="python",
                ))
                # Collect call references from function body
                body = _child_by_type(child, "block")
                if body:
                    _collect_calls(body, sym_id, refs, source_bytes)

            elif child.type in ("import_statement", "import_from_statement"):
                # Associate imports with a pseudo-caller at module level
                _collect_imports(child, None, refs, source_bytes)

            elif child.type == "expression_statement" and parent_class_id is None:
                # Module-level UPPER_CASE assignments → constant
                assign = _child_by_type(child, "assignment")
                if assign:
                    lhs = assign.child_by_field_name("left")
                    if lhs and lhs.type == "identifier":
                        aname = _node_text(lhs, source_bytes)
                        if aname.isupper():
                            sym_id = str(uuid.uuid4())
                            symbols.append(_new_symbol(
                                symbol_id=sym_id,
                                project_id=project_id,
                                name=aname,
                                kind="constant",
                                file_path=file_path,
                                line_number=assign.start_point[0] + 1,
                                end_line=assign.end_point[0] + 1,
                                scope=scope,
                                visibility="public",
                                signature=f"{aname} = ...",
                                parent_symbol_id=None,
                                file_hash=file_hash,
                                language="python",
                            ))

    def _collect_calls(node, from_sym_id: str, refs: list, source_bytes: bytes):
        """Walk a node tree collecting call_expression nodes."""
        if node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                name = _node_text(func_node, source_bytes).split("(")[0]
                refs.append(_new_ref(
                    from_symbol_id=from_sym_id,
                    to_symbol_id=None,
                    to_symbol_name=name,
                    ref_type="calls",
                ))
        for child in node.children:
            _collect_calls(child, from_sym_id, refs, source_bytes)

    def _collect_imports(node, from_sym_id: Optional[str], refs: list, source_bytes: bytes):
        text = _node_text(node, source_bytes)
        # Extract module name (first identifier after import/from)
        parts = text.replace("import ", " import ").split()
        if parts:
            module = parts[1] if parts[0] in ("from", "import") else parts[0]
            refs.append(_new_ref(
                from_symbol_id=from_sym_id or "module",
                to_symbol_id=None,
                to_symbol_name=module,
                ref_type="imports",
            ))

    _process_node(tree.root_node)
    return symbols, refs


# ---- TypeScript / JavaScript ------------------------------------------------

def _extract_typescript(
    tree,
    source_bytes: bytes,
    file_path: str,
    project_id: str,
    file_hash: str,
    language: str,
) -> tuple[list[dict], list[dict]]:
    """Extract TypeScript/JavaScript symbols and references."""
    symbols: list[dict] = []
    refs: list[dict] = []
    class_ids: dict[str, str] = {}

    def _is_exported(node) -> bool:
        parent = node.parent
        return parent is not None and parent.type == "export_statement"

    def _params_text(params_node) -> str:
        if not params_node:
            return ""
        return _node_text(params_node, source_bytes).strip("()")

    def _process_node(node, parent_class_id: Optional[str] = None, scope: str = "module"):
        for child in node.children:
            t = child.type

            if t == "function_declaration":
                name_node = _child_by_type(child, "identifier")
                if not name_node:
                    continue
                fname = _node_text(name_node, source_bytes)
                params = _child_by_type(child, "formal_parameters")
                ret = child.child_by_field_name("return_type")
                ret_text = (": " + _node_text(ret, source_bytes).lstrip(": ")) if ret else ""
                sig = f"function {fname}({_params_text(params)}){ret_text}"
                exported = _is_exported(child)
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=fname,
                    kind="function",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility="public" if exported else "private",
                    signature=sig,
                    parent_symbol_id=parent_class_id,
                    file_hash=file_hash,
                    language=language,
                ))
                body = _child_by_type(child, "statement_block")
                if body:
                    _collect_calls_ts(body, sym_id, refs, source_bytes)

            elif t == "class_declaration":
                name_node = _child_by_type(child, "type_identifier", "identifier")
                if not name_node:
                    continue
                cname = _node_text(name_node, source_bytes)
                # Detect extends
                heritage = _child_by_type(child, "class_heritage")
                extends_clause = _child_by_type(heritage, "extends_clause") if heritage else None
                implements_clause = _child_by_type(heritage, "implements_clause") if heritage else None
                exported = _is_exported(child)
                sym_id = str(uuid.uuid4())
                class_ids[cname] = sym_id
                sig_parts = [f"class {cname}"]
                if extends_clause:
                    ext_name = _node_text(extends_clause, source_bytes).replace("extends ", "")
                    sig_parts.append(f"extends {ext_name.split()[0]}")
                    refs.append(_new_ref(
                        from_symbol_id=sym_id,
                        to_symbol_id=None,
                        to_symbol_name=ext_name.split()[0],
                        ref_type="extends",
                    ))
                if implements_clause:
                    impl_text = _node_text(implements_clause, source_bytes).replace("implements ", "")
                    sig_parts.append(f"implements {impl_text}")
                    for iname in impl_text.split(","):
                        refs.append(_new_ref(
                            from_symbol_id=sym_id,
                            to_symbol_id=None,
                            to_symbol_name=iname.strip().split("<")[0],
                            ref_type="implements",
                        ))
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=cname,
                    kind="class",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility="public" if exported else "private",
                    signature=" ".join(sig_parts),
                    parent_symbol_id=parent_class_id,
                    file_hash=file_hash,
                    language=language,
                ))
                body = _child_by_type(child, "class_body")
                if body:
                    _process_node(body, parent_class_id=sym_id, scope=cname)

            elif t == "method_definition":
                name_node = _child_by_type(child, "property_identifier", "identifier")
                if not name_node:
                    continue
                mname = _node_text(name_node, source_bytes)
                params = _child_by_type(child, "formal_parameters")
                ret = child.child_by_field_name("return_type")
                ret_text = (": " + _node_text(ret, source_bytes).lstrip(": ")) if ret else ""
                modifiers = [c.type for c in child.children
                             if c.type in ("public", "private", "protected", "static", "async")]
                vis = "private" if "private" in modifiers else "public"
                sig = f"{' '.join(modifiers)} {mname}({_params_text(params)}){ret_text}".strip()
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=mname,
                    kind="method",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=sig,
                    parent_symbol_id=parent_class_id,
                    file_hash=file_hash,
                    language=language,
                ))
                body = _child_by_type(child, "statement_block")
                if body:
                    _collect_calls_ts(body, sym_id, refs, source_bytes)

            elif t == "interface_declaration":
                name_node = _child_by_type(child, "type_identifier", "identifier")
                if not name_node:
                    continue
                iname = _node_text(name_node, source_bytes)
                exported = _is_exported(child)
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=iname,
                    kind="interface",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility="public" if exported else "private",
                    signature=f"interface {iname}",
                    parent_symbol_id=None,
                    file_hash=file_hash,
                    language=language,
                ))

            elif t == "type_alias_declaration":
                name_node = _child_by_type(child, "type_identifier", "identifier")
                if not name_node:
                    continue
                tname = _node_text(name_node, source_bytes)
                exported = _is_exported(child)
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=tname,
                    kind="type_alias",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility="public" if exported else "private",
                    signature=f"type {tname} = ...",
                    parent_symbol_id=None,
                    file_hash=file_hash,
                    language=language,
                ))

            elif t == "enum_declaration":
                name_node = _child_by_type(child, "identifier")
                if not name_node:
                    continue
                ename = _node_text(name_node, source_bytes)
                exported = _is_exported(child)
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=ename,
                    kind="enum",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility="public" if exported else "private",
                    signature=f"enum {ename}",
                    parent_symbol_id=None,
                    file_hash=file_hash,
                    language=language,
                ))

            elif t in ("lexical_declaration", "variable_declaration"):
                # Handle const/let/var declarations — critical for:
                # - Arrow function components: const Trading = () => { ... }
                # - Custom hooks: const useToggleKillSwitch = () => { ... }
                # - HOCs and wrappers: const withAuth = (Component) => ...
                for declarator in child.children:
                    if declarator.type != "variable_declarator":
                        continue
                    decl_name_node = _child_by_type(declarator, "identifier")
                    if not decl_name_node:
                        continue
                    decl_name = _node_text(decl_name_node, source_bytes)
                    # Find the value (right side of =)
                    value_node = declarator.child_by_field_name("value")
                    if not value_node:
                        continue
                    # Arrow functions and function expressions → extract as function
                    if value_node.type in ("arrow_function", "function_expression", "function"):
                        params = _child_by_type(value_node, "formal_parameters")
                        ret = value_node.child_by_field_name("return_type")
                        ret_text = (": " + _node_text(ret, source_bytes).lstrip(": ")) if ret else ""
                        sig = f"const {decl_name} = ({_params_text(params)}){ret_text} => ..."
                        exported = _is_exported(child)
                        sym_id = str(uuid.uuid4())
                        symbols.append(_new_symbol(
                            symbol_id=sym_id,
                            project_id=project_id,
                            name=decl_name,
                            kind="function",
                            file_path=file_path,
                            line_number=child.start_point[0] + 1,
                            end_line=child.end_point[0] + 1,
                            scope=scope,
                            visibility="public" if exported else "private",
                            signature=sig,
                            parent_symbol_id=parent_class_id,
                            file_hash=file_hash,
                            language=language,
                        ))
                        body = _child_by_type(value_node, "statement_block")
                        if body:
                            _collect_calls_ts(body, sym_id, refs, source_bytes)
                    # Object literals assigned to const (e.g., const adapter = { fetch(){}, save(){} })
                    # Recurse into the object so nested method_definition nodes are extracted.
                    elif value_node.type in ("object", "object_pattern"):
                        _process_node(value_node, parent_class_id=parent_class_id, scope=scope)
                    # Call expressions assigned to const (e.g., const router = createRouter(...))
                    elif value_node.type == "call_expression":
                        exported = _is_exported(child)
                        sym_id = str(uuid.uuid4())
                        func_node = value_node.child_by_field_name("function")
                        func_name = _node_text(func_node, source_bytes) if func_node else "?"
                        symbols.append(_new_symbol(
                            symbol_id=sym_id,
                            project_id=project_id,
                            name=decl_name,
                            kind="variable",
                            file_path=file_path,
                            line_number=child.start_point[0] + 1,
                            end_line=child.end_point[0] + 1,
                            scope=scope,
                            visibility="public" if exported else "private",
                            signature=f"const {decl_name} = {func_name}(...)",
                            parent_symbol_id=parent_class_id,
                            file_hash=file_hash,
                            language=language,
                        ))
                        refs.append(_new_ref(
                            from_symbol_id=sym_id,
                            to_symbol_id=None,
                            to_symbol_name=func_name,
                            ref_type="calls",
                        ))

            elif t == "export_statement":
                # Recurse into export_statement to catch exported declarations
                _process_node(child, parent_class_id=parent_class_id, scope=scope)

            elif t in ("import_statement", "import_declaration"):
                src = _child_by_type(child, "string")
                module = _node_text(src, source_bytes).strip("\"'") if src else ""
                if module:
                    refs.append(_new_ref(
                        from_symbol_id="module",
                        to_symbol_id=None,
                        to_symbol_name=module,
                        ref_type="imports",
                    ))

            else:
                # Generic recursion for blocks, program root, etc.
                if child.child_count > 0:
                    _process_node(child, parent_class_id=parent_class_id, scope=scope)

    def _collect_calls_ts(node, from_sym_id: str, refs: list, source_bytes: bytes):
        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func:
                # FB403 — capture receiver expression for object-method dispatch
                # (e.g., userStore.fetch() — record "userStore.fetch", not just "fetch").
                # Cross-module dispatch resolution can then split on '.' and try to
                # resolve the receiver to a class. If the call is bare (foo()),
                # there's no '.' and we record the function name directly.
                # John's "no truncation" principle: capture full receiver text up to
                # the last '(' so multi-segment receivers (a.b.c.method) survive.
                full = _node_text(func, source_bytes).split("(")[0]
                # Strip generic type params like foo<T>
                if "<" in full:
                    full = full.split("<")[0]
                refs.append(_new_ref(
                    from_symbol_id=from_sym_id,
                    to_symbol_id=None,
                    to_symbol_name=full,
                    ref_type="calls",
                ))
        for child in node.children:
            _collect_calls_ts(child, from_sym_id, refs, source_bytes)

    # ---- FB405: barrel re-export detection -----------------------------
    # Pattern A: `export * from './foo'` — appears in tree-sitter as
    #            export_statement with an export_clause OR a string source.
    # Pattern B: `export { foo, bar } from './foo'` — export_statement with
    #            an export_clause containing export_specifier nodes plus a
    #            string source.
    # We capture each as a ref with ref_type='re_exports'. Storage trick:
    # refs need a real from_symbol_id (FK), so when we encounter the first
    # re-export in a file we lazily emit a synthetic module-level symbol
    # named after the file and anchor every re_export ref to it. This
    # uses ONLY the existing schema (FB405 spec: no new columns).
    barrel_module_id: Optional[str] = None

    def _ensure_barrel_module(line_no: int) -> str:
        nonlocal barrel_module_id
        if barrel_module_id is not None:
            return barrel_module_id
        sym_id = str(uuid.uuid4())
        # File basename without extension as symbol name
        bare = file_path.replace("\\", "/").rsplit("/", 1)[-1]
        bare = bare.rsplit(".", 1)[0] or bare
        symbols.append(_new_symbol(
            symbol_id=sym_id,
            project_id=project_id,
            name=bare,
            kind="module",
            file_path=file_path,
            line_number=max(line_no, 1),
            end_line=max(line_no, 1),
            scope="module",
            visibility="public",
            signature=f"// barrel module {bare}",
            parent_symbol_id=None,
            file_hash=file_hash,
            language=language,
        ))
        barrel_module_id = sym_id
        return sym_id

    def _collect_re_exports(node) -> None:
        # Walk top-level children for export_statement nodes whose source is
        # a string literal (the `from './x'` part).
        for child in node.children:
            if child.type != "export_statement":
                continue
            # Find the `from "./x"` source string
            src = _child_by_type(child, "string")
            if not src:
                continue
            module_path = _node_text(src, source_bytes).strip("\"'")
            # Determine star vs named
            # `export * from "./x"` — has a `*` token but no export_clause
            has_star = any(c.type == "*" or _node_text(c, source_bytes) == "*"
                           for c in child.children)
            export_clause = _child_by_type(child, "export_clause")
            from_id = _ensure_barrel_module(child.start_point[0] + 1)
            if has_star and not export_clause:
                refs.append(_new_ref(
                    from_symbol_id=from_id,
                    to_symbol_id=None,
                    to_symbol_name=f"{module_path}:*",
                    ref_type="re_exports",
                ))
            elif export_clause:
                for spec in export_clause.children:
                    if spec.type != "export_specifier":
                        continue
                    name_node = _child_by_type(spec, "identifier")
                    spec_name = _node_text(name_node, source_bytes) if name_node else "?"
                    refs.append(_new_ref(
                        from_symbol_id=from_id,
                        to_symbol_id=None,
                        to_symbol_name=f"{module_path}:{spec_name}",
                        ref_type="re_exports",
                    ))

    _process_node(tree.root_node)
    _collect_re_exports(tree.root_node)
    return symbols, refs


# ---- C# ---------------------------------------------------------------------

def _extract_csharp(
    tree,
    source_bytes: bytes,
    file_path: str,
    project_id: str,
    file_hash: str,
) -> tuple[list[dict], list[dict]]:
    symbols: list[dict] = []
    refs: list[dict] = []

    def _visibility(node) -> str:
        for child in node.children:
            if child.type == "modifier":
                text = _node_text(child, source_bytes)
                if text in ("public", "internal", "protected"):
                    return text
                if text == "private":
                    return "private"
        return "private"

    def _process_node(node, parent_class_id: Optional[str] = None, scope: str = "namespace"):
        for child in node.children:
            t = child.type

            if t == "class_declaration":
                name_node = _child_by_type(child, "identifier")
                if not name_node:
                    continue
                cname = _node_text(name_node, source_bytes)
                vis = _visibility(child)
                bases = _child_by_type(child, "base_list")
                sig = f"class {cname}"
                if bases:
                    sig += " : " + _node_text(bases, source_bytes).lstrip(": ")
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=cname,
                    kind="class",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=sig,
                    parent_symbol_id=parent_class_id,
                    file_hash=file_hash,
                    language="c_sharp",
                ))
                body = _child_by_type(child, "declaration_list")
                if body:
                    _process_node(body, parent_class_id=sym_id, scope=cname)

            elif t == "interface_declaration":
                name_node = _child_by_type(child, "identifier")
                if not name_node:
                    continue
                iname = _node_text(name_node, source_bytes)
                vis = _visibility(child)
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=iname,
                    kind="interface",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=f"interface {iname}",
                    parent_symbol_id=None,
                    file_hash=file_hash,
                    language="c_sharp",
                ))

            elif t == "enum_declaration":
                name_node = _child_by_type(child, "identifier")
                if not name_node:
                    continue
                ename = _node_text(name_node, source_bytes)
                vis = _visibility(child)
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=ename,
                    kind="enum",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=f"enum {ename}",
                    parent_symbol_id=None,
                    file_hash=file_hash,
                    language="c_sharp",
                ))

            elif t == "method_declaration":
                name_node = _child_by_type(child, "identifier")
                if not name_node:
                    continue
                mname = _node_text(name_node, source_bytes)
                ret_node = child.child_by_field_name("type")
                ret_text = _node_text(ret_node, source_bytes) if ret_node else "void"
                params_node = _child_by_type(child, "parameter_list")
                params_text = _node_text(params_node, source_bytes) if params_node else "()"
                vis = _visibility(child)
                modifiers = " ".join(
                    _node_text(c, source_bytes)
                    for c in child.children if c.type == "modifier"
                )
                sig = f"{modifiers} {ret_text} {mname}{params_text}".strip()
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=mname,
                    kind="method",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=sig,
                    parent_symbol_id=parent_class_id,
                    file_hash=file_hash,
                    language="c_sharp",
                ))
                body = _child_by_type(child, "block")
                if body:
                    _collect_calls_cs(body, sym_id, refs, source_bytes)

            elif t == "property_declaration":
                name_node = _child_by_type(child, "identifier")
                if not name_node:
                    continue
                pname = _node_text(name_node, source_bytes)
                ret_node = child.child_by_field_name("type")
                ret_text = _node_text(ret_node, source_bytes) if ret_node else ""
                vis = _visibility(child)
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=pname,
                    kind="property",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=f"{vis} {ret_text} {pname} {{ get; set; }}".strip(),
                    parent_symbol_id=parent_class_id,
                    file_hash=file_hash,
                    language="c_sharp",
                ))

            elif t == "using_directive":
                ns_node = _child_by_type(child, "qualified_name", "identifier", "name_equals")
                ns = _node_text(ns_node, source_bytes) if ns_node else ""
                if ns:
                    refs.append(_new_ref(
                        from_symbol_id="module",
                        to_symbol_id=None,
                        to_symbol_name=ns,
                        ref_type="imports",
                    ))

            else:
                if child.child_count > 0:
                    _process_node(child, parent_class_id=parent_class_id, scope=scope)

    def _collect_calls_cs(node, from_sym_id: str, refs: list, source_bytes: bytes):
        if node.type == "invocation_expression":
            func = node.child_by_field_name("expression")
            if func:
                name = _node_text(func, source_bytes).split(".")[-1]
                refs.append(_new_ref(
                    from_symbol_id=from_sym_id,
                    to_symbol_id=None,
                    to_symbol_name=name,
                    ref_type="calls",
                ))
        for child in node.children:
            _collect_calls_cs(child, from_sym_id, refs, source_bytes)

    _process_node(tree.root_node)
    return symbols, refs


# ---- Rust -------------------------------------------------------------------

def _extract_rust(
    tree,
    source_bytes: bytes,
    file_path: str,
    project_id: str,
    file_hash: str,
) -> tuple[list[dict], list[dict]]:
    symbols: list[dict] = []
    refs: list[dict] = []

    def _is_pub(node) -> bool:
        for child in node.children:
            if child.type == "visibility_modifier":
                return _node_text(child, source_bytes).startswith("pub")
        return False

    def _process_node(node, parent_impl_id: Optional[str] = None, scope: str = "crate"):
        for child in node.children:
            t = child.type

            if t == "function_item":
                name_node = _child_by_type(child, "identifier")
                if not name_node:
                    continue
                fname = _node_text(name_node, source_bytes)
                params_node = _child_by_type(child, "parameters")
                params_text = _node_text(params_node, source_bytes) if params_node else "()"
                ret_node = child.child_by_field_name("return_type")
                ret_text = (" -> " + _node_text(ret_node, source_bytes)) if ret_node else ""
                vis = "public" if _is_pub(child) else "private"
                kind = "method" if parent_impl_id else "function"
                sig = f"fn {fname}{params_text}{ret_text}"
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=fname,
                    kind=kind,
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=sig,
                    parent_symbol_id=parent_impl_id,
                    file_hash=file_hash,
                    language="rust",
                ))
                body = _child_by_type(child, "block")
                if body:
                    _collect_calls_rs(body, sym_id, refs, source_bytes)

            elif t == "struct_item":
                name_node = _child_by_type(child, "type_identifier")
                if not name_node:
                    continue
                sname = _node_text(name_node, source_bytes)
                vis = "public" if _is_pub(child) else "private"
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=sname,
                    kind="class",  # treat structs as classes per spec
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=f"struct {sname}",
                    parent_symbol_id=None,
                    file_hash=file_hash,
                    language="rust",
                ))

            elif t == "enum_item":
                name_node = _child_by_type(child, "type_identifier")
                if not name_node:
                    continue
                ename = _node_text(name_node, source_bytes)
                vis = "public" if _is_pub(child) else "private"
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=ename,
                    kind="enum",
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=f"enum {ename}",
                    parent_symbol_id=None,
                    file_hash=file_hash,
                    language="rust",
                ))

            elif t == "trait_item":
                name_node = _child_by_type(child, "type_identifier")
                if not name_node:
                    continue
                tname = _node_text(name_node, source_bytes)
                vis = "public" if _is_pub(child) else "private"
                sym_id = str(uuid.uuid4())
                symbols.append(_new_symbol(
                    symbol_id=sym_id,
                    project_id=project_id,
                    name=tname,
                    kind="interface",  # traits map to interface
                    file_path=file_path,
                    line_number=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    scope=scope,
                    visibility=vis,
                    signature=f"trait {tname}",
                    parent_symbol_id=None,
                    file_hash=file_hash,
                    language="rust",
                ))

            elif t == "impl_item":
                # impl Foo or impl Trait for Foo
                type_node = child.child_by_field_name("type")
                impl_name = _node_text(type_node, source_bytes) if type_node else "impl"
                trait_node = child.child_by_field_name("trait")
                impl_id = str(uuid.uuid4())
                # Emit an extends/implements ref if impl Trait for Struct
                if trait_node and type_node:
                    refs.append(_new_ref(
                        from_symbol_id=impl_id,
                        to_symbol_id=None,
                        to_symbol_name=_node_text(trait_node, source_bytes),
                        ref_type="implements",
                    ))
                body = _child_by_type(child, "declaration_list")
                if body:
                    _process_node(body, parent_impl_id=impl_id, scope=impl_name)

            elif t == "use_declaration":
                path_node = _child_by_type(child, "scoped_identifier", "identifier",
                                            "use_wildcard", "use_list")
                if path_node:
                    refs.append(_new_ref(
                        from_symbol_id="module",
                        to_symbol_id=None,
                        to_symbol_name=_node_text(path_node, source_bytes),
                        ref_type="imports",
                    ))

            else:
                if child.child_count > 0:
                    _process_node(child, parent_impl_id=parent_impl_id, scope=scope)

    def _collect_calls_rs(node, from_sym_id: str, refs: list, source_bytes: bytes):
        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func:
                name = _node_text(func, source_bytes).split("::")[-1].split("(")[0]
                refs.append(_new_ref(
                    from_symbol_id=from_sym_id,
                    to_symbol_id=None,
                    to_symbol_name=name,
                    ref_type="calls",
                ))
        for child in node.children:
            _collect_calls_rs(child, from_sym_id, refs, source_bytes)

    _process_node(tree.root_node)
    return symbols, refs


# ---------------------------------------------------------------------------
# Per-file dispatch
# ---------------------------------------------------------------------------

def parse_file(
    file_path: Path,
    project_id: str,
    file_hash: str,
) -> tuple[list[dict], list[dict]]:
    """Parse a single source file. Returns (symbols, refs) or raises."""
    language = EXTENSION_TO_LANGUAGE[file_path.suffix]
    parser = _get_parser(language)
    if parser is None:
        raise RuntimeError(f"No parser available for language: {language}")

    source_bytes = file_path.read_bytes()
    tree = parser.parse(source_bytes)
    str_path = str(file_path)

    if language == "python":
        return _extract_python(tree, source_bytes, str_path, project_id, file_hash)
    elif language in ("typescript", "javascript"):
        return _extract_typescript(tree, source_bytes, str_path, project_id, file_hash, language)
    elif language == "c_sharp":
        return _extract_csharp(tree, source_bytes, str_path, project_id, file_hash)
    elif language == "rust":
        return _extract_rust(tree, source_bytes, str_path, project_id, file_hash)
    else:
        raise RuntimeError(f"Extractor not implemented for language: {language}")


# ---------------------------------------------------------------------------
# Database I/O
# ---------------------------------------------------------------------------

def get_project_id(conn, project_name: str) -> Optional[str]:
    """Look up project_id by name. Returns None if not found."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT project_id FROM claude.projects WHERE project_name = %s",
            (project_name,),
        )
        row = cur.fetchone()
        return str(row["project_id"]) if row else None


def ensure_hash_table(conn) -> None:
    """Create claude.code_file_hashes if it doesn't exist, and backfill from symbols."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS claude.code_file_hashes (
                project_id UUID NOT NULL REFERENCES claude.projects(project_id),
                file_path TEXT NOT NULL,
                file_hash VARCHAR(64) NOT NULL,
                symbols_count INTEGER DEFAULT 0,
                indexed_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (project_id, file_path)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_hashes_project
                ON claude.code_file_hashes(project_id)
        """)
        # Backfill from existing symbols (idempotent — ON CONFLICT DO NOTHING)
        cur.execute("""
            INSERT INTO claude.code_file_hashes (project_id, file_path, file_hash, symbols_count)
            SELECT project_id, file_path, file_hash, COUNT(*) as symbols_count
            FROM claude.code_symbols
            WHERE file_hash IS NOT NULL
            GROUP BY project_id, file_path, file_hash
            ON CONFLICT (project_id, file_path) DO NOTHING
        """)
        conn.commit()
    logger.info("Hash table ensured (claude.code_file_hashes)")


def get_cached_hashes(conn, project_id: str) -> dict[str, str]:
    """Return {file_path: file_hash} from the dedicated hash tracking table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT file_path, file_hash
            FROM claude.code_file_hashes
            WHERE project_id = %s
            """,
            (project_id,),
        )
        return {row["file_path"]: row["file_hash"] for row in cur.fetchall()}


def upsert_file_hash(conn, project_id: str, file_path: str, file_hash: str, symbols_count: int) -> None:
    """Record that a file was successfully processed, even if it yielded 0 symbols."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO claude.code_file_hashes (project_id, file_path, file_hash, symbols_count, indexed_at)
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (project_id, file_path)
            DO UPDATE SET file_hash = EXCLUDED.file_hash,
                          symbols_count = EXCLUDED.symbols_count,
                          indexed_at = now()
            """,
            (project_id, file_path, file_hash, symbols_count),
        )


def delete_symbols_for_files(conn, file_paths: list[str]) -> int:
    """Delete all symbols (and cascading refs) for the given file paths. Returns count."""
    if not file_paths:
        return 0
    total = 0
    with conn.cursor() as cur:
        for fp in file_paths:
            # Delete refs whose from_symbol_id belongs to this file
            cur.execute(
                """
                DELETE FROM claude.code_references
                WHERE from_symbol_id IN (
                    SELECT symbol_id FROM claude.code_symbols WHERE file_path = %s
                )
                """,
                (fp,),
            )
            cur.execute(
                "DELETE FROM claude.code_symbols WHERE file_path = %s",
                (fp,),
            )
            total += cur.rowcount
    return total


def insert_symbols(conn, symbols: list[dict]) -> None:
    """Batch-insert symbols into claude.code_symbols."""
    if not symbols:
        return
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO claude.code_symbols
                (symbol_id, project_id, name, kind, file_path, line_number, end_line,
                 scope, visibility, signature, parent_symbol_id, file_hash, language,
                 last_indexed_at)
            VALUES
                (%(symbol_id)s, %(project_id)s, %(name)s, %(kind)s, %(file_path)s,
                 %(line_number)s, %(end_line)s, %(scope)s, %(visibility)s, %(signature)s,
                 %(parent_symbol_id)s, %(file_hash)s, %(language)s, NOW())
            ON CONFLICT (symbol_id) DO UPDATE SET
                name = EXCLUDED.name,
                kind = EXCLUDED.kind,
                file_path = EXCLUDED.file_path,
                line_number = EXCLUDED.line_number,
                end_line = EXCLUDED.end_line,
                scope = EXCLUDED.scope,
                visibility = EXCLUDED.visibility,
                signature = EXCLUDED.signature,
                parent_symbol_id = EXCLUDED.parent_symbol_id,
                file_hash = EXCLUDED.file_hash,
                language = EXCLUDED.language,
                last_indexed_at = NOW(),
                updated_at = NOW()
            """,
            symbols,
        )


def insert_refs(conn, refs: list[dict]) -> None:
    """Batch-insert references into claude.code_references, skipping module-level placeholders."""
    if not refs:
        return
    # Strip out refs whose from_symbol_id is the placeholder "module" (no real UUID)
    valid = [r for r in refs if r["from_symbol_id"] != "module"]
    if not valid:
        return
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO claude.code_references
                (ref_id, from_symbol_id, to_symbol_id, to_symbol_name, ref_type)
            VALUES
                (%(ref_id)s, %(from_symbol_id)s, %(to_symbol_id)s, %(to_symbol_name)s, %(ref_type)s)
            ON CONFLICT (ref_id) DO NOTHING
            """,
            valid,
        )


def resolve_cross_file_refs(conn, project_id: str) -> int:
    """
    Attempt to fill in to_symbol_id for unresolved references by matching
    to_symbol_name against known symbol names in the same project.

    FB402 — Cross-language collision fix: only match candidates whose
    language matches the language of the source symbol. Without this
    scoping, a JS function `now()` resolves to a Python `now()` and
    `code_context.callees` becomes nonsense.

    FB403 — Object-method dispatch fix: call collectors now record the
    full receiver expression (e.g., `userStore.fetch`) when present.
    Resolution strategy:
        1. Exact match on full name (e.g., method named `userStore.fetch`).
        2. If `to_symbol_name` contains '.', split on the last '.' and
           match the trailing segment as a method/function name. Same
           language-scope rule applies. This is best-effort — true
           receiver-type tracking is a follow-up FB.
        3. Bare names match on `name` directly (existing behaviour).

    All three passes are idempotent: each only updates rows where
    to_symbol_id IS NULL, so re-runs converge.

    Returns the count of refs updated across all passes.
    """
    total = 0
    with conn.cursor() as cur:
        # Pass 0 — repair pass for cross-language refs left by an older
        # resolver build (FB402). NULL out any 'calls' resolution where
        # the source and target languages disagree so Pass 1 can re-resolve
        # them with the language-scoped query. Idempotent: a clean DB
        # leaves zero rows to update.
        cur.execute(
            """
            UPDATE claude.code_references cr
            SET to_symbol_id = NULL
            FROM claude.code_symbols fs, claude.code_symbols ts
            WHERE cr.from_symbol_id = fs.symbol_id
              AND cr.to_symbol_id = ts.symbol_id
              AND fs.language IS DISTINCT FROM ts.language
              AND fs.project_id = %s
              AND cr.ref_type = 'calls'
            """,
            (project_id,),
        )

        # Pass 1 — exact name match, language-scoped (FB402).
        cur.execute(
            """
            UPDATE claude.code_references cr
            SET to_symbol_id = cs.symbol_id
            FROM claude.code_symbols cs, claude.code_symbols fs
            WHERE cr.to_symbol_id IS NULL
              AND cr.from_symbol_id = fs.symbol_id
              AND cr.to_symbol_name = cs.name
              AND cs.project_id = %s
              AND fs.project_id = %s
              AND cs.language = fs.language
              AND cr.ref_type IN ('calls', 'extends', 'implements')
            """,
            (project_id, project_id),
        )
        total += cur.rowcount

        # Pass 2 — receiver-method dispatch (FB403). When the captured
        # to_symbol_name contains '.', split on the LAST '.' and try the
        # trailing token as a method/function name (still language-scoped).
        # Example: 'userStore.fetch' → match symbol named 'fetch'.
        # We only run this for unresolved refs to avoid clobbering Pass 1.
        cur.execute(
            """
            UPDATE claude.code_references cr
            SET to_symbol_id = cs.symbol_id
            FROM claude.code_symbols cs, claude.code_symbols fs
            WHERE cr.to_symbol_id IS NULL
              AND cr.from_symbol_id = fs.symbol_id
              AND position('.' in cr.to_symbol_name) > 0
              AND cs.name = substring(cr.to_symbol_name from '[^.]+$')
              AND cs.project_id = %s
              AND fs.project_id = %s
              AND cs.language = fs.language
              AND cr.ref_type = 'calls'
            """,
            (project_id, project_id),
        )
        total += cur.rowcount

        return total


def cleanup_stale_symbols(conn, project_id: str, live_paths: set[str]) -> int:
    """Delete symbols whose file_path no longer exists on disk."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT file_path FROM claude.code_symbols WHERE project_id = %s",
            (project_id,),
        )
        db_paths = {row["file_path"] for row in cur.fetchall()}

    stale = db_paths - live_paths
    if not stale:
        return 0

    logger.info("Removing stale symbols for %d deleted files", len(stale))
    deleted = delete_symbols_for_files(conn, list(stale))
    return deleted


# ---------------------------------------------------------------------------
# Embeddings (via embedding_provider abstraction)
# ---------------------------------------------------------------------------

def _embed_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """
    Generate embeddings for a batch of texts using the configured provider.
    Returns a list of embedding vectors (or None entries on error).
    """
    try:
        result = _provider_embed_batch(texts)
        if result is not None:
            return result
    except Exception as exc:
        logger.warning("Batch embedding failed: %s", exc)

    logger.error("Embedding failed for batch of %d texts", len(texts))
    return [None] * len(texts)


def generate_embeddings_for_project(conn, project_id: str) -> int:
    """
    Generate and store embeddings for symbols that have no embedding yet.
    Returns the number of symbols embedded.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT symbol_id, kind, name, file_path, signature
            FROM claude.code_symbols
            WHERE project_id = %s AND embedding IS NULL
            ORDER BY symbol_id
            """,
            (project_id,),
        )
        rows = cur.fetchall()

    if not rows:
        return 0

    logger.info("Generating embeddings for %d symbols", len(rows))
    embedded = 0

    for batch_start in range(0, len(rows), EMBEDDING_BATCH_SIZE):
        batch = rows[batch_start: batch_start + EMBEDDING_BATCH_SIZE]
        texts = [
            "{kind} {name} in {file_path}: {signature}".format(**r)
            for r in batch
        ]
        vectors = _embed_batch(texts)

        updates = [
            (vec, row["symbol_id"])
            for vec, row in zip(vectors, batch)
            if vec is not None
        ]

        if updates:
            with conn.cursor() as cur:
                cur.executemany(
                    "UPDATE claude.code_symbols SET embedding = %s WHERE symbol_id = %s",
                    updates,
                )
            conn.commit()
            embedded += len(updates)

        logger.info(
            "Embedded batch %d-%d (%d successful)",
            batch_start + 1,
            batch_start + len(batch),
            len(updates),
        )

    return embedded


# ---------------------------------------------------------------------------
# Main indexing entry point
# ---------------------------------------------------------------------------

def index_project(
    project_name: str,
    project_path: str,
    force_full: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Index a project's codebase into claude.code_symbols and claude.code_references.

    Args:
        project_name: Registered name in claude.projects.
        project_path: Filesystem root to scan.
        force_full:   When True, re-index every file regardless of hash.
        dry_run:      When True, report what would happen without writing to DB.

    Returns:
        Summary dict with keys: files_scanned, files_indexed, symbols_extracted,
        refs_extracted, refs_resolved, symbols_embedded, stale_deleted.
        In dry_run mode, adds: files_skipped, files_errored, file_details[].
    """
    root = Path(project_path)
    if not root.exists():
        raise FileNotFoundError(f"Project path not found: {project_path}")

    conn = get_db_connection(strict=True)

    try:
        # Ensure hash tracking table exists (idempotent)
        ensure_hash_table(conn)

        project_id = get_project_id(conn, project_name)
        if project_id is None:
            raise ValueError(
                f"Project '{project_name}' not found in claude.projects. "
                "Register it first."
            )

        logger.info("Indexing project '%s' (id=%s) at %s%s",
                     project_name, project_id, root,
                     " [DRY RUN]" if dry_run else "")

        # Discover all source files
        all_files = discover_files(root)
        logger.info("Discovered %d source files", len(all_files))
        live_paths = {str(f) for f in all_files}

        # Load cached hashes for incremental mode
        cached_hashes: dict[str, str] = {} if force_full else get_cached_hashes(conn, project_id)

        stats = {
            "files_scanned": len(all_files),
            "files_indexed": 0,
            "files_skipped": 0,
            "files_errored": 0,
            "symbols_extracted": 0,
            "refs_extracted": 0,
            "refs_resolved": 0,
            "symbols_embedded": 0,
            "stale_deleted": 0,
        }

        # Dry run collects per-file diagnostics
        file_details: list[dict] = [] if dry_run else []

        for file_path in all_files:
            str_fp = str(file_path)
            try:
                new_hash = compute_sha256(file_path)
            except OSError as exc:
                logger.warning("Cannot read %s: %s", str_fp, exc)
                stats["files_errored"] += 1
                if dry_run:
                    file_details.append({"file": str_fp, "status": "read_error", "error": str(exc)})
                continue

            if not force_full and cached_hashes.get(str_fp) == new_hash:
                logger.debug("Skip (unchanged): %s", file_path.name)
                stats["files_skipped"] += 1
                if dry_run:
                    file_details.append({"file": str_fp, "status": "skip_unchanged"})
                continue

            # Dry run: parse but don't write
            if dry_run:
                try:
                    file_symbols, file_refs = parse_file(file_path, project_id, new_hash)
                    file_details.append({
                        "file": str_fp,
                        "status": "would_index",
                        "symbols": len(file_symbols),
                        "refs": len(file_refs),
                    })
                    stats["files_indexed"] += 1
                    stats["symbols_extracted"] += len(file_symbols)
                    stats["refs_extracted"] += len(file_refs)
                except Exception as exc:
                    file_details.append({"file": str_fp, "status": "parse_error", "error": str(exc)})
                    stats["files_errored"] += 1
                continue

            logger.info("Indexing: %s", str_fp)

            # Remove stale symbols for this file before re-inserting
            delete_symbols_for_files(conn, [str_fp])

            try:
                file_symbols, file_refs = parse_file(file_path, project_id, new_hash)
            except Exception as exc:
                logger.warning("Parse failed for %s: %s", str_fp, exc)
                stats["files_errored"] += 1
                continue

            try:
                insert_symbols(conn, file_symbols)
                insert_refs(conn, file_refs)
                # Record hash AFTER successful parse — even for 0-symbol files
                upsert_file_hash(conn, project_id, str_fp, new_hash, len(file_symbols))
                conn.commit()
            except Exception as exc:
                conn.rollback()
                logger.warning("DB insert failed for %s: %s", str_fp, exc)
                stats["files_errored"] += 1
                continue

            stats["files_indexed"] += 1
            stats["symbols_extracted"] += len(file_symbols)
            stats["refs_extracted"] += len(file_refs)
            logger.debug(
                "  → %d symbols, %d refs",
                len(file_symbols), len(file_refs),
            )

        if dry_run:
            stats["file_details"] = file_details
            logger.info("Dry run complete: %s", {k: v for k, v in stats.items() if k != "file_details"})
            return stats

        # Cross-file reference resolution
        logger.info("Resolving cross-file references...")
        resolved = resolve_cross_file_refs(conn, project_id)
        conn.commit()
        stats["refs_resolved"] = resolved
        logger.info("Resolved %d cross-file references", resolved)

        # Stale cleanup (also clean hash table)
        stale_deleted = cleanup_stale_symbols(conn, project_id, live_paths)
        # Also remove stale hashes for deleted files
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM claude.code_file_hashes
                WHERE project_id = %s AND file_path NOT IN (
                    SELECT unnest(%s::text[])
                )
                """,
                (project_id, list(live_paths)),
            )
        if stale_deleted:
            conn.commit()
        stats["stale_deleted"] = stale_deleted

        # Embeddings (fail-open: errors are logged and skipped)
        try:
            embedded = generate_embeddings_for_project(conn, project_id)
            stats["symbols_embedded"] = embedded
        except Exception as exc:
            logger.warning("Embedding step failed (continuing without embeddings): %s", exc)

        logger.info("Indexing complete: %s", stats)
        return stats

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index a project codebase into the Code Knowledge Graph (claude.code_symbols).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python code_indexer.py my-project C:/Projects/my-project
  python code_indexer.py my-project C:/Projects/my-project --full
        """,
    )
    parser.add_argument("project_name", help="Registered project name (claude.projects)")
    parser.add_argument("project_path", help="Root directory of the project to index")
    parser.add_argument(
        "--full",
        action="store_true",
        default=False,
        help="Force full re-index (ignore cached file hashes)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        stats = index_project(
            project_name=args.project_name,
            project_path=args.project_path,
            force_full=args.full,
        )
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        sys.exit(2)

    print("\nIndexing Summary")
    print("=" * 40)
    for key, val in stats.items():
        print(f"  {key:<22} {val:>8,}")
    print("=" * 40)


if __name__ == "__main__":
    main()
