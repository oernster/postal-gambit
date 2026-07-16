"""Application ports: the seams infrastructure must implement."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Protocol

from postalgambit.application.dto import BoardView, GameStatus, MoveApplied
from postalgambit.domain.game import Colour, GameId, GameRecord
from postalgambit.domain.identity import Identity


class RulesEngine(Protocol):
    """All chess knowledge flows through this seam."""

    def validate(self, pgn: str) -> None:
        """Raise IllegalPgnError unless the PGN replays legally."""
        ...

    def normalize(self, pgn: str) -> str:
        """Replay and re-export, giving canonical formatting."""
        ...

    def moves(self, pgn: str) -> tuple[str, ...]:
        """The mainline as SAN strings."""
        ...

    def turn(self, pgn: str) -> Colour: ...

    def status(self, pgn: str) -> GameStatus: ...

    def headers(self, pgn: str) -> Mapping[str, str]: ...

    def board_view(self, pgn: str) -> BoardView: ...

    def ascii_board(self, pgn: str) -> str: ...

    def legal_targets(self, pgn: str, source: str) -> tuple[str, ...]:
        """Legal destination squares for the piece on source."""
        ...

    def apply_uci(
        self, pgn: str, source: str, target: str, promotion: str | None = None
    ) -> MoveApplied:
        """Apply a move given as squares; raise IllegalMoveError if illegal."""
        ...

    def apply_san(self, pgn: str, san: str) -> MoveApplied:
        """Apply a SAN move; raise IllegalMoveError if illegal."""
        ...

    def with_result(self, pgn: str, result: str, termination: str) -> str:
        """Set the Result and Termination tags, ending the game."""
        ...


class GameStore(Protocol):
    def save(self, record: GameRecord) -> None: ...

    def load(self, game_id: GameId) -> GameRecord:
        """Raise StorageError when the game does not exist."""
        ...

    def exists(self, game_id: GameId) -> bool: ...

    def list_all(self) -> tuple[GameRecord, ...]: ...

    def delete(self, game_id: GameId) -> None: ...


class SettingsStore(Protocol):
    def load(self) -> Identity: ...

    def save(self, identity: Identity) -> None: ...

    def load_theme(self) -> str:
        """The persisted theme name, or an empty string when unset."""
        ...

    def save_theme(self, theme: str) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime:
        """The current moment as an aware UTC datetime."""
        ...


class IdGenerator(Protocol):
    def new_id(self) -> str:
        """A fresh canonical uuid4 string."""
        ...
