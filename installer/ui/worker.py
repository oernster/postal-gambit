"""Running an installer operation off the UI thread.

Install, repair and uninstall all move tens of megabytes, so running them on the
UI thread froze the window for the whole operation and left the progress bar
unable to paint. Each runs on a worker thread instead and reports back through
signals, which is what replaced the single status line and its
QApplication.processEvents() nudge. British spelling is used in comments. No em
dashes appear anywhere.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot

from installer.ops.errors import InstallerError
from installer.ops.progress import ProgressCallback

# An operation receives a progress reporter and returns whatever the caller
# needs afterwards: the installed executable path, else None.
Operation = Callable[[ProgressCallback], object]

NO_ERROR = ""
UNEXPECTED_ERROR = "The operation failed: {detail}"


class OperationWorker(QObject):
    """Runs one operation and reports its progress, then its outcome."""

    progressed = Signal(int, str)
    finished = Signal(str, object)

    def __init__(self, operation: Operation) -> None:
        super().__init__()
        self._operation = operation

    @Slot()
    def run(self) -> None:
        """Run the operation, reporting failure as a message rather than raising.

        A worker thread that raises would tear down the thread with nothing
        shown, so every failure is turned into the message the window displays.
        """
        try:
            result = self._operation(self._report)
        except InstallerError as error:
            self.finished.emit(str(error), None)
            return
        except Exception as error:  # noqa: BLE001
            # Last resort: an unexpected failure must still reach the user
            # rather than disappearing with the thread.
            self.finished.emit(UNEXPECTED_ERROR.format(detail=error), None)
            return
        self.finished.emit(NO_ERROR, result)

    def _report(self, pct: int, message: str) -> None:
        """Forward one progress update to the UI thread."""
        self.progressed.emit(pct, message)


class OperationRunner(QObject):
    """Owns the worker thread for one operation and cleans it up afterwards.

    Every receiver below is a real slot on this object, which lives on the UI
    thread, connected explicitly queued. That is load-bearing rather than
    stylistic. A signal connected to a plain function or lambda has no receiver
    object for Qt to take a thread from, so it is invoked directly on whichever
    thread emitted it. Connected that way, everything here would run on the
    worker thread: the window's progress and status updates would be widget
    calls from the wrong thread; worse, quitting the thread would end with the
    thread waiting on itself, which never returns.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: OperationWorker | None = None
        self._on_progress: Callable[[int, str], None] | None = None
        self._on_finished: Callable[[str, object], None] | None = None

    def start(
        self,
        operation: Operation,
        on_progress: Callable[[int, str], None],
        on_finished: Callable[[str, object], None],
    ) -> None:
        """Run ``operation`` on a worker thread and report back on the UI thread."""
        self._on_progress = on_progress
        self._on_finished = on_finished

        thread = QThread(self)
        worker = OperationWorker(operation)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progressed.connect(
            self._relay_progress, Qt.ConnectionType.QueuedConnection
        )
        worker.finished.connect(
            self._relay_finished, Qt.ConnectionType.QueuedConnection
        )

        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(int, str)
    def _relay_progress(self, pct: int, message: str) -> None:
        """Hand one progress update to the window, on the UI thread."""
        if self._on_progress is not None:
            self._on_progress(pct, message)

    @Slot(str, object)
    def _relay_finished(self, error: str, result: object) -> None:
        """Retire the thread, then report the outcome.

        The thread is joined before the callback runs, so a callback that
        closes the window cannot leave a thread running behind it.
        """
        self._stop()
        callback = self._on_finished
        self._on_progress = None
        self._on_finished = None
        if callback is not None:
            callback(error, result)

    def _stop(self) -> None:
        """Quit and wait for the worker thread, then release both objects.

        Only ever called from the UI thread. The worker's ``run`` has already
        returned by the time this runs, so the wait is the thread's event loop
        unwinding rather than the operation completing.
        """
        thread = self._thread
        if thread is not None:
            thread.quit()
            thread.wait()
        self._thread = None
        self._worker = None
