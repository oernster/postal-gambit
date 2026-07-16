"""Launch plumbing for clicked postalgambit: links.

One Postal Gambit runs per user: a second launch (the OS starting the
registered handler for a clicked link) forwards its link over a local
socket to the running instance and exits, so the move lands in the window
the user already has open. On macOS the OS delivers link opens as
QFileOpenEvent instead of argv, so a QApplication subclass routes those to
the same handler.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

SERVER_NAME = "uk.codecrafter.PostalGambit"
_CONNECT_TIMEOUT_MS = 500
_WRITE_TIMEOUT_MS = 1000


def forward_to_running_instance(payload: str) -> bool:
    """Hand the payload to a running instance; False when none is listening.

    The payload is newline-terminated so the receiver knows when the whole
    transmission has arrived; the server closes the connection once it has
    read the line, and waiting for that close keeps the pipe alive until
    the data has actually been consumed.
    """
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(_CONNECT_TIMEOUT_MS):
        return False
    socket.write(payload.encode("utf-8") + b"\n")
    socket.flush()
    socket.waitForBytesWritten(_WRITE_TIMEOUT_MS)
    if socket.state() != QLocalSocket.LocalSocketState.UnconnectedState:
        socket.waitForDisconnected(_WRITE_TIMEOUT_MS)
    return True


class SingleInstanceServer(QObject):
    """The running instance's end: receives payloads from later launches."""

    payloadReceived = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # A crashed instance leaves a stale socket behind; clear it so the
        # fresh listen succeeds.
        QLocalServer.removeServer(SERVER_NAME)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        self._server.listen(SERVER_NAME)

    def _on_connection(self) -> None:
        # The transmission is one newline-terminated line. Drain as data
        # arrives (some may already be buffered before these connections
        # exist) and finish on the newline, closing the connection to tell
        # the sender its payload was consumed. A sender that vanished early
        # still gets whatever arrived emitted, so a bare reveal works.
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        buffer = bytearray()
        done = {"value": False}

        def finish() -> None:
            if done["value"]:
                return
            done["value"] = True
            self.payloadReceived.emit(buffer.decode("utf-8", errors="replace").strip())
            socket.disconnectFromServer()
            socket.deleteLater()

        def drain() -> None:
            buffer.extend(bytes(socket.readAll()))
            if b"\n" in buffer:
                finish()

        socket.readyRead.connect(drain)
        socket.disconnected.connect(finish)
        drain()


class LinkAwareApplication(QApplication):
    """QApplication that routes macOS QFileOpenEvent URLs to a handler."""

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.link_handler: Callable[[str], None] | None = None

    def event(self, event: QEvent) -> bool:  # noqa: N802 (Qt override)
        if event.type() == QEvent.Type.FileOpen and self.link_handler is not None:
            url = event.url().toString() or event.file()
            if url:
                self.link_handler(url)
                return True
        return super().event(event)
