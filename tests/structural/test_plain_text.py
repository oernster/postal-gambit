"""Every label and message box in the app is built plain-text.

The UI is outside the line gate, so the P-1 route (a correspondent's words
rendered as markup, which loads what the markup names) is closed by a rule
over the source: labels and message boxes are made only in
`ui/plain_text.py`, which fixes their format to plain text. A new
`QLabel(...)` or `QMessageBox.warning(...)` anywhere else fails here.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.structural.scan import iter_modules, parse, relative_name

PLAIN_TEXT_HOME = "postalgambit/ui/plain_text.py"
_CONSTRUCTED = {"QLabel", "QMessageBox"}
_STATIC_BOXES = {"about", "critical", "information", "question", "warning"}


def _offences(path: Path) -> list[str]:
    found = []
    for node in ast.walk(parse(path)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in _CONSTRUCTED:
            found.append(f"{func.id}(...) at line {node.lineno}")
        elif (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "QMessageBox"
            and func.attr in _STATIC_BOXES
        ):
            found.append(f"QMessageBox.{func.attr}(...) at line {node.lineno}")
    return found


class TestPlainTextHome:
    def test_no_label_or_box_is_built_outside_its_home(self) -> None:
        problems = [
            f"{relative_name(path)}: {offence}"
            for path in iter_modules("ui")
            if relative_name(path) != PLAIN_TEXT_HOME
            for offence in _offences(path)
        ]
        assert problems == []

    def test_the_home_exists_and_is_where_they_are_built(self) -> None:
        homes = [p for p in iter_modules("ui") if relative_name(p) == PLAIN_TEXT_HOME]
        assert len(homes) == 1
        assert _offences(homes[0]) != []

    def test_the_scan_sees_a_planted_label(self, tmp_path: Path) -> None:
        plant = tmp_path / "plant.py"
        plant.write_text("QLabel('x')\nQMessageBox.warning(None, 't', 'x')\n")
        assert len(_offences(plant)) == 2
