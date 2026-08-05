"""Making my move on a board of my own games; also judging which games an
action may be offered for at all."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from postalgambit.application.dto import (
    RANK_ORDER,
    BoardView,
    GameStatus,
    MoveApplied,
)
from postalgambit.application.ports import Clock, GameStore, RulesEngine
from postalgambit.domain.errors import DomainError, NotYourTurnError
from postalgambit.domain.game import GameId, GameRecord
from postalgambit.domain.wire import WireAction, WireMessage

# A pawn reaching either end of the board promotes. Both ranks are read off the
# board's own rank order rather than spelled a second time here.
PROMOTION_RANKS = (RANK_ORDER[0], RANK_ORDER[-1])

# Piece codes are upper case for white and lower for black, so one letter
# answers "is this a pawn" for either side.
PAWN = "P"


@dataclass(frozen=True, slots=True)
class MoveService:
    store: GameStore
    rules: RulesEngine
    clock: Clock

    def board(self, game_id: GameId) -> BoardView:
        return self.rules.board_view(self.store.load(game_id).pgn)

    def status(self, game_id: GameId) -> GameStatus:
        return self.rules.status(self.store.load(game_id).pgn)

    def moves(self, game_id: GameId) -> tuple[str, ...]:
        """The game's mainline as SAN strings, for the move-history panel."""
        return self.rules.moves(self.store.load(game_id).pgn)

    def is_my_turn(self, record: GameRecord) -> bool:
        if self.rules.status(record.pgn).is_over:
            return False
        return self.rules.turn(record.pgn) is record.meta.my_colour

    def is_promotion(self, game_id: GameId, source: str, target: str) -> bool:
        """Whether moving source to target lands a pawn on its far rank.

        The window has to ask which piece before it can play the move, so it
        needs the answer up front. It is a rule about the position rather than
        about the widget that drew it, so it is answered here.
        """
        if target[-1:] not in PROMOTION_RANKS:
            return False
        return self.board(game_id).piece_at(source).upper() == PAWN

    # Eligibility --------------------------------------------------------
    #
    # Which games an action may be offered for is a decision about game state,
    # not about buttons. The window and the action bar ask these rather than
    # filtering records themselves, so there is one answer per question and it
    # sits inside the coverage gate.

    def in_progress(self, records: Iterable[GameRecord]) -> tuple[GameRecord, ...]:
        """The games an action can still change: those that are not yet over."""
        return tuple(
            record for record in records if not self.rules.status(record.pgn).is_over
        )

    def draw_acceptable(self, records: Iterable[GameRecord]) -> tuple[GameRecord, ...]:
        """The games carrying an open draw offer that can still be drawn."""
        return tuple(
            record
            for record in self.in_progress(records)
            if record.meta.draw_offer_open
        )

    def awaiting_opponent(
        self, records: Iterable[GameRecord]
    ) -> tuple[GameRecord, ...]:
        """The games that can receive an imported move: still running and
        waiting on the other player rather than on me."""
        return tuple(
            record
            for record in self.in_progress(records)
            if not self.is_my_turn(record)
        )

    def legal_targets(self, game_id: GameId, source: str) -> tuple[str, ...]:
        record = self.store.load(game_id)
        if not self.is_my_turn(record):
            return ()
        return self.rules.legal_targets(record.pgn, source)

    def my_move(
        self,
        game_id: GameId,
        source: str,
        target: str,
        promotion: str | None = None,
        offer_draw: bool = False,
    ) -> tuple[GameRecord, WireMessage, MoveApplied]:
        record = self.store.load(game_id)
        if self.rules.status(record.pgn).is_over:
            raise DomainError("the game is already over")
        if self.rules.turn(record.pgn) is not record.meta.my_colour:
            raise NotYourTurnError("it is not your move")
        applied = self.rules.apply_uci(record.pgn, source, target, promotion)
        updated = record.with_pgn(applied.new_pgn, self.clock.now())
        self.store.save(updated)
        message = WireMessage(
            action=WireAction.MOVE,
            pgn=applied.new_pgn,
            offer_draw=offer_draw,
            from_email=record.meta.me.email,
        )
        return updated, message, applied
