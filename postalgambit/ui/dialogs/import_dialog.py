"""The inbound email: paste text, resolve every import outcome."""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from postalgambit.application.dto import ImportKind, ImportOutcome
from postalgambit.domain.errors import PostalGambitError
from postalgambit.domain.game import GameId, GameRecord
from postalgambit.ui.dialogs.neutral_dialog import NeutralDialog, close_row
from postalgambit.ui.labels import game_label, game_labels

_DIALOG_MIN_WIDTH = 640
_BODY_MIN_HEIGHT = 300
_PROMPT = "Paste the text of your opponent's email (or a bare move like Nf6) below."

ImportRunner = Callable[[str, GameId | None], ImportOutcome]
NewGameCreator = Callable[[ImportOutcome, str], GameRecord]


class ImportDialog(NeutralDialog):
    def __init__(
        self,
        run_import: ImportRunner,
        create_new_game: NewGameCreator,
        candidate_games: tuple[GameRecord, ...],
        parent: QWidget | None = None,
        initial_text: str = "",
    ) -> None:
        super().__init__(parent)
        self._run_import = run_import
        self._create_new_game = create_new_game
        self.setWindowTitle("Import a move")
        self.setMinimumWidth(_DIALOG_MIN_WIDTH)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(_PROMPT))
        self.text = QPlainTextEdit()
        # Tab leaves the paste box for the next stop (a pasted email never
        # needs a literal tab typed); the arrows stay with the caret.
        self.text.setTabChangesFocus(True)
        self.text.setMinimumHeight(_BODY_MIN_HEIGHT)
        if initial_text:
            self.text.setPlainText(initial_text)
        layout.addWidget(self.text)
        chooser_row = QHBoxLayout()
        chooser_row.addWidget(QLabel("Game (for bare moves):"))
        self.game_choice = QComboBox()
        self.game_choice.addItem("Detect from the pasted text", None)
        labels = game_labels(candidate_games)
        for record in candidate_games:
            meta = record.meta
            self.game_choice.addItem(labels[meta.game_id.value], meta.game_id)
        chooser_row.addWidget(self.game_choice, stretch=1)
        layout.addLayout(chooser_row)
        self.result_label = QLabel("")
        layout.addWidget(self.result_label)
        import_button = QPushButton("Import")
        import_button.setObjectName("Primary")
        import_button.clicked.connect(self._attempt_import)
        row = QHBoxLayout()
        row.addWidget(import_button)
        row.addStretch()
        layout.addLayout(row)
        layout.addLayout(close_row(self))

    def _attempt_import(self) -> None:
        text = self.text.toPlainText()
        chosen = self.game_choice.currentData()
        try:
            outcome = self._run_import(text, chosen)
        except PostalGambitError as error:
            QMessageBox.warning(self, "Import failed", str(error))
            return
        if outcome.kind is ImportKind.NEEDS_GAME_CHOICE:
            self.result_label.setText(
                f"{outcome.detail}. Pick the game above and import again."
            )
            return
        if outcome.kind is ImportKind.NEW_GAME:
            self._offer_new_game(outcome)
            return
        self.result_label.setText(outcome.detail)
        self.accept()

    def _offer_new_game(self, outcome: ImportOutcome) -> None:
        # The block's From header carries the sender's address, so a game
        # arriving through the one-click link or a paste is created without
        # asking. The prompt survives only as the fallback for blocks from
        # older versions or hand-typed text, which carry no address.
        sender_email = self._sender_email(outcome)
        question = "This message belongs to a game that is not on file yet. Create it?"
        if sender_email:
            question += f"\n\nReplies will go to {sender_email}."
        confirmed = QMessageBox.question(self, "New game", question)
        if confirmed != QMessageBox.StandardButton.Yes:
            return
        email = sender_email or self._ask_opponent_email()
        if email is None:
            return
        try:
            record = self._create_new_game(outcome, email)
        except PostalGambitError as error:
            QMessageBox.warning(self, "Import failed", str(error))
            return
        self.result_label.setText(f"Created from the message: {game_label(record)}.")
        self.accept()

    @staticmethod
    def _sender_email(outcome: ImportOutcome) -> str:
        """The message's From address, blank unless it looks like one."""
        if outcome.message is None:
            return ""
        candidate = outcome.message.from_email.strip()
        return candidate if "@" in candidate else ""

    def _ask_opponent_email(self) -> str | None:
        email, entered = QInputDialog.getText(
            self, "Opponent email", "Your opponent's email address:"
        )
        if not entered:
            return None
        return email.strip()
