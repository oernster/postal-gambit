"""The outbound email: preview, open in the mail client or copy."""

from __future__ import annotations

import os
import sys

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

_DIALOG_MIN_WIDTH = 640
_BODY_MIN_HEIGHT = 380
_COPIED_NOTE = "Copied. Paste into a new email to {to}."
_TOO_LONG_NOTE = "This email is too long for a mailto link; use the clipboard instead."


class ExportDialog(NeutralDialog):
    def __init__(self, draft: EmailDraft, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._draft = draft
        self.setWindowTitle("Send your move")
        self.setMinimumWidth(_DIALOG_MIN_WIDTH)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"To: {draft.to or '(no opponent email on file)'}"))
        subject = QLineEdit(draft.subject)
        subject.setReadOnly(True)
        layout.addWidget(subject)
        body = QPlainTextEdit(draft.body)
        body.setReadOnly(True)
        body.setMinimumHeight(_BODY_MIN_HEIGHT)
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

    def _open_mail_client(self) -> None:
        # On Windows, Qt's openUrl has a special mail branch that resolves the LEGACY
        # default-mail-client registry (Software\Clients\Mail), where a stale Outlook
        # entry can linger, instead of the per-user MAILTO choice from Settings >
        # Default apps. os.startfile drives the same ShellExecute path a clicked link
        # uses, which honours the user's actual choice.
        if sys.platform == "win32":
            os.startfile(self._draft.mailto_uri)
            return
        QDesktopServices.openUrl(QUrl(self._draft.mailto_uri))

    def _copy(self) -> None:
        text = (
            f"To: {self._draft.to}\n"
            f"Subject: {self._draft.subject}\n\n"
            f"{self._draft.body}"
        )
        QGuiApplication.clipboard().setText(text)
        self.note.setText(_COPIED_NOTE.format(to=self._draft.to or "your opponent"))
