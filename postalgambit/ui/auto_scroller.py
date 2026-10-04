"""Content that reads itself, gently.

A long licence or the About page holds still for a moment when it opens, then
descends slowly, holds at the end, rewinds fast and repeats. The reader can
take over at any moment; the cycle suspends and picks up again from wherever
they left it, never from the top and never switched off for good.

Ported from latencylab's `latencylab_ui/auto_scroller.py` (itself from
Fulcrum), with the two later corrections Stellody folds in:

- A dialog that focuses something inside the surface as it opens must not read
  as a reader taking hold; the long opening stillness would silently become the
  short manual one. Focus arrivals are ignored until the start hold is spent;
  the flag clears the moment that hold runs out rather than on the first
  movement, so a reader arriving in between is not missed.
- A surface frozen under a modal ignores INPUT as well as time. A closing
  dialog can return a view to the top; acting on that would leave the surface
  suspended instead of exactly where it was. A frozen surface has no reader by
  definition, so the suspension itself is gated on the freeze.

The constants below are the application's, not each surface's: if one surface
needs a different speed, the speed is wrong everywhere. They are also PIXELS.
A QTextEdit or QTextBrowser scrolls in pixels; a QPlainTextEdit scrolls in
LINES, so one unit there is a whole line and the rewind fifteen lines a tick.
The scroller refuses one outright (NarrateX's rule) so that cannot recur.

The scroller never touches a focus policy: `scroll_focus.OverflowFocus` owns
whether the surface is a stop.
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

# Still on open, so the reader can orient before anything moves.
START_HOLD_MS = 5000

# One pixel every SECOND tick. The pace is halved by counting ticks rather than
# by lengthening the timer, which would coarsen every wait in the cycle with it.
DESCENT_PX = 1
TICKS_PER_DESCENT = 2

# Long enough to finish reading the tail before the rewind takes it away.
BOTTOM_HOLD_MS = 5000

# A reposition, not a reading pass, so it travels fast.
REWIND_PX = 15

TOP_HOLD_MS = 2000

# Stillness required after reading by hand before the cycle picks up again.
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
    """Drives one pixel-scrolling surface through the reading cycle.

    The surface is the scroller's Qt parent, so the scroller lives and dies
    with it and no caller has to hold a reference to keep it alive.
    """

    def __init__(self, area: QAbstractScrollArea) -> None:
        if isinstance(area, QPlainTextEdit):
            raise TypeError("AutoScroller needs a pixel-scrolling surface")
        super().__init__(area)
        self._area = area
        # Seeded as a top hold carrying the start hold, which is what makes a
        # freshly opened surface sit still before its first descent.
        self._phase = Phase.PAUSE_TOP
        self._wait_ms = START_HOLD_MS
        self._ticks_to_step = TICKS_PER_DESCENT
        self._opening = True

        # The viewport sees the wheel and the clicks; the widget sees the keys.
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

    # ------------------------------------------------------------- suspension

    def _suspend(self) -> None:
        """Hand the surface to the reader, for a while.

        Never a disable: taking over by hand must not switch the feature off
        for the rest of the surface's life. Gated on the freeze, so nothing
        reaching a surface beneath a modal can corrupt the state it preserves.
        """
        if self._is_frozen():
            return
        self._phase = Phase.MANUAL
        self._wait_ms = MANUAL_RESUME_MS

    def _on_slider_moved(self, _value: int) -> None:
        """Dragging the scrollbar counts as reading by hand."""
        self._suspend()

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        """Wheel, click and key on the surface are all reading by hand."""
        if event.type() in _MANUAL_EVENTS:
            self._suspend()
        return super().eventFilter(watched, event)

    def _on_focus_changed(self, _old: QWidget | None, new: QWidget | None) -> None:
        """Focus arriving anywhere inside counts as reading by hand.

        A child taking focus never sees the surface's own event filter, so the
        application-wide signal plus an ancestry test is the only way to catch
        it. Ignored through the start hold: opening focus is not a reader.
        """
        if self._opening:
            return
        if new is not None and (new is self._area or self._area.isAncestorOf(new)):
            self._suspend()

    # ------------------------------------------------------------------ ticks

    def _is_frozen(self) -> bool:
        """Whether a modal above this surface owns the screen.

        Two surfaces reading at once compete for the eye, so anything beneath a
        modal is FROZEN rather than suspended: the tick returns before
        consuming any wait, so phase, position and remaining hold are all
        exactly where they were when the modal closes.
        """
        modal = QApplication.activeModalWidget()
        if modal is None:
            return False
        return not (modal is self._area.window() or modal.isAncestorOf(self._area))

    def _tick(self) -> None:
        """One step of the cycle; the timer drives it, as may a test directly."""
        bar = self._area.verticalScrollBar()
        if bar.maximum() == 0:
            # Nothing overflows, so there is nothing to read. Attaching this to
            # a surface that happens to fit is free rather than wrong.
            return
        if self._is_frozen():
            return

        if self._wait_ms > 0:
            self._wait_ms -= TICK_MS
            if self._wait_ms > 0:
                return
            # The opening stillness is over, so focus now means a reader.
            self._opening = False
            self._phase = self._phase_after_wait(bar)
            return

        if self._phase == Phase.DOWN:
            self._descend(bar)
        elif self._phase == Phase.UP:
            self._rewind(bar)

    def _phase_after_wait(self, bar: QScrollBar) -> Phase:
        """Where the cycle goes once a hold runs out.

        After a manual pause with the bar already at the bottom the only way
        on is to rewind; otherwise the reader is carried on downwards from
        exactly where they stopped.
        """
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
