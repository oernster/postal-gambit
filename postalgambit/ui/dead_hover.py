"""The red inert marker: a disabled control under the mouse.

Qt's stylesheet engine never matches :hover on a disabled widget (its
pseudo-class mapping nests hover under enabled), so a :disabled:hover
rule is unmatchable. This watcher tracks the widget under the cursor
application-wide and flips a dynamic property on a disabled interactive
control, which the stylesheet selects with [deadHover="true"] to paint
the danger ring.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QPushButton,
    QRadioButton,
    QWidget,
)

DEAD_HOVER_PROPERTY = "deadHover"

_WATCHED_TYPES = (QPushButton, QCheckBox, QRadioButton, QComboBox)
_REFRESH_EVENTS = (
    QEvent.Type.MouseMove,
    QEvent.Type.HoverMove,
    QEvent.Type.Enter,
    QEvent.Type.Leave,
    QEvent.Type.WindowDeactivate,
)


class DeadHoverWatcher(QObject):
    """Marks the disabled interactive control under the cursor, if any."""

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._current: QWidget | None = None
        app.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt override)
        if event.type() in _REFRESH_EVENTS:
            self._refresh()
        return False

    def _refresh(self) -> None:
        target = self._disabled_control_under_cursor()
        if target is self._current:
            return
        previous, self._current = self._current, target
        if previous is not None:
            self._mark(previous, False)
        if target is not None:
            self._mark(target, True)

    def _disabled_control_under_cursor(self) -> QWidget | None:
        widget = QApplication.widgetAt(QCursor.pos())
        while widget is not None:
            if isinstance(widget, _WATCHED_TYPES):
                return widget if not widget.isEnabled() else None
            widget = widget.parentWidget()
        return None

    def _mark(self, widget: QWidget, on: bool) -> None:
        try:
            widget.setProperty(DEAD_HOVER_PROPERTY, on)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
        except RuntimeError:
            # The widget's C++ side was destroyed (its dialog closed while
            # hovered); there is nothing left to unmark.
            pass
