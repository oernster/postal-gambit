"""The right-hand panel: the app badge above the move history."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget

from postalgambit.ui.icons import get_badge_png_path

_MOVES_MIN_WIDTH = 190
_BADGE_PX = 160
_PLIES_PER_ROW = 2


class SidePanel(QWidget):
    """App badge on top, the selected game's move history beneath."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        badge_path = get_badge_png_path()
        if badge_path is not None:
            badge = QLabel()
            badge.setPixmap(
                QPixmap(str(badge_path)).scaled(
                    _BADGE_PX,
                    _BADGE_PX,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            badge.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(badge)
        heading = QLabel("Moves")
        heading.setObjectName("Heading")
        layout.addWidget(heading)
        self.move_list = QListWidget()
        self.move_list.setMinimumWidth(_MOVES_MIN_WIDTH)
        layout.addWidget(self.move_list, stretch=1)

    def show_moves(self, sans: tuple[str, ...]) -> None:
        """Render the mainline as numbered move pairs, latest visible."""
        self.move_list.clear()
        for index in range(0, len(sans), _PLIES_PER_ROW):
            number = index // _PLIES_PER_ROW + 1
            white = sans[index]
            black = sans[index + 1] if index + 1 < len(sans) else ""
            self.move_list.addItem(f"{number}. {white}  {black}".rstrip())
        self.move_list.scrollToBottom()

    def clear_moves(self) -> None:
        self.move_list.clear()
