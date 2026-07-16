"""Making my move on a board of my own games."""

from __future__ import annotations

from dataclasses import dataclass

from postalgambit.application.dto import BoardView, GameStatus, MoveApplied
from postalgambit.application.ports import Clock, GameStore, RulesEngine
from postalgambit.domain.errors import DomainError, NotYourTurnError
from postalgambit.domain.game import GameId, GameRecord
from postalgambit.domain.wire import WireAction, WireMessage


@dataclass(frozen=True, slots=True)
class MoveService:
    store: GameStore
    rules: RulesEngine
    clock: Clock

    def board(self, game_id: GameId) -> BoardView:
        return self.rules.board_view(self.store.load(game_id).pgn)

    def status(self, game_id: GameId) -> GameStatus:
        return self.rules.status(self.store.load(game_id).pgn)

    def is_my_turn(self, record: GameRecord) -> bool:
        if self.rules.status(record.pgn).is_over:
            return False
        return self.rules.turn(record.pgn) is record.meta.my_colour

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
            action=WireAction.MOVE, pgn=applied.new_pgn, offer_draw=offer_draw
        )
        return updated, message, applied
