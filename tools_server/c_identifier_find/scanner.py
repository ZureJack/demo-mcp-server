from __future__ import annotations

import os
import threading
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_c as tsc

from .storage import SymbolData, SymbolStorage

C_LANGUAGE = Language(tsc.language())
_PARSER_LOCK = threading.Lock()
_PARSER: Parser | None = None


def _get_parser() -> Parser:
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser(C_LANGUAGE)
    return _PARSER


def _byte_to_line(source: bytes, pos: int) -> int:
    return source[:pos].count(b"\n") + 1


def _find_name_node(node):
    """Walk down declarator chain to find the identifier/type_identifier."""
    if node.type in ("identifier", "type_identifier"):
        return node
    for field in ("declarator", "name"):
        child = node.child_by_field_name(field)
        if child is not None:
            result = _find_name_node(child)
            if result is not None:
                return result
    for child in node.children:
        if child.type in ("identifier", "type_identifier"):
            return child
        result = _find_name_node(child)
        if result is not None:
            return result
    return None


def _is_function_prototype(node) -> bool:
    """Check if a declaration node is a function prototype."""
    if node.type != "declaration":
        return False
    for child in node.children:
        if child.type == "function_declarator":
            return True
    return False


def _extract_symbols_from_node(
    node, source: bytes, symbols: list[SymbolData]
) -> None:
    t = node.type

    # ---- function definition ----
    if t == "function_definition":
        name_node = _find_name_node(node)
        if name_node is not None:
            name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
            definition = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            symbols.append(SymbolData(
                name=name,
                file_path="",
                line=name_node.start_point.row + 1,
                column=name_node.start_point.column + 1,
                kind="definition",
                symbol_type="function",
                definition=definition,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
            ))
        for child in node.children:
            _extract_symbols_from_node(child, source, symbols)
        return

    # ---- declaration (variable, function prototype, struct/union/enum) ----
    if t == "declaration":
        has_specifier = False
        for child in node.children:
            if child.type in ("struct_specifier", "union_specifier", "enum_specifier"):
                has_specifier = True
                _extract_struct_union_enum(child, source, node, symbols)

        if has_specifier:
            return

        if _is_function_prototype(node):
            name_node = _find_name_node(node)
            if name_node is not None:
                name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                definition = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                symbols.append(SymbolData(
                    name=name,
                    file_path="",
                    line=name_node.start_point.row + 1,
                    column=name_node.start_point.column + 1,
                    kind="declaration",
                    symbol_type="function",
                    definition=definition,
                    start_line=node.start_point.row + 1,
                    end_line=node.end_point.row + 1,
                ))
            return

        for child in node.children:
            if child.type in ("identifier", "init_declarator", "pointer_declarator", "array_declarator"):
                _extract_variable(child, source, node, symbols)
        return

    # ---- type_definition ----
    if t == "type_definition":
        name_node = _find_name_node(node)
        if name_node is not None:
            name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
            definition = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            symbols.append(SymbolData(
                name=name,
                file_path="",
                line=name_node.start_point.row + 1,
                column=name_node.start_point.column + 1,
                kind="definition",
                symbol_type="type",
                definition=definition,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
            ))
        return

    # ---- preproc_def / preproc_function_def ----
    if t in ("preproc_def", "preproc_function_def"):
        name_node = node.child_by_field_name("name")
        if name_node is None:
            for child in node.children:
                if child.type == "identifier":
                    name_node = child
                    break
        if name_node is not None:
            name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
            definition = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            symbols.append(SymbolData(
                name=name,
                file_path="",
                line=name_node.start_point.row + 1,
                column=name_node.start_point.column + 1,
                kind="definition",
                symbol_type="macro",
                definition=definition,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
            ))
        return

    # ---- enumerator (enum constants) ----
    if t == "enumerator":
        name_node = node.child_by_field_name("name")
        if name_node is None:
            for child in node.children:
                if child.type == "identifier":
                    name_node = child
                    break
        if name_node is not None:
            name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
            definition = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            symbols.append(SymbolData(
                name=name,
                file_path="",
                line=name_node.start_point.row + 1,
                column=name_node.start_point.column + 1,
                kind="definition",
                symbol_type="enum",
                definition=definition,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
            ))
        return

    # recurse into children
    for child in node.children:
        _extract_symbols_from_node(child, source, symbols)


def _extract_struct_union_enum(node, source: bytes, parent_decl, symbols: list[SymbolData]) -> None:
    """Extract struct/union/enum definition or declaration."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return

    has_body = node.child_by_field_name("body") is not None
    name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
    definition = source[parent_decl.start_byte:parent_decl.end_byte].decode("utf-8", errors="replace")

    symbol_type = node.type.replace("_specifier", "")  # struct / union / enum
    kind = "definition" if has_body else "declaration"

    symbols.append(SymbolData(
        name=name,
        file_path="",
        line=name_node.start_point.row + 1,
        column=name_node.start_point.column + 1,
        kind=kind,
        symbol_type=symbol_type,
        definition=definition,
        start_line=parent_decl.start_point.row + 1,
        end_line=parent_decl.end_point.row + 1,
    ))


def _extract_variable(declarator_node, source: bytes, parent_decl, symbols: list[SymbolData]) -> None:
    """Extract a variable declaration or definition."""
    name_node = _find_name_node(declarator_node)
    if name_node is None:
        return

    name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
    definition = source[parent_decl.start_byte:parent_decl.end_byte].decode("utf-8", errors="replace")

    kind = "definition" if declarator_node.type == "init_declarator" else "declaration"

    symbols.append(SymbolData(
        name=name,
        file_path="",
        line=name_node.start_point.row + 1,
        column=name_node.start_point.column + 1,
        kind=kind,
        symbol_type="variable",
        definition=definition,
        start_line=parent_decl.start_point.row + 1,
        end_line=parent_decl.end_point.row + 1,
    ))


def extract_symbols(source: bytes, file_path: str, project_dir: str) -> list[SymbolData]:
    """Parse a C source file and extract all symbol declarations/definitions."""
    parser = _get_parser()
    with _PARSER_LOCK:
        tree = parser.parse(source)
    root = tree.root_node

    rel_path = _make_rel(file_path, project_dir)
    symbols: list[SymbolData] = []
    _extract_symbols_from_node(root, source, symbols)

    symbols = [sym._replace(file_path=rel_path) for sym in symbols]
    return symbols


def _make_rel(path: str, project_dir: str) -> str:
    try:
        return str(Path(path).relative_to(project_dir))
    except ValueError:
        return path


def _collect_files(project_dir: str, config: dict) -> list[str]:
    """Collect all C source/header files from the project directory."""
    exclude_dirs = set(config.get("exclude_dirs", [".git", "build", ".venv", "__pycache__"]))
    include_dirs = config.get("include_dirs", [])
    extensions = tuple(config.get("include_extensions", [".c", ".h"]))
    follow_symlinks = config.get("follow_symlinks", False)

    files: list[str] = []

    if include_dirs:
        search_roots = [os.path.join(project_dir, d) for d in include_dirs]
    else:
        search_roots = [project_dir]

    for root_dir in search_roots:
        root_dir = os.path.abspath(root_dir)
        for dirpath, dirnames, filenames in os.walk(root_dir, followlinks=follow_symlinks):
            rel = os.path.relpath(dirpath, project_dir)
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs and not d.startswith(".")]
            for f in filenames:
                if f.endswith(extensions):
                    files.append(os.path.join(dirpath, f))

    return sorted(files)


def full_scan(
    project_dir: str,
    config: dict,
    storage: SymbolStorage,
    cancel: threading.Event,
    on_progress: callable,
) -> None:
    files = _collect_files(project_dir, config)
    total = len(files)

    for i, file_path in enumerate(files):
        if cancel.is_set():
            return

        try:
            with open(file_path, "rb") as f:
                source = f.read()
            symbols = extract_symbols(source, file_path, project_dir)
            if symbols:
                storage.add_symbols(symbols)
        except Exception as e:
            print(f"[c_identifier_find] 扫描错误 {file_path}: {e}", flush=True)

        if (i + 1) % 50 == 0 or i == total - 1:
            on_progress(i + 1, total)

    on_progress(total, total)


def reparse_file(file_path: str, project_dir: str, config: dict) -> list[SymbolData]:
    """Re-parse a single file and return its symbols."""
    try:
        with open(file_path, "rb") as f:
            source = f.read()
    except (FileNotFoundError, PermissionError):
        return []
    return extract_symbols(source, file_path, project_dir)
