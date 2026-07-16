"""DTOs crossing the application boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from postalgambit.domain.game import Colour, GameRecord
from postalgambit.domain.wire import WireMessage

BOARD_SQUARES = 64

RESULT_ONGOING = "*"
RESULT_WHITE_WINS = "1-0"
RESULT_BLACK_WINS = "0-1"
RESULT_DRAW = "1/2-1/2"


@dataclass(frozen=True, slots=True)
class GameStatus:
    result: str
    description: str

    @property
    def is_over(self) -> bool:
        return self.result != RESULT_ONGOING


@dataclass(frozen=True, slots=True)
class BoardView:
    """The position as an 8x8 grid.

    squares holds 64 piece codes indexed rank 8 first: index 0 is a8,
    index 7 is h8, index 56 is a1. Codes are PNBRQK for white, pnbrqk for
    black, empty string for an empty square.
    """

    squares: tuple[str, ...]
    turn: Colour
    in_check: bool

    def __post_init__(self) -> None:
        if len(self.squares) != BOARD_SQUARES:
            raise ValueError(f"expected {BOARD_SQUARES} squares")


@dataclass(frozen=True, slots=True)
class MoveApplied:
    new_pgn: str
    san: str
    move_number: int
    mover: Colour
    status: GameStatus


class ImportKind(Enum):
    APPLIED = "applied"
    GAME_OVER = "game-over"
    NEW_GAME = "new-game"
    NEEDS_GAME_CHOICE = "needs-game-choice"


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    kind: ImportKind
    detail: str
    record: GameRecord | None = None
    message: WireMessage | None = None


@dataclass(frozen=True, slots=True)
class EmailDraft:
    to: str
    subject: str
    body: str
    mailto_uri: str
    mailto_ok: bool
