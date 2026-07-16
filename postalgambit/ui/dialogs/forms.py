"""Small form dialogs: new game, identity and promotion choice."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from postalgambit.domain.game import Colour
from postalgambit.domain.identity import Identity
from postalgambit.ui.dialogs.neutral_dialog import NeutralDialog

PROMOTION_CHOICES = (
    ("Queen", "q"),
    ("Rook", "r"),
    ("Bishop", "b"),
    ("Knight", "n"),
)


class NewGameDialog(NeutralDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New game")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.opponent_name = QLineEdit()
        self.opponent_email = QLineEdit()
        self.play_white = QRadioButton("I play White (I move first)")
        self.play_black = QRadioButton("I play Black (they move first)")
        self.play_white.setChecked(True)
        form.addRow("Opponent name:", self.opponent_name)
        form.addRow("Opponent email:", self.opponent_email)
        form.addRow(self.play_white)
        form.addRow(self.play_black)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def my_colour(self) -> Colour:
        return Colour.WHITE if self.play_white.isChecked() else Colour.BLACK


class IdentityDialog(NeutralDialog):
    def __init__(self, identity: Identity, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Your details")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(identity.name)
        self.email = QLineEdit(identity.email)
        form.addRow("Your name:", self.name)
        form.addRow("Your email:", self.email)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def identity(self) -> Identity:
        return Identity(name=self.name.text().strip(), email=self.email.text().strip())


class PromotionDialog(NeutralDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Promote pawn")
        layout = QVBoxLayout(self)
        self.piece = QComboBox()
        for label, letter in PROMOTION_CHOICES:
            self.piece.addItem(label, letter)
        layout.addWidget(self.piece)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def letter(self) -> str:
        return self.piece.currentData()
