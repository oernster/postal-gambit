"""The installer's licence text reads itself, gently.

A STANDALONE COPY of the application's `postalgambit/ui/auto_scroller.py`, as
latencylab's and Fulcrum's installers carry their own: the setup program
imports nothing from the postalgambit package. The constants and the cycle are
the application's; change both copies together.

The text holds still for a moment when it opens, descends slowly, holds at the
end, rewinds fast and repeats. Reading by hand suspends it, never disables it;
a modal above the surface freezes it in place and a frozen surface takes no
input. Focus arriving during the start hold is the dialog opening, not a
reader, so it is ignored until that hold is spent.

Only pixel-scrolling surfaces may wear it: the licence is a QTextEdit, which
scrolls in pixels; a QPlainTextEdit scrolls in lines and is refused. The
scroller never touches a focus policy: `reading_pane.OverflowFocus` owns that.
"""

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QPlainTextEdit,
    QScrollBar,
    QWidget,
)

TICK_MS = 40
START_HOLD_MS = 5000
DESCENT_PX = 1
TICKS_PER_DESCENT = 2
BOTTOM_HOLD_MS = 5000
REWIND_PX = 15
TOP_HOLD_MS = 2000
MANUAL_RESUME_MS = 2500

_MANUAL_EVENTS = (
    QEvent.Type.Wheel,
    QEvent.Type.MouseButtonPress,
    QEvent.Type.KeyPress,
)


class Phase(Enum):
    DOWN = auto()
    PAUSE_BOTTOM = auto()
    UP = auto()
    PAUSE_TOP = auto()
    MANUAL = auto()


class AutoScroller(QObject):
    """Drives one pixel-scrolling surface through the reading cycle."""

    def __init__(self, area: QAbstractScrollArea) -> None:
        if isinstance(area, QPlainTextEdit):
            raise TypeError("AutoScroller needs a pixel-scrolling surface")
        super().__init__(area)
        self._area = area
        self._phase = Phase.PAUSE_TOP
        self._wait_ms = START_HOLD_MS
        self._ticks_to_step = TICKS_PER_DESCENT
        self._opening = True

        area.viewport().installEventFilter(self)
        area.installEventFilter(self)

        bar = area.verticalScrollBar()
        bar.sliderPressed.connect(self._suspend)
        bar.sliderReleased.connect(self._suspend)
        bar.sliderMoved.connect(self._on_slider_moved)

        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._on_focus_changed)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(TICK_MS)

    def _suspend(self) -> None:
        """Hand the surface to the reader for a while; never while frozen."""
        if self._is_frozen():
            return
        self._phase = Phase.MANUAL
        self._wait_ms = MANUAL_RESUME_MS

    def _on_slider_moved(self, _value: int) -> None:
        self._suspend()

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        if event.type() in _MANUAL_EVENTS:
            self._suspend()
        return super().eventFilter(watched, event)

    def _on_focus_changed(self, _old: QWidget | None, new: QWidget | None) -> None:
        if self._opening:
            return
        if new is not None and (new is self._area or self._area.isAncestorOf(new)):
            self._suspend()

    def _is_frozen(self) -> bool:
        modal = QApplication.activeModalWidget()
        if modal is None:
            return False
        return not (modal is self._area.window() or modal.isAncestorOf(self._area))

    def _tick(self) -> None:
        bar = self._area.verticalScrollBar()
        if bar.maximum() == 0:
            return
        if self._is_frozen():
            return

        if self._wait_ms > 0:
            self._wait_ms -= TICK_MS
            if self._wait_ms > 0:
                return
            self._opening = False
            self._phase = self._phase_after_wait(bar)
            return

        if self._phase == Phase.DOWN:
            self._descend(bar)
        elif self._phase == Phase.UP:
            self._rewind(bar)

    def _phase_after_wait(self, bar: QScrollBar) -> Phase:
        if self._phase == Phase.PAUSE_BOTTOM:
            return Phase.UP
        if self._phase == Phase.MANUAL and bar.value() >= bar.maximum():
            return Phase.UP
        return Phase.DOWN

    def _descend(self, bar: QScrollBar) -> None:
        self._ticks_to_step -= 1
        if self._ticks_to_step > 0:
            return
        self._ticks_to_step = TICKS_PER_DESCENT

        if bar.value() >= bar.maximum():
            self._phase = Phase.PAUSE_BOTTOM
            self._wait_ms = BOTTOM_HOLD_MS
            return
        bar.setValue(bar.value() + DESCENT_PX)

    def _rewind(self, bar: QScrollBar) -> None:
        if bar.value() <= bar.minimum():
            self._phase = Phase.PAUSE_TOP
            self._wait_ms = TOP_HOLD_MS
            return
        bar.setValue(bar.value() - REWIND_PX)
