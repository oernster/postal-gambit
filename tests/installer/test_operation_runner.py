"""The setup program's worker plumbing, checked without a window.

This guards a defect that shipped once. Every callback was connected to a plain
lambda, which Qt invokes directly on whichever thread emitted the signal, so all
of them ran on the worker thread: the window's progress and status updates
became widget calls from the wrong thread; worse, retiring the thread ended
with the thread waiting on itself, which never returns. The installer reached the end
of an install, launched the application and then hung with no way to close it.

Nothing here needs a widget or a display, so the check costs a
``QCoreApplication`` and nothing else.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication, QThread, QTimer

from installer.ui.worker import UNEXPECTED_ERROR, OperationRunner

# A regression deadlocks rather than failing, so the loop gets a deadline and
# the assertions below turn a hang into a readable failure.
TIMEOUT_MS = 10_000

HALFWAY_PCT = 50
HALFWAY_MESSAGE = "halfway"
RESULT = "the result"
FAILURE_DETAIL = "no disk"


@pytest.fixture()
def app() -> QCoreApplication:
    """The one application object these tests share."""
    existing = QCoreApplication.instance()
    return existing if existing is not None else QCoreApplication([])


def _run_until_quit(app: QCoreApplication) -> None:
    """Run the event loop until something quits it, else until the deadline."""
    guard = QTimer()
    guard.setSingleShot(True)
    guard.timeout.connect(app.quit)
    guard.start(TIMEOUT_MS)
    try:
        app.exec()
    finally:
        guard.stop()


class TestOperationRunner:
    def test_every_callback_arrives_on_the_thread_that_started_the_work(
        self, app: QCoreApplication
    ) -> None:
        runner = OperationRunner()
        home = QThread.currentThread()
        progress: list[tuple[int, str, QThread]] = []
        outcome: list[tuple[str, object, QThread]] = []

        def operation(report):
            report(HALFWAY_PCT, HALFWAY_MESSAGE)
            return RESULT

        def on_progress(pct: int, message: str) -> None:
            progress.append((pct, message, QThread.currentThread()))

        def on_finished(error: str, result: object) -> None:
            outcome.append((error, result, QThread.currentThread()))
            app.quit()

        runner.start(operation, on_progress, on_finished)
        _run_until_quit(app)

        assert outcome, "the operation never reported back"
        error, result, finished_on = outcome[0]
        assert error == ""
        assert result == RESULT
        assert finished_on is home
        assert progress == [(HALFWAY_PCT, HALFWAY_MESSAGE, home)]

    def test_a_failing_operation_reports_its_message_rather_than_raising(
        self, app: QCoreApplication
    ) -> None:
        runner = OperationRunner()
        outcome: list[tuple[str, object, QThread]] = []

        def operation(_report):
            raise ValueError(FAILURE_DETAIL)

        def on_finished(error: str, result: object) -> None:
            outcome.append((error, result, QThread.currentThread()))
            app.quit()

        runner.start(operation, lambda *_: None, on_finished)
        _run_until_quit(app)

        assert outcome, "the failure never reported back"
        error, result, finished_on = outcome[0]
        assert error == UNEXPECTED_ERROR.format(detail=FAILURE_DETAIL)
        assert result is None
        assert finished_on is QThread.currentThread()

    def test_a_second_operation_runs_after_the_first(
        self, app: QCoreApplication
    ) -> None:
        """The thread has to be retired before the callback, not after it.

        A runner that left its thread running would fail here rather than in
        production, where the symptom was a window that would not close.
        """
        runner = OperationRunner()
        results: list[object] = []

        def make_operation(value: str):
            def operation(_report) -> str:
                return value

            return operation

        def on_finished(_error: str, result: object) -> None:
            results.append(result)
            app.quit()

        for value in ("first", "second"):
            runner.start(make_operation(value), lambda *_: None, on_finished)
            _run_until_quit(app)

        assert results == ["first", "second"]
