"""The installer's reading pane: a keyboard stop by Tab only, only while it overflows.

A STANDALONE COPY of the application's `postalgambit/ui/scroll_focus.py`, as
latencylab's installer carries its own: the setup program imports nothing from
the postalgambit package. Change both copies together.

A licence text is a pane holding words, not a control. Qt gives a QTextEdit
StrongFocus, so a click anywhere in the licence focused it and the dialog
opened on it. TabFocus means a click never focuses it; and a text that fits its
viewport scrolls nowhere, so it drops off the ring altogether. The policy is
re-decided whenever either scrollbar's range changes and on every resize. The
viewport is a separate focusable child and is never a stop. British spelling is
used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QAbstractScrollArea


class OverflowFocus(QObject):
    """Keeps one scroll area a TabFocus stop exactly while it overflows."""

    def __init__(self, area: QAbstractScrollArea) -> None:
        super().__init__(area)
        self._area = area
        area.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)
        area.installEventFilter(self)
        for bar in (area.verticalScrollBar(), area.horizontalScrollBar()):
            bar.rangeChanged.connect(self.sync)
        self.sync()

    def eventFilter(self, watched, event) -> bool:
        """Resizing changes whether the content still fits, so re-decide."""
        if event.type() == QEvent.Type.Resize:
            self.sync()
        return False

    def overflows(self) -> bool:
        """True when the area actually has somewhere to scroll."""
        return (
            self._area.verticalScrollBar().maximum() > 0
            or self._area.horizontalScrollBar().maximum() > 0
        )

    def sync(self, *_range: int) -> None:
        """A stop while it scrolls somewhere; never a stop when it does not."""
        self._area.setFocusPolicy(
            Qt.FocusPolicy.TabFocus if self.overflows() else Qt.FocusPolicy.NoFocus
        )
