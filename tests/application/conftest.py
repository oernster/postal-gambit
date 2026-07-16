"""Shared wiring for application-service tests: real rules engine, fakes
for every port with I/O."""

from __future__ import annotations

import pytest

from postalgambit.application.game_service import GameService
from postalgambit.application.import_service import ImportService
from postalgambit.application.move_service import MoveService
from postalgambit.domain.game import Colour, GameRecord
from postalgambit.domain.identity import Identity
from postalgambit.infrastructure.rules_pychess import PythonChessRulesEngine
from tests.fakes import (
    InMemoryGameStore,
    InMemorySettingsStore,
    SequenceIdGenerator,
    TickingClock,
)

RULES = PythonChessRulesEngine()


@pytest.fixture()
def store() -> InMemoryGameStore:
    return InMemoryGameStore()


@pytest.fixture()
def settings() -> InMemorySettingsStore:
    return InMemorySettingsStore(Identity(name="Oliver", email="o@example.org"))


@pytest.fixture()
def game_service(
    store: InMemoryGameStore, settings: InMemorySettingsStore
) -> GameService:
    return GameService(
        store=store,
        rules=RULES,
        settings=settings,
        clock=TickingClock(),
        ids=SequenceIdGenerator(),
    )


@pytest.fixture()
def move_service(store: InMemoryGameStore) -> MoveService:
    return MoveService(store=store, rules=RULES, clock=TickingClock())


@pytest.fixture()
def import_service(store: InMemoryGameStore) -> ImportService:
    return ImportService(store=store, rules=RULES, clock=TickingClock())


def new_game(game_service: GameService, my_colour: Colour = Colour.WHITE) -> GameRecord:
    return game_service.create_game("Jane", "jane@example.org", my_colour)
