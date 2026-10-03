"""P-8: one damaged game file must not stop the window being built.

The window lists the games while it is constructed, before it can show
anything, so a raise there is a silent death before a window opens. This
builds the real window over the real JSON stores in a temporary folder,
offscreen, with no update check wired so nothing can reach the network. It
never shows the window.
"""

from __future__ import annotations

from pathlib import Path

import shiboken6

from postalgambit.application.export_service import ExportService
from postalgambit.application.game_service import GameService
from postalgambit.application.import_service import ImportService
from postalgambit.application.move_service import MoveService
from postalgambit.domain.game import Colour
from postalgambit.domain.identity import Identity
from postalgambit.infrastructure.rules_pychess import PythonChessRulesEngine
from postalgambit.infrastructure.settings_json import JsonSettingsStore
from postalgambit.infrastructure.store_json import GAMES_DIR_NAME, JsonGameStore
from postalgambit.ui.main_window import MainWindow
from tests.fakes import SequenceIdGenerator, TickingClock


def test_window_builds_and_lists_the_readable_games(tmp_path: Path) -> None:
    rules = PythonChessRulesEngine()
    clock = TickingClock()
    store = JsonGameStore(tmp_path)
    settings = JsonSettingsStore(tmp_path)
    settings.save(Identity(name="Oliver", email="o@example.org"))
    games = GameService(
        store=store,
        rules=rules,
        settings=settings,
        clock=clock,
        ids=SequenceIdGenerator(),
    )
    games.create_game("Jane", "jane@example.org", Colour.WHITE)
    damaged = tmp_path / GAMES_DIR_NAME / "zz-damaged.json"
    damaged.write_text("{ not json", encoding="utf-8")
    window = MainWindow(
        game_service=games,
        move_service=MoveService(store=store, rules=rules, clock=clock),
        import_service=ImportService(store=store, rules=rules, clock=clock),
        export_service=ExportService(rules=rules),
        settings_store=settings,
    )
    try:
        assert window.game_list.count() == 1
        assert damaged.read_text(encoding="utf-8") == "{ not json"
    finally:
        shiboken6.delete(window)
