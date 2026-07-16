"""Shared AST scanning helpers for the structural tests."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "postalgambit"


def iter_modules(subpackage: str = "") -> list[Path]:
    root = PACKAGE_ROOT / subpackage if subpackage else PACKAGE_ROOT
    return sorted(root.rglob("*.py"))


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imports_of(path: Path) -> set[str]:
    """Every imported module name, TYPE_CHECKING blocks exempt."""
    found: set[str] = set()
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.If) and _is_type_checking(node.test):
            continue
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            found.add(node.module)
    return found


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def is_stdlib(module: str) -> bool:
    return module.split(".")[0] in sys.stdlib_module_names


def relative_name(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()
