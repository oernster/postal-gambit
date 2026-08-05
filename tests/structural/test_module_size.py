"""Invariant 8: modules stay at or below the line cap.

The setup program is in scope deliberately. It was one module of over a
thousand lines that no rule could see, which is exactly the state this limit
exists to prevent. The staged installer payload is build output rather than
source, so it is skipped, and the delivery scripts stay exempt because they are
linear recipes read top to bottom.
"""

from __future__ import annotations

from pathlib import Path

from tests.structural.scan import REPO_ROOT, iter_modules, relative_name

MODULE_LINE_CAP = 400

# Trees outside the package that the cap also covers.
EXTRA_SCANNED_TREES = ("installer",)
SKIPPED_PARTS = ("__pycache__", "payload")


def _extra_modules() -> list[Path]:
    """Return every module in the extra trees, skipping caches and build output."""
    found: list[Path] = []
    for tree in EXTRA_SCANNED_TREES:
        base = REPO_ROOT / tree
        if not base.is_dir():
            continue
        found.extend(
            path
            for path in sorted(base.rglob("*.py"))
            if not any(part in SKIPPED_PARTS for part in path.parts)
        )
    return found


class TestModuleSize:
    def test_every_module_fits_the_cap(self) -> None:
        oversized = []
        for path in [*iter_modules(), *_extra_modules()]:
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines > MODULE_LINE_CAP:
                oversized.append(f"{relative_name(path)}: {lines} lines")
        assert oversized == []
