"""Dialog base with a neutral start: nothing is focused or highlighted when
a dialog opens; the first Tab enters the ring of real controls."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QWidget


class _NeutralStart(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(0, 0)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    def focusOutEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        super().focusOutEvent(event)


class NeutralDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._neutral_start = _NeutralStart(self)
        self._started = False

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        if not self._started:
            self._started = True
            self._neutral_start.setFocus()


def close_row(dialog: QDialog, label: str = "Close") -> QHBoxLayout:
    row = QHBoxLayout()
    row.addStretch()
    button = QPushButton(label)
    button.clicked.connect(dialog.accept)
    row.addWidget(button)
    return row
