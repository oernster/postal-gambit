"""Shared AST scanning helpers for the structural tests."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "postalgambit"

# The Python that reaches a user's machine beyond the package itself: the two
# composition roots at the top of the tree and the setup program. Anything a
# user installs is subject to the product's claims, so this is the surface the
# no-network invariant is proven over.
SHIPPED_ROOT_MODULES = ("main.py", "installer_main.py")
SHIPPED_TREES = ("installer",)

# The test tree is held to the size cap alongside the code it exercises. It is
# not shipped, so it is scanned separately rather than folded into the above.
TEST_TREE = "tests"

# Not shipped. These scripts build what ships and run only on a developer's
# machine, where reaching the network is legitimate: the Flatpak build
# downloads its wheels and the macOS build talks to Apple to notarise. Holding
# them to the application's no-network invariant would be a claim about the
# wrong thing, so the exemption is named here rather than left to the accident
# of which directory a file happens to sit in.
DELIVERY_SCRIPTS = (
    "buildexe.py",
    "buildinstaller.py",
    "builddmg.py",
    "generate_icons.py",
    "stamp_version.py",
)

# Caches, plus the installer's staged payload, which is build output rather
# than source.
SKIPPED_PARTS = ("__pycache__", "payload")


def iter_modules(subpackage: str = "") -> list[Path]:
    root = PACKAGE_ROOT / subpackage if subpackage else PACKAGE_ROOT
    return sorted(root.rglob("*.py"))


def iter_shipped_modules() -> list[Path]:
    """Every module that reaches a user's machine.

    A declared entry that has gone missing raises rather than being skipped.
    A scanner that quietly covers nothing is a suite that passes for the wrong
    reason, which is the failure this scope exists to remove.
    """
    found = list(iter_modules())
    found.extend(_required_file(REPO_ROOT / name) for name in SHIPPED_ROOT_MODULES)
    for tree in SHIPPED_TREES:
        found.extend(_tree_modules(_required_dir(REPO_ROOT / tree)))
    return sorted(found)


def iter_capped_modules() -> list[Path]:
    """Everything the size cap covers: what ships, plus the test tree."""
    tests = _tree_modules(_required_dir(REPO_ROOT / TEST_TREE))
    return sorted([*iter_shipped_modules(), *tests])


def _tree_modules(base: Path) -> list[Path]:
    return [
        path
        for path in sorted(base.rglob("*.py"))
        if not any(part in SKIPPED_PARTS for part in path.parts)
    ]


def _required_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(_missing(path))
    return path


def _required_dir(path: Path) -> Path:
    if not path.is_dir():
        raise FileNotFoundError(_missing(path))
    return path


def _missing(path: Path) -> str:
    return (
        f"{path.name} is named in tests/structural/scan.py as part of the "
        "scanned surface and is not there. Rename it in scan.py or put it back; "
        "do not let the scan silently shrink."
    )


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
