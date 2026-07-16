"""Game lifecycle: create, list, resign, draws and creation from the wire."""

from __future__ import annotations

from dataclasses import dataclass

from postalgambit.application.dto import (
    RESULT_BLACK_WINS,
    RESULT_DRAW,
    RESULT_WHITE_WINS,
)
from postalgambit.application.ports import (
    Clock,
    GameStore,
    IdGenerator,
    RulesEngine,
    SettingsStore,
)
from postalgambit.domain.errors import DivergenceError, DomainError
from postalgambit.domain.game import Colour, GameId, GameMeta, GameRecord, Player
from postalgambit.domain.pgn_tags import GAME_ID_TAG, new_game_pgn
from postalgambit.domain.wire import WireAction, WireMessage

TERMINATION_RESIGNATION = "resignation"
TERMINATION_AGREED_DRAW = "agreed draw"


@dataclass(frozen=True, slots=True)
class GameService:
    store: GameStore
    rules: RulesEngine
    settings: SettingsStore
    clock: Clock
    ids: IdGenerator

    def create_game(
        self, opponent_name: str, opponent_email: str, my_colour: Colour
    ) -> GameRecord:
        identity = self.settings.load()
        if not identity.is_configured:
            raise DomainError("set your own name in settings before creating a game")
        me = Player(identity.name, identity.email)
        opponent = Player(opponent_name, opponent_email)
        now = self.clock.now()
        meta = GameMeta(
            game_id=GameId(self.ids.new_id()),
            white=me if my_colour is Colour.WHITE else opponent,
            black=opponent if my_colour is Colour.WHITE else me,
            my_colour=my_colour,
            created_at=now,
            updated_at=now,
        )
        record = GameRecord(meta=meta, pgn=new_game_pgn(meta, now.date()))
        self.store.save(record)
        return record

    def create_from_wire(self, message: WireMessage, opponent_email: str) -> GameRecord:
        if message.action not in (WireAction.INVITE, WireAction.MOVE):
            raise DivergenceError(
                f"a {message.action.value} message cannot start a game"
            )
        self.rules.validate(message.pgn)
        pgn = self.rules.normalize(message.pgn)
        headers = self.rules.headers(pgn)
        game_id = GameId(headers.get(GAME_ID_TAG, ""))
        if self.store.exists(game_id):
            raise DivergenceError(f"game {game_id.short} already exists")
        my_colour = self.rules.turn(pgn)
        identity = self.settings.load()
        my_email = identity.email
        white_name = headers.get("White", "White")
        black_name = headers.get("Black", "Black")
        now = self.clock.now()
        meta = GameMeta(
            game_id=game_id,
            white=Player(
                white_name,
                my_email if my_colour is Colour.WHITE else opponent_email,
            ),
            black=Player(
                black_name,
                my_email if my_colour is Colour.BLACK else opponent_email,
            ),
            my_colour=my_colour,
            created_at=now,
            updated_at=now,
            draw_offer_open=message.offer_draw,
        )
        record = GameRecord(meta=meta, pgn=pgn)
        self.store.save(record)
        return record

    def list_games(self) -> tuple[GameRecord, ...]:
        records = self.store.list_all()
        return tuple(sorted(records, key=lambda r: r.meta.updated_at, reverse=True))

    def get(self, game_id: GameId) -> GameRecord:
        return self.store.load(game_id)

    def delete(self, game_id: GameId) -> None:
        self.store.delete(game_id)

    def resign(self, game_id: GameId) -> tuple[GameRecord, WireMessage]:
        record = self.store.load(game_id)
        self._require_in_progress(record)
        result = (
            RESULT_BLACK_WINS
            if record.meta.my_colour is Colour.WHITE
            else RESULT_WHITE_WINS
        )
        pgn = self.rules.with_result(record.pgn, result, TERMINATION_RESIGNATION)
        updated = record.with_pgn(pgn, self.clock.now())
        self.store.save(updated)
        return updated, WireMessage(
            action=WireAction.RESIGN, pgn=pgn, from_email=record.meta.me.email
        )

    def accept_draw(self, game_id: GameId) -> tuple[GameRecord, WireMessage]:
        record = self.store.load(game_id)
        self._require_in_progress(record)
        if not record.meta.draw_offer_open:
            raise DomainError("there is no draw offer to accept")
        pgn = self.rules.with_result(record.pgn, RESULT_DRAW, TERMINATION_AGREED_DRAW)
        updated = record.with_pgn(pgn, self.clock.now())
        self.store.save(updated)
        return updated, WireMessage(
            action=WireAction.DRAW_ACCEPT, pgn=pgn, from_email=record.meta.me.email
        )

    def _require_in_progress(self, record: GameRecord) -> None:
        if self.rules.status(record.pgn).is_over:
            raise DomainError("the game is already over")
