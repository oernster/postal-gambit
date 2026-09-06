"""The outbound email: preview, open in the mail client or copy."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Callable

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from postalgambit.application.dto import EmailDraft
from postalgambit.ui.dialogs.neutral_dialog import NeutralDialog, close_row
from postalgambit.ui.scroll_focus import OverflowFocus

_DIALOG_MIN_WIDTH = 640
_BODY_MIN_HEIGHT = 380
_COPIED_NOTE = "Copied. Paste into a new email to {to}."
_TOO_LONG_NOTE = "This email is too long for a mailto link; use the clipboard instead."


class ExportDialog(NeutralDialog):
    """The outbound email: the moment the move stops being local.

    Opening the mail client or copying the email hands the move to the
    outside world, which is the last thing this application can observe
    about it. `on_dispatch` is called then, so the window can record that
    the move is no longer take-back-able.
    """

    def __init__(
        self,
        draft: EmailDraft,
        parent: QWidget | None = None,
        on_dispatch: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._draft = draft
        self._on_dispatch = on_dispatch
        self.setWindowTitle("Send your move")
        self.setMinimumWidth(_DIALOG_MIN_WIDTH)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"To: {draft.to or '(no opponent email on file)'}"))
        subject = QLineEdit(draft.subject)
        subject.setReadOnly(True)
        layout.addWidget(subject)
        body = QPlainTextEdit(draft.body)
        body.setReadOnly(True)
        # Tab steps the ring out of the body; the arrows stay with it for
        # scrolling, matching the scrollable-content stop contract.
        body.setTabChangesFocus(True)
        body.setMinimumHeight(_BODY_MIN_HEIGHT)
        # Read-only, so it is a stop only while the email overruns the
        # box; a preview that fits scrolls nowhere and leaves the ring.
        OverflowFocus(body)
        layout.addWidget(body)
        self.note = QLabel("")
        layout.addWidget(self.note)
        buttons = QHBoxLayout()
        open_button = QPushButton("Open in mail client")
        open_button.setObjectName("Primary")
        open_button.clicked.connect(self._open_mail_client)
        copy_button = QPushButton("Copy email to clipboard")
        copy_button.clicked.connect(self._copy)
        buttons.addWidget(open_button)
        buttons.addWidget(copy_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        layout.addLayout(close_row(self))
        if not draft.mailto_ok:
            open_button.setEnabled(False)
            self.note.setText(_TOO_LONG_NOTE)

    def _dispatched(self) -> None:
        if self._on_dispatch is not None:
            self._on_dispatch()

    def _open_mail_client(self) -> None:
        self._dispatched()
        # On Windows, Qt's openUrl has a special mail branch that resolves the LEGACY
        # default-mail-client registry (Software\Clients\Mail), where a stale Outlook
        # entry can linger, instead of the per-user MAILTO choice from Settings >
        # Default apps. os.startfile drives the same ShellExecute path a clicked link
        # uses, which honours the user's actual choice.
        if sys.platform == "win32":
            os.startfile(self._draft.mailto_uri)
            return
        # On Linux, Qt's openUrl re-serialises the URI from its parsed QUrl form on
        # the way to the desktop portal, prettifying the percent-encoding (spaces
        # come out raw, other escapes half-survive); the mail client's compose
        # window is prefilled with the mangled remains. Hand the exact encoded URI
        # to xdg-open instead, so the handler receives it verbatim; openUrl stays
        # as the fallback and as the macOS path, which passes the encoded form
        # faithfully.
        if sys.platform.startswith("linux"):
            try:
                subprocess.Popen(["xdg-open", self._draft.mailto_uri])
                return
            except OSError:
                pass
        QDesktopServices.openUrl(QUrl(self._draft.mailto_uri))

    def _copy(self) -> None:
        self._dispatched()
        text = (
            f"To: {self._draft.to}\n"
            f"Subject: {self._draft.subject}\n\n"
            f"{self._draft.body}"
        )
        QGuiApplication.clipboard().setText(text)
        self.note.setText(_COPIED_NOTE.format(to=self._draft.to or "your opponent"))
