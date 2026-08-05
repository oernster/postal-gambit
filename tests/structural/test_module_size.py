"""Invariant 8: modules stay at or below the line cap and clear of its band.

The setup program is in scope deliberately. It was one module of over a
thousand lines that no rule could see, which is exactly the state this limit
exists to prevent. The test tree is in scope on the same grounds: a test file
grows the same way a source file does and is refactored under the same rule.
The staged installer payload is build output rather than source, so it is
skipped. The delivery scripts stay exempt because they are linear recipes read
top to bottom.
"""

from __future__ import annotations

from tests.structural.scan import iter_capped_modules, relative_name

MODULE_LINE_CAP = 400

# The 5% rule. A file at 399 passes the cap and then fails on the next edit
# made to it, for a reason that has nothing to do with that edit, so the person
# making the small change pays for someone else's large one. The band is
# derived from the cap rather than written as a second literal, so the two
# numbers cannot drift apart if the cap ever moves.
DANGER_BAND_PERCENT = 5
DANGER_BAND_START = MODULE_LINE_CAP - (MODULE_LINE_CAP * DANGER_BAND_PERCENT) // 100

# Where a file in the band has to land. Not merely under the cap: shaving a
# line or two buys nothing, because the next edit undoes it and the same file
# is refactored over and over. Extract a cohesive concern and take the
# reduction once.
LANDING_LINES = 350


def _line_counts() -> list[tuple[str, int]]:
    return [
        (relative_name(path), len(path.read_text(encoding="utf-8").splitlines()))
        for path in iter_capped_modules()
    ]


def _report(offenders: list[tuple[str, int]]) -> str:
    ordered = sorted(offenders, key=lambda pair: pair[1], reverse=True)
    return "\n".join(f"- {lines:4d}  {name}" for name, lines in ordered)


class TestModuleSize:
    def test_every_module_fits_the_cap(self) -> None:
        oversized = [
            (name, lines) for name, lines in _line_counts() if lines > MODULE_LINE_CAP
        ]
        assert oversized == [], (
            f"Every module must be at most {MODULE_LINE_CAP} lines. Extract a "
            f"cohesive concern and land the result at {LANDING_LINES} or fewer, "
            "not just under the cap.\n" + _report(oversized)
        )

    def test_no_module_sits_in_the_danger_band(self) -> None:
        in_band = [
            (name, lines)
            for name, lines in _line_counts()
            if DANGER_BAND_START < lines < MODULE_LINE_CAP
        ]
        assert in_band == [], (
            f"The {DANGER_BAND_PERCENT}% danger band "
            f"({DANGER_BAND_START + 1} to {MODULE_LINE_CAP - 1} lines) is "
            f"occupied. Take each file to {LANDING_LINES} or fewer by "
            "extracting a cohesive concern; do not shave lines to sit just "
            "under the cap, because the next edit undoes it.\n" + _report(in_band)
        )
