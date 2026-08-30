"""The strip along the foot of the window, holding the donate button.

The button sits first in the row, apart from everything else, because it
belongs to nothing on screen: put where nothing else is reached by accident,
it cannot be pressed while aiming for a game action.

The mark is drawn at the height of one of the application's own pill buttons,
taken from a real button's size hint rather than written as a number, so it
follows the font and the display scaling instead of drifting away from them.
The picture carries no meaning on its own, so the tooltip says where pressing
it goes.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

DONATE_TOOLTIP = "Buy the author a drink (opens your browser)"
_TRAY_MARGIN_PX = 6


def _pill_height() -> int:
    """The height of one of the window's own buttons, measured not assumed.

    A fresh widget carries the fallback font until it is polished, so it is
    polished before it is asked how tall it wants to be.
    """
    probe = QPushButton("Re-send last email")
    probe.ensurePolished()
    return probe.sizeHint().height()


class BottomTray(QWidget):
    """A foot of its own: this window has no header tray to join."""

    def __init__(
        self,
        parent: QWidget | None = None,
        donate_icon: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BottomTray")
        # A QWidget SUBCLASS does not paint the background or the border its
        # stylesheet gives it unless this is set: measured, with the rule in
        # place, as the top edge coming out in the parent's fill rather than
        # the border colour. Without it the foot loses the line that makes it
        # read as a foot, silently and with the stylesheet looking correct.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # A container is never a focus stop, so it is said rather than left
        # to whatever the toolkit would otherwise decide.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.donate_button = QPushButton(self)
        self.donate_button.setToolTip(DONATE_TOOLTIP)
        self.donate_button.setAccessibleName("Donate to support Postal Gambit")
        self.donate_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if donate_icon is not None:
            mark = _pill_height()
            self.donate_button.setIcon(QIcon(str(donate_icon)))
            self.donate_button.setIconSize(QSize(mark, mark))
        else:
            # Never a silent empty button: without the artwork it still says
            # what it does, so a missing asset is visible rather than mute.
            self.donate_button.setText("Donate")
        row = QHBoxLayout(self)
        row.setContentsMargins(
            _TRAY_MARGIN_PX, _TRAY_MARGIN_PX, _TRAY_MARGIN_PX, _TRAY_MARGIN_PX
        )
        row.addWidget(self.donate_button)
        row.addStretch()

    def ring_stops(self) -> tuple[QPushButton, ...]:
        """This tray's controls, left to right as they are drawn."""
        return (self.donate_button,)
