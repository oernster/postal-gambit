"""An update check whose controller is deleted before its answer comes back.

The controller is a child of the main window, so deleting the window deletes
it. A check still out at that moment runs on to its emit; through a deleted
controller that raises "Signal source has been deleted" on a thread nothing
catches. This is hardening: a probe of the app's real close and quit paths
found the controller still alive after the event loop ended, so the test
deletes the window directly. Nobody is left to tell, so the answer is
dropped; what must not happen is an exception escaping a thread this
application started.
"""

from __future__ import annotations

import threading

import shiboken6
from PySide6.QtWidgets import QWidget

from postalgambit.application.dto import ReleaseInfo
from postalgambit.application.update_service import UpdateService, platform_key_for
from postalgambit.ui.update_check import UpdateCheckController
from tests.fakes import InMemorySettingsStore

CURRENT = "1.0.0"
# Far longer than a check against a stand-in takes, so only a hang reaches it.
WAIT_SECONDS = 5


class HeldSource:
    """A release source that answers only once the test lets it."""

    def __init__(self) -> None:
        self.asked = threading.Event()
        self.answer = threading.Event()
        self.worker: threading.Thread | None = None

    def latest_release(self) -> ReleaseInfo | None:
        """Say it has been asked, then wait to be allowed to answer."""
        self.worker = threading.current_thread()
        self.asked.set()
        self.answer.wait(WAIT_SECONDS)
        return None


def test_an_answer_with_nowhere_to_go_is_dropped_not_raised(monkeypatch) -> None:
    escaped: list[BaseException | None] = []
    monkeypatch.setattr(
        threading, "excepthook", lambda raised: escaped.append(raised.exc_value)
    )
    source = HeldSource()
    window = QWidget()
    controller = UpdateCheckController(
        window,
        UpdateService(source, CURRENT, platform_key_for("win32")),
        InMemorySettingsStore(),
    )
    controller.check_manually()
    assert source.asked.wait(WAIT_SECONDS), "the check never started"
    shiboken6.delete(window)
    assert not shiboken6.isValid(controller), "the window kept its controller"
    source.answer.set()
    source.worker.join(WAIT_SECONDS)
    assert not source.worker.is_alive(), "the check never finished"
    assert escaped == []
