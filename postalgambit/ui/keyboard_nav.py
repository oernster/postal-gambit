"""One explicit focus ring for the whole window.

Tab and Right step forward; Shift+Tab and Left step back; the ring wraps
and skips disabled or hidden stops. Menu titles are the first region:
a menu stop highlights its title without opening it, Down opens it. The
board widget is a two-dimensional canvas, so while it has focus the
horizontal arrows stay with it and only Tab/Shift+Tab step the ring.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenuBar, QWidget

_FORWARD_KEYS = (Qt.Key.Key_Tab, Qt.Key.Key_Right)
_BACK_KEYS = (Qt.Key.Key_Backtab, Qt.Key.Key_Left)


class KeyboardNavigator(QObject):
    def __init__(
        self,
        window: QWidget,
        menubar: QMenuBar,
        menu_actions: tuple[QAction, ...],
        widget_stops: tuple[QWidget, ...],
        board: QWidget | None = None,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._menubar = menubar
        self._menu_actions = menu_actions
        self._widget_stops = widget_stops
        self._board = board
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt override)
        if event.type() != QEvent.Type.KeyPress:
            return False
        if not self._window.isActiveWindow():
            return False
        if QApplication.activeModalWidget() is not None:
            return False
        key = event.key()
        board_focused = self._board is not None and self._board.hasFocus()
        horizontal = key in (Qt.Key.Key_Left, Qt.Key.Key_Right)
        if board_focused and horizontal:
            return False
        if key in _FORWARD_KEYS and not self._shift(event):
            self._step(1)
            return True
        if key in _BACK_KEYS or (key == Qt.Key.Key_Tab and self._shift(event)):
            self._step(-1)
            return True
        return False

    def _shift(self, event) -> bool:
        return bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

    def _stops(self) -> list[tuple[str, object]]:
        stops: list[tuple[str, object]] = [
            ("menu", action) for action in self._menu_actions
        ]
        stops.extend(
            ("widget", widget)
            for widget in self._widget_stops
            if widget.isEnabled() and widget.isVisible()
        )
        return stops

    def _current_index(self, stops: list[tuple[str, object]]) -> int | None:
        active = self._menubar.activeAction()
        focused = QApplication.focusWidget()
        for index, (kind, target) in enumerate(stops):
            if kind == "menu" and target is active:
                return index
            if kind == "widget" and target is focused:
                return index
        return None

    def _step(self, direction: int) -> None:
        stops = self._stops()
        if not stops:
            return
        current = self._current_index(stops)
        index = 0 if current is None else (current + direction) % len(stops)
        self._activate(stops[index])

    def _activate(self, stop: tuple[str, object]) -> None:
        kind, target = stop
        self._close_open_menu()
        if kind == "menu":
            self._menubar.setFocus(Qt.FocusReason.TabFocusReason)
            self._menubar.setActiveAction(target)
            return
        self._menubar.setActiveAction(None)
        target.setFocus(Qt.FocusReason.TabFocusReason)

    def _close_open_menu(self) -> None:
        popup = QApplication.activePopupWidget()
        if popup is not None:
            popup.hide()


class NeutralStartWidget(QWidget):
    """A 0x0 focus sink so the window opens with nothing highlighted."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(0, 0)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    def focusOutEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        super().focusOutEvent(event)
