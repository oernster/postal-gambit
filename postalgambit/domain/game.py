"""Core game model: identities, players and the persisted game record.

The PGN text inside a GameRecord is the canonical game state. Whose turn it
is, status and outcome are always derived from it by replay, never stored,
so a record cannot drift out of step with its own moves.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from postalgambit.domain.errors import DomainError

SHORT_ID_LENGTH = 8
_UUID_CANONICAL_LENGTH = 36


class Colour(Enum):
    WHITE = "white"
    BLACK = "black"

    @property
    def other(self) -> Colour:
        return Colour.BLACK if self is Colour.WHITE else Colour.WHITE


@dataclass(frozen=True, slots=True)
class GameId:
    value: str

    def __post_init__(self) -> None:
        if len(self.value) != _UUID_CANONICAL_LENGTH or self.value.count("-") != 4:
            raise DomainError(f"not a canonical uuid: {self.value!r}")

    @property
    def short(self) -> str:
        return self.value[:SHORT_ID_LENGTH]


@dataclass(frozen=True, slots=True)
class Player:
    name: str
    email: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainError("player name must not be blank")


@dataclass(frozen=True, slots=True)
class GameMeta:
    game_id: GameId
    white: Player
    black: Player
    my_colour: Colour
    created_at: datetime
    updated_at: datetime
    draw_offer_open: bool = False

    @property
    def me(self) -> Player:
        return self.white if self.my_colour is Colour.WHITE else self.black

    @property
    def opponent(self) -> Player:
        return self.black if self.my_colour is Colour.WHITE else self.white


@dataclass(frozen=True, slots=True)
class GameRecord:
    meta: GameMeta
    pgn: str

    def with_pgn(
        self, pgn: str, updated_at: datetime, draw_offer_open: bool = False
    ) -> GameRecord:
        meta = replace(
            self.meta, updated_at=updated_at, draw_offer_open=draw_offer_open
        )
        return GameRecord(meta=meta, pgn=pgn)
