"""The uninstall confirmation.

Removing the application is destructive, so it is always confirmed and the
confirmation names what goes and what does not. The user's games are kept
unless they ask otherwise, and the dialog says so. British spelling is used in
comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from installer.constants import APP_DISPLAY_NAME
from installer.ui.icons import app_icon
from installer.ui.themes import (
    BUTTON_GAP,
    DANGER_ACTION,
    DIALOG_MARGIN,
    SECONDARY_ACTION,
    STYLESHEET,
)

CONFIRM_LABEL = "Uninstall"
CANCEL_LABEL = "Cancel"
REMOVE_SETTINGS_LABEL = f"Also remove my {APP_DISPLAY_NAME} games and settings"
MESSAGE = (
    f"Remove {APP_DISPLAY_NAME} and its shortcuts from this PC? Your games and "
    "settings are kept unless you tick the box below."
)


class UninstallDialog(QDialog):
    """A small themed confirmation, with an option to remove games too."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Uninstall {APP_DISPLAY_NAME}")
        self.setWindowIcon(app_icon())
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN
        )
        layout.setSpacing(BUTTON_GAP)

        message = QLabel(MESSAGE)
        message.setWordWrap(True)
        layout.addWidget(message)

        self._remove_settings = QCheckBox(REMOVE_SETTINGS_LABEL)
        layout.addWidget(self._remove_settings)

        confirm = QPushButton(CONFIRM_LABEL)
        confirm.setObjectName(DANGER_ACTION)
        confirm.clicked.connect(self.accept)
        cancel = QPushButton(CANCEL_LABEL)
        cancel.setObjectName(SECONDARY_ACTION)
        cancel.clicked.connect(self.reject)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(confirm)
        layout.addLayout(row)

    def remove_settings(self) -> bool:
        """Return whether the user asked to also remove their games."""
        return self._remove_settings.isChecked()
