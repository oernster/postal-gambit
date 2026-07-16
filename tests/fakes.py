"""Hand-written fakes implementing the application ports. No mock libraries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from postalgambit.domain.errors import StorageError
from postalgambit.domain.game import GameId, GameRecord
from postalgambit.domain.identity import Identity

FIXED_NOW = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)


class InMemoryGameStore:
    def __init__(self) -> None:
        self.records: dict[str, GameRecord] = {}

    def save(self, record: GameRecord) -> None:
        self.records[record.meta.game_id.value] = record

    def load(self, game_id: GameId) -> GameRecord:
        try:
            return self.records[game_id.value]
        except KeyError:
            raise StorageError(f"no stored game {game_id.short}") from None

    def exists(self, game_id: GameId) -> bool:
        return game_id.value in self.records

    def list_all(self) -> tuple[GameRecord, ...]:
        return tuple(self.records.values())

    def delete(self, game_id: GameId) -> None:
        if game_id.value not in self.records:
            raise StorageError(f"no stored game {game_id.short}")
        del self.records[game_id.value]


class InMemorySettingsStore:
    def __init__(self, identity: Identity | None = None) -> None:
        self.identity = identity if identity is not None else Identity()

    def load(self) -> Identity:
        return self.identity

    def save(self, identity: Identity) -> None:
        self.identity = identity


class TickingClock:
    """Returns FIXED_NOW, advancing one minute per call."""

    def __init__(self) -> None:
        self.calls = 0

    def now(self) -> datetime:
        stamp = FIXED_NOW + timedelta(minutes=self.calls)
        self.calls += 1
        return stamp


class SequenceIdGenerator:
    """Deterministic canonical uuids: 00000000-0000-4000-8000-000000000001..."""

    def __init__(self) -> None:
        self.issued = 0

    def new_id(self) -> str:
        self.issued += 1
        return f"00000000-0000-4000-8000-{self.issued:012d}"
