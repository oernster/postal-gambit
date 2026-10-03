"""Labels and message boxes that show text as text, never as markup.

Qt renders a label or message box as rich text whenever its text merely looks
like HTML. Much of what this window shows was written by a correspondent: the
names in an invitation, the address in its From header, an error quoting what
was pasted. Rendered as markup, an `<img>` naming a file makes Qt read that
file; on Windows a UNC path opens a connection to the host it names. So
every label and box in the application is built here with its format fixed to
plain text; `tests/structural/test_plain_text.py` fails on one built anywhere
else.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox, QWidget

_PLAIN = Qt.TextFormat.PlainText


def plain_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setTextFormat(_PLAIN)
    return label


def message_box(
    parent: QWidget | None,
    title: str,
    text: str,
    icon: QMessageBox.Icon = QMessageBox.Icon.NoIcon,
) -> QMessageBox:
    """A box ready for buttons and exec; its text is plain."""
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setTextFormat(_PLAIN)
    box.setText(text)
    return box


def warn(parent: QWidget | None, title: str, text: str) -> None:
    message_box(parent, title, text, QMessageBox.Icon.Warning).exec()


def inform(parent: QWidget | None, title: str, text: str) -> None:
    message_box(parent, title, text, QMessageBox.Icon.Information).exec()


def ask(parent: QWidget | None, title: str, text: str) -> bool:
    """A yes or no question; True when the answer is yes."""
    box = message_box(parent, title, text, QMessageBox.Icon.Question)
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    return box.exec() == QMessageBox.StandardButton.Yes
