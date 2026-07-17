"""Dialog base with a neutral start and the shared keyboard ring.

Nothing is focused or highlighted when a dialog opens; the first Tab (or
Right) enters the ring of real controls. Every dialog inherits the same
arrow model as the main window: Right steps the ring forward and Left
steps it back (Qt's own focus chain supplies the wrap and skips disabled
stops), text widgets keep their arrows for the caret or scrolling and a
closed dropdown opens on Down rather than silently changing its value.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QWidget,
)

_DROP_OPEN_KEYS = (
    Qt.Key.Key_Down,
    Qt.Key.Key_Return,
    Qt.Key.Key_Enter,
    Qt.Key.Key_Space,
)


class _NeutralStart(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(0, 0)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    def focusOutEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        super().focusOutEvent(event)


class _DialogRing(QObject):
    """Arrow aliases for the active dialog's focus ring.

    Installed application-wide but inert unless its own dialog is the
    active modal widget, so stacked dialogs never fight. An open dropdown
    popup owns its keys entirely (Qt walks the items, Enter chooses,
    Escape closes back to the opener).
    """

    def __init__(self, dialog: NeutralDialog) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt override)
        if event.type() != QEvent.Type.KeyPress:
            return False
        if QApplication.activeModalWidget() is not self._dialog:
            return False
        if QApplication.activePopupWidget() is not None:
            return False
        focused = QApplication.focusWidget()
        if focused is None or not self._dialog.isAncestorOf(focused):
            return False
        key = event.key()
        if isinstance(focused, QComboBox):
            # A closed dropdown drops open on Down (or Enter/Space) and
            # never silently changes value; Up is inert while closed.
            if key in _DROP_OPEN_KEYS:
                focused.showPopup()
                return True
            if key == Qt.Key.Key_Up:
                return True
        elif isinstance(focused, (QLineEdit, QPlainTextEdit, QTextEdit)):
            # Caret movement and scrolling own the arrows (QTextBrowser is
            # a QTextEdit; QPlainTextEdit is its own hierarchy); the field
            # is left with Tab, never an arrow.
            return False
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and isinstance(
            focused, (QCheckBox, QRadioButton)
        ):
            # Enter activates the FOCUSED stop, matching Space. Left to
            # Qt, Enter here would fire the dialog's default button and
            # submit the form instead of toggling the focused control.
            focused.click()
            return True
        if key == Qt.Key.Key_Right:
            self._dialog.step_focus(forward=True)
            return True
        if key == Qt.Key.Key_Left:
            self._dialog.step_focus(forward=False)
            return True
        return False


class NeutralDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._neutral_start = _NeutralStart(self)
        self._ring = _DialogRing(self)
        self._started = False

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        if not self._started:
            self._started = True
            self._neutral_start.setFocus()

    def step_focus(self, forward: bool) -> None:
        """Step Qt's focus chain: the arrows' alias for Tab and Shift+Tab.

        The chain wraps at both ends and skips disabled or hidden stops,
        so the ring contract holds without a hand-built stop list.
        """
        if forward:
            self.focusNextChild()
        else:
            self.focusPreviousChild()


def close_row(dialog: QDialog, label: str = "Close") -> QHBoxLayout:
    row = QHBoxLayout()
    row.addStretch()
    button = QPushButton(label)
    button.clicked.connect(dialog.accept)
    row.addWidget(button)
    return row
