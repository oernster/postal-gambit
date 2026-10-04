"""The reading cycle, driven tick by tick, over BOTH copies of the scroller.

Ported from latencylab `tests/test_ui_auto_scroller.py`, with the corrections
Stellody folds in (opening focus is not a reader; a frozen surface takes no
input) and NarrateX's refusal of a QPlainTextEdit. The application and the
setup program each carry a copy, since the installer imports nothing from the
postalgambit package; every test runs against both, so the copies cannot drift.

Real time is never waited on. Each scroller's own timer is stopped first, after
asserting it was running, since a timer that never starts would otherwise pass
everything; then the tick is called by hand.
"""

from __future__ import annotations

import math

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from installer.ui import auto_scroller as installer_scroller
from postalgambit.ui import auto_scroller as app_scroller

# Enough text that the pane must overflow whatever the platform metrics are.
LONG_TEXT = "\n".join(f"line {n}" for n in range(400))
PANE_W = 200
PANE_H = 80
FITS_SIZE = 400
DESCENT_TICKS = 20
FROZEN_TICKS = 50
HAND_POSITION = 50
MODAL_POSITION = 30


@pytest.fixture(params=[app_scroller, installer_scroller], ids=["app", "installer"])
def module(request):
    return request.param


@pytest.fixture()
def app() -> QApplication:
    instance = QApplication.instance()
    assert isinstance(instance, QApplication)
    return instance


@pytest.fixture()
def pane(app: QApplication):
    widget = QTextBrowser()
    widget.setPlainText(LONG_TEXT)
    widget.resize(PANE_W, PANE_H)
    widget.show()
    app.processEvents()
    assert widget.verticalScrollBar().maximum() > 0, "the pane must overflow"
    yield widget
    widget.close()
    widget.deleteLater()


def attach(module, area):
    """Attach, prove the timer was running, then take the clock by hand."""
    scroller = module.AutoScroller(area)
    assert scroller.timer.isActive()
    assert scroller.timer.interval() == module.TICK_MS
    scroller.timer.stop()
    return scroller


def run_ticks(scroller, count: int) -> None:
    for _ in range(count):
        scroller._tick()


def ticks_for(module, milliseconds: int) -> int:
    """Ticks until a hold of this length is spent, rounding up.

    The manual hold is 62.5 ticks, so it ends on the 63rd (measured).
    """
    return math.ceil(milliseconds / module.TICK_MS)


def reading(module, pane):
    """A scroller already past its start hold, descending from the top."""
    scroller = attach(module, pane)
    run_ticks(scroller, ticks_for(module, module.START_HOLD_MS))
    assert scroller._phase is module.Phase.DOWN
    return scroller


def test_the_canon_constants_are_kept(module) -> None:
    assert (module.TICK_MS, module.START_HOLD_MS) == (40, 5000)
    assert (module.DESCENT_PX, module.TICKS_PER_DESCENT) == (1, 2)
    assert (module.BOTTOM_HOLD_MS, module.REWIND_PX) == (5000, 15)
    assert (module.TOP_HOLD_MS, module.MANUAL_RESUME_MS) == (2000, 2500)


def test_a_line_scrolling_surface_is_refused(module, app) -> None:
    """A QPlainTextEdit counts LINES, so the pixel pace would race."""
    with pytest.raises(TypeError):
        module.AutoScroller(QPlainTextEdit())


def test_a_pixel_surface_travels_far_further_than_a_line_surface(app) -> None:
    """The measurement behind the refusal, so the number is not folklore."""
    by_lines = QPlainTextEdit()
    by_lines.setPlainText(LONG_TEXT)
    by_pixels = QTextBrowser()
    by_pixels.setPlainText(LONG_TEXT)
    for widget in (by_lines, by_pixels):
        widget.resize(PANE_W, PANE_H)
        widget.show()
    app.processEvents()
    lines = by_lines.verticalScrollBar().maximum()
    assert by_pixels.verticalScrollBar().maximum() > lines * 5
    for widget in (by_lines, by_pixels):
        widget.close()


def test_a_fresh_surface_holds_still_before_it_reads(module, pane) -> None:
    scroller = attach(module, pane)
    bar = pane.verticalScrollBar()
    run_ticks(scroller, ticks_for(module, module.START_HOLD_MS) - 1)
    assert bar.value() == 0
    assert scroller._phase is module.Phase.PAUSE_TOP
    run_ticks(scroller, 1)
    assert scroller._phase is module.Phase.DOWN
    assert bar.value() == 0


def test_the_descent_is_half_pace_and_the_rewind_is_not(module, pane) -> None:
    scroller = reading(module, pane)
    bar = pane.verticalScrollBar()
    run_ticks(scroller, DESCENT_TICKS)
    assert bar.value() == DESCENT_TICKS // module.TICKS_PER_DESCENT

    # From the bottom, so the step has room rather than clamping at zero.
    scroller._phase = module.Phase.UP
    bar.setValue(bar.maximum())
    before = bar.value()
    run_ticks(scroller, 1)
    assert before - bar.value() == module.REWIND_PX


def test_the_cycle_turns_round_at_both_ends(module, pane) -> None:
    scroller = reading(module, pane)
    bar = pane.verticalScrollBar()
    bar.setValue(bar.maximum())
    run_ticks(scroller, module.TICKS_PER_DESCENT)
    assert scroller._phase is module.Phase.PAUSE_BOTTOM

    run_ticks(scroller, ticks_for(module, module.BOTTOM_HOLD_MS) - 1)
    assert scroller._phase is module.Phase.PAUSE_BOTTOM
    assert bar.value() == bar.maximum(), "the tail is held for reading"
    run_ticks(scroller, 1)
    assert scroller._phase is module.Phase.UP

    run_ticks(scroller, bar.maximum() // module.REWIND_PX + 1)
    assert bar.value() == bar.minimum()
    run_ticks(scroller, 1)
    assert scroller._phase is module.Phase.PAUSE_TOP

    run_ticks(scroller, ticks_for(module, module.TOP_HOLD_MS))
    assert scroller._phase is module.Phase.DOWN


def test_reading_by_hand_suspends_then_resumes_in_place(module, pane) -> None:
    """Taking over never switches the feature off, nor rewinds to the top."""
    scroller = reading(module, pane)
    bar = pane.verticalScrollBar()
    bar.setValue(HAND_POSITION)
    scroller._suspend()
    assert scroller._phase is module.Phase.MANUAL

    run_ticks(scroller, ticks_for(module, module.MANUAL_RESUME_MS) - 1)
    assert bar.value() == HAND_POSITION, "nothing moves while the reader has it"
    run_ticks(scroller, 1)
    assert scroller._phase is module.Phase.DOWN
    run_ticks(scroller, module.TICKS_PER_DESCENT)
    assert bar.value() == HAND_POSITION + module.DESCENT_PX


def test_a_manual_pause_at_the_very_bottom_rewinds(module, pane) -> None:
    scroller = reading(module, pane)
    bar = pane.verticalScrollBar()
    bar.setValue(bar.maximum())
    scroller._suspend()
    run_ticks(scroller, ticks_for(module, module.MANUAL_RESUME_MS))
    assert scroller._phase is module.Phase.UP


def test_wheel_click_and_key_suspend_and_nothing_else_does(module, pane) -> None:
    """The viewport sees the wheel and clicks; the widget sees the keys."""
    scroller = reading(module, pane)
    wheel = QWheelEvent(
        QPointF(0, 0),
        QPointF(0, 0),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    key = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier
    )
    for watched, event in ((pane.viewport(), wheel), (pane, key)):
        scroller._phase = module.Phase.DOWN
        assert scroller.eventFilter(watched, event) is False
        assert scroller._phase is module.Phase.MANUAL

    scroller._phase = module.Phase.DOWN
    scroller.eventFilter(pane, QEvent(QEvent.Type.Show))
    assert scroller._phase is module.Phase.DOWN


def test_the_scrollbar_counts_as_reading_by_hand(module, pane) -> None:
    scroller = reading(module, pane)
    bar = pane.verticalScrollBar()
    for signal in (bar.sliderPressed, bar.sliderReleased):
        scroller._phase = module.Phase.DOWN
        signal.emit()
        assert scroller._phase is module.Phase.MANUAL
    scroller._phase = module.Phase.DOWN
    bar.sliderMoved.emit(HAND_POSITION)
    assert scroller._phase is module.Phase.MANUAL


def test_focus_arriving_inside_counts_as_reading_by_hand(module, pane) -> None:
    """Watched at the application, with an ancestry test, once the surface is open."""
    scroller = reading(module, pane)
    scroller._on_focus_changed(None, pane.viewport())
    assert scroller._phase is module.Phase.MANUAL

    for elsewhere in (None, QWidget()):
        scroller._phase = module.Phase.DOWN
        scroller._on_focus_changed(None, elsewhere)
        assert scroller._phase is module.Phase.DOWN


def test_the_start_hold_survives_the_opening_focus(module, pane) -> None:
    """A dialog focusing its text as it opens is not a reader taking hold."""
    scroller = attach(module, pane)
    scroller._on_focus_changed(None, pane)
    assert scroller._phase is module.Phase.PAUSE_TOP
    run_ticks(scroller, ticks_for(module, module.START_HOLD_MS) - 1)
    scroller._on_focus_changed(None, pane)
    assert scroller._phase is module.Phase.PAUSE_TOP
    run_ticks(scroller, 1)
    assert scroller._phase is module.Phase.DOWN, "the full hold, not the manual one"

    # The flag cleared with the hold, so a reader arriving now is seen.
    scroller._on_focus_changed(None, pane)
    assert scroller._phase is module.Phase.MANUAL


def test_a_surface_that_fits_costs_nothing(module, app) -> None:
    short = QTextBrowser()
    short.setPlainText("one line")
    short.resize(FITS_SIZE, FITS_SIZE)
    short.show()
    app.processEvents()
    scroller = attach(module, short)
    assert short.verticalScrollBar().maximum() == 0
    run_ticks(scroller, ticks_for(module, module.START_HOLD_MS) * 2)
    assert scroller._phase is module.Phase.PAUSE_TOP, "the hold was never consumed"
    assert scroller._wait_ms == module.START_HOLD_MS
    short.close()


def test_a_modal_above_freezes_the_surface_and_its_input(module, pane, app) -> None:
    """Frozen, not suspended; and a frozen surface takes no input at all."""
    scroller = reading(module, pane)
    bar = pane.verticalScrollBar()
    bar.setValue(MODAL_POSITION)
    scroller._phase = module.Phase.PAUSE_BOTTOM
    scroller._wait_ms = module.BOTTOM_HOLD_MS

    modal = QDialog()
    modal.setModal(True)
    modal.show()
    app.processEvents()
    assert QApplication.activeModalWidget() is modal
    assert scroller._is_frozen() is True

    run_ticks(scroller, FROZEN_TICKS)
    scroller._suspend()
    bar.sliderReleased.emit()
    assert bar.value() == MODAL_POSITION
    assert scroller._phase is module.Phase.PAUSE_BOTTOM
    assert scroller._wait_ms == module.BOTTOM_HOLD_MS

    modal.close()
    app.processEvents()
    assert scroller._is_frozen() is False
    modal.deleteLater()


def test_a_modal_that_owns_the_surface_does_not_freeze_it(module, app) -> None:
    """The modal's OWN surfaces are exactly the ones that should still read."""
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    inner = QTextBrowser(dialog)
    inner.setPlainText(LONG_TEXT)
    layout.addWidget(inner)
    layout.addWidget(QPushButton("Close", dialog))
    dialog.setModal(True)
    dialog.show()
    app.processEvents()
    scroller = attach(module, inner)
    assert QApplication.activeModalWidget() is dialog
    assert scroller._is_frozen() is False
    dialog.close()
    dialog.deleteLater()


def test_the_scroller_changes_no_focus_policy(module, app) -> None:
    """Focus is the reading pane's business; the scroller only watches it."""
    pane = QTextBrowser()
    policies = (pane.focusPolicy(), pane.viewport().focusPolicy())
    attach(module, pane)
    assert (pane.focusPolicy(), pane.viewport().focusPolicy()) == policies
