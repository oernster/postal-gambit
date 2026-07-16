"""Selection-aware game actions behind the main window's buttons and menu.

Each flow filters the current selection down to the games it can apply to,
confirms once with a modal naming the targets and the count, applies the
per-game application-service call and then walks the export dialogs one
game at a time, because every resigned or drawn game still owes its
opponent an email.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QMessageBox, QWidget

from postalgambit.application.export_service import ExportService
from postalgambit.application.game_service import GameService
from postalgambit.application.move_service import MoveService
from postalgambit.domain.errors import PostalGambitError
from postalgambit.domain.game import GameRecord
from postalgambit.domain.wire import WireAction, WireMessage
from postalgambit.ui.dialogs.export_dialog import ExportDialog

_MAX_NAMED_GAMES = 6

SelectionProvider = Callable[[], tuple[GameRecord, ...]]
RefreshCallback = Callable[[], None]


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def describe_games(records: tuple[GameRecord, ...]) -> str:
    """A short, explicit listing of the games an action will touch."""
    lines = [
        f"{r.meta.white.name} vs {r.meta.black.name} [{r.meta.game_id.short}]"
        for r in records[:_MAX_NAMED_GAMES]
    ]
    overflow = len(records) - _MAX_NAMED_GAMES
    if overflow > 0:
        lines.append(f"and {plural(overflow, 'more game')}")
    return "\n".join(lines)


class GameActions:
    """Bulk-capable resign, draw-acceptance, deletion and re-send flows."""

    def __init__(
        self,
        parent: QWidget,
        games: GameService,
        moves: MoveService,
        exports: ExportService,
        selection: SelectionProvider,
        refresh: RefreshCallback,
    ) -> None:
        self._parent = parent
        self._games = games
        self._moves = moves
        self._exports = exports
        self._selection = selection
        self._refresh = refresh

    # Eligibility -------------------------------------------------------

    def resignable(self) -> tuple[GameRecord, ...]:
        return tuple(
            r
            for r in self._selection()
            if not self._moves.status(r.meta.game_id).is_over
        )

    def draw_acceptable(self) -> tuple[GameRecord, ...]:
        return tuple(
            r
            for r in self._selection()
            if r.meta.draw_offer_open and not self._moves.status(r.meta.game_id).is_over
        )

    # Flows -------------------------------------------------------------

    def resign(self) -> None:
        records = self.resignable()
        if not self._confirm(
            records,
            "Resign",
            lambda n, names: (
                f"Resign {plural(n, 'game')}?\n\n{names}\n\n"
                "Your opponent wins each game. You will then be shown one "
                "email per game to send."
            ),
            empty="No selected game is still in progress.",
        ):
            return
        endings = []
        for record in records:
            updated, message = self._games.resign(record.meta.game_id)
            endings.append((updated, message))
        self._finish_with_exports(endings)

    def accept_draw(self) -> None:
        records = self.draw_acceptable()
        if not self._confirm(
            records,
            "Accept draw",
            lambda n, names: (
                f"Accept the draw offered in {plural(n, 'game')}?\n\n{names}\n\n"
                "Each game ends 1/2-1/2. You will then be shown one email "
                "per game to send."
            ),
            empty="No selected game has an open draw offer.",
        ):
            return
        endings = []
        for record in records:
            updated, message = self._games.accept_draw(record.meta.game_id)
            endings.append((updated, message))
        self._finish_with_exports(endings)

    def delete(self) -> None:
        records = self._selection()
        if not self._confirm(
            records,
            "Delete game",
            lambda n, names: (
                f"Delete {plural(n, 'game')}?\n\n{names}\n\n"
                "Each stored game file and its history are removed."
            ),
            empty="No game is selected.",
        ):
            return
        for record in records:
            self._games.delete(record.meta.game_id)
        self._refresh()

    def resend(self) -> None:
        """Rebuild and show the outbound email for every selected game."""
        records = self._selection()
        if not records:
            return
        skipped = []
        for record in records:
            message = WireMessage(action=WireAction.MOVE, pgn=record.pgn)
            try:
                draft = self._exports.build_email(record, message)
            except PostalGambitError:
                skipped.append(record)
                continue
            ExportDialog(draft, self._parent).exec()
        if skipped:
            QMessageBox.information(
                self._parent,
                "Re-send",
                "Skipped games with no moves yet:\n" + describe_games(tuple(skipped)),
            )

    # Helpers -----------------------------------------------------------

    def _confirm(
        self,
        records: tuple[GameRecord, ...],
        title: str,
        build_text: Callable[[int, str], str],
        empty: str,
    ) -> bool:
        if not records:
            QMessageBox.information(self._parent, title, empty)
            return False
        answer = QMessageBox.question(
            self._parent,
            title,
            build_text(len(records), describe_games(records)),
        )
        return answer == QMessageBox.StandardButton.Yes

    def _finish_with_exports(
        self, endings: list[tuple[GameRecord, WireMessage]]
    ) -> None:
        self._refresh()
        for updated, message in endings:
            ExportDialog(
                self._exports.build_email(updated, message), self._parent
            ).exec()
