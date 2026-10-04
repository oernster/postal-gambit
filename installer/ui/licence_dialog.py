"""A themed, scrollable view of a bundled licence text.

Two licences ship with the setup program: the application licence (GPL-3.0) and
the installer wrapper's own as-is notice. One parameterised dialog serves both,
so the two viewer buttons differ only in the text and the title they pass.

Licence texts arrive hard-wrapped, so the view does not wrap them again: it is
sized to the widest line instead, which keeps the original layout readable
rather than reflowing it into ragged pairs of lines. British spelling is used in
comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from installer.ui.auto_scroller import AutoScroller
from installer.ui.icons import app_icon
from installer.ui.reading_pane import OverflowFocus
from installer.ui.themes import (
    BORDER_PX,
    BUTTON_GAP,
    DIALOG_MARGIN,
    LICENCE_DIALOG_HEIGHT,
    LICENCE_VIEW,
    SECONDARY_ACTION,
    SIDES,
    STYLESHEET,
    TEXT_PADDING_PX,
    WIDTH_SAFETY_PX,
)

CLOSE_LABEL = "Close"


def licence_view_width(view: QTextEdit, text: str) -> int:
    """Return the pixel width that shows the widest licence line in full."""
    view.ensurePolished()
    metrics = view.fontMetrics()
    lines = text.splitlines() or [text]
    widest = max(metrics.horizontalAdvance(line) for line in lines)
    doc_margin = round(view.document().documentMargin())
    scrollbar = view.verticalScrollBar().sizeHint().width()
    chrome = SIDES * (doc_margin + TEXT_PADDING_PX + BORDER_PX)
    return widest + scrollbar + chrome + WIDTH_SAFETY_PX


def close_row(dialog: QDialog) -> tuple[QHBoxLayout, QPushButton]:
    """Return the shared trailing row and the single Close button it holds."""
    close = QPushButton(CLOSE_LABEL)
    close.setObjectName(SECONDARY_ACTION)
    close.clicked.connect(dialog.accept)
    row = QHBoxLayout()
    row.addStretch()
    row.addWidget(close)
    return row, close


class LicenceDialog(QDialog):
    """A themed, scrollable view of one licence text."""

    def __init__(
        self,
        licence_text: str,
        title: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(app_icon())
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN
        )
        layout.setSpacing(BUTTON_GAP)

        view = QTextEdit()
        view.setObjectName(LICENCE_VIEW)
        view.setReadOnly(True)
        view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        view.setPlainText(licence_text)
        layout.addWidget(view)
        OverflowFocus(view)
        # The licence reads itself; focus stays the reading pane's business.
        AutoScroller(view)

        width = licence_view_width(view, licence_text)
        view.setMinimumWidth(width)
        self.resize(width + SIDES * DIALOG_MARGIN, LICENCE_DIALOG_HEIGHT)

        row, self._close = close_row(self)
        layout.addLayout(row)
        self._started = False

    def showEvent(self, event) -> None:
        """Open on Close, never on the text.

        A dialog opened to read a licence has one thing to act on, so it opens
        there. The text is a reading pane: a stop only by Tab and only while it
        overflows, never focused on open (ported from latencylab's installer).
        """
        super().showEvent(event)
        if not self._started:
            self._started = True
            self._close.setFocus(Qt.FocusReason.TabFocusReason)
