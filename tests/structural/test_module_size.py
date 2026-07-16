"""Invariant 8: modules stay at or below the line cap."""

from __future__ import annotations

from tests.structural.scan import iter_modules, relative_name

MODULE_LINE_CAP = 400


class TestModuleSize:
    def test_every_module_fits_the_cap(self) -> None:
        oversized = []
        for path in iter_modules():
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines > MODULE_LINE_CAP:
                oversized.append(f"{relative_name(path)}: {lines} lines")
        assert oversized == []
