"""Postal Gambit composition root: the only module that wires layers."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from postalgambit.application.export_service import ExportService
from postalgambit.application.game_service import GameService
from postalgambit.application.import_service import ImportService
from postalgambit.application.move_service import MoveService
from postalgambit.infrastructure.clock import SystemClock
from postalgambit.infrastructure.ids import Uuid4Generator
from postalgambit.infrastructure.rules_pychess import PythonChessRulesEngine
from postalgambit.infrastructure.settings_json import JsonSettingsStore
from postalgambit.infrastructure.store_json import JsonGameStore
from postalgambit.ui.dialogs.forms import IdentityDialog
from postalgambit.ui.icons import get_app_icon_path
from postalgambit.ui.main_window import MainWindow
from postalgambit.ui.theme import build_qss
from postalgambit.version import APP_NAME

DATA_DIR_NAME = ".postal-gambit"
WINDOW_START_WIDTH = 1150
WINDOW_START_HEIGHT = 640


def create_window(data_dir: Path) -> MainWindow:
    rules = PythonChessRulesEngine()
    store = JsonGameStore(data_dir)
    settings = JsonSettingsStore(data_dir)
    clock = SystemClock()
    ids = Uuid4Generator()
    return MainWindow(
        game_service=GameService(
            store=store, rules=rules, settings=settings, clock=clock, ids=ids
        ),
        move_service=MoveService(store=store, rules=rules, clock=clock),
        import_service=ImportService(store=store, rules=rules, clock=clock),
        export_service=ExportService(rules=rules),
        settings_store=settings,
    )


def _ensure_identity(settings: JsonSettingsStore, window: MainWindow) -> None:
    identity = settings.load()
    if identity.is_configured:
        return
    dialog = IdentityDialog(identity, window)
    dialog.setWindowTitle(f"Welcome to {APP_NAME}")
    if dialog.exec():
        settings.save(dialog.identity)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(build_qss())
    icon_path = get_app_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))
    data_dir = Path.home() / DATA_DIR_NAME
    window = create_window(data_dir)
    window.resize(WINDOW_START_WIDTH, WINDOW_START_HEIGHT)
    window.show()
    _ensure_identity(JsonSettingsStore(data_dir), window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
