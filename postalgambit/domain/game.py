"""Core game model: identities, players and the persisted game record.

The PGN text inside a GameRecord is the canonical game state. Whose turn it
is, status and outcome are always derived from it by replay, never stored,
so a record cannot drift out of step with its own moves.

One fact about a game cannot live in its PGN: whether my latest move has
been handed to the mail client yet. A move that has not left the machine is
still mine to take back; once it has gone out, the opponent may already be
replying to it, so it is final. That fact rides on the meta as
`unsent_move`.

A draw offered with my move is the same shape of fact. It is a thing said in
the email rather than a thing on the board, so the PGN cannot hold it; the
email is now written when the move is sent rather than when it is played.
It rides on the meta as `my_draw_offer` and survives the send, so a
move sent a second time carries the same offer it did the first time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from postalgambit.domain.errors import DomainError

SHORT_ID_LENGTH = 8
# The one spelling a uuid has as `str(uuid.uuid4())` writes it. A GameID
# arrives in a stranger's email and becomes a file name, so nothing looser
# passes: no path separators, no dots and no case variants that reach the
# same file on a case-insensitive disk.
_UUID_CANONICAL = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


class Colour(Enum):
    WHITE = "white"
    BLACK = "black"

    @property
    def other(self) -> Colour:
        return Colour.BLACK if self is Colour.WHITE else Colour.WHITE

    @staticmethod
    def of_ply(ply_index: int) -> Colour:
        """Who made the ply at this zero-based index. Every game here starts
        from the initial position, so White makes the even plies."""
        return Colour.WHITE if ply_index % 2 == 0 else Colour.BLACK


@dataclass(frozen=True, slots=True)
class GameId:
    value: str

    def __post_init__(self) -> None:
        if not _UUID_CANONICAL.fullmatch(self.value):
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
    unsent_move: bool = False
    my_draw_offer: bool = False

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
        self,
        pgn: str,
        updated_at: datetime,
        draw_offer_open: bool = False,
        unsent_move: bool = False,
        my_draw_offer: bool = False,
    ) -> GameRecord:
        """A record carrying new PGN. Anything awaiting a send is cleared
        unless the caller says otherwise, because every other way the PGN
        changes (an imported reply, a resignation, an accepted draw, a move
        taken back) settles the question of the previous move."""
        meta = replace(
            self.meta,
            updated_at=updated_at,
            draw_offer_open=draw_offer_open,
            unsent_move=unsent_move,
            my_draw_offer=my_draw_offer,
        )
        return GameRecord(meta=meta, pgn=pgn)

    def with_move_sent(self) -> GameRecord:
        """The same position, no longer awaiting a send. The move has left
        the application, so it can no longer be taken back. Any draw offered
        with it stays, since sending the move again must say the same thing."""
        return GameRecord(meta=replace(self.meta, unsent_move=False), pgn=self.pgn)
