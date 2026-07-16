"""Menu-bar construction for the main window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from postalgambit.ui.dialogs.about import AboutDialog
from postalgambit.version import APP_NAME

if TYPE_CHECKING:
    from postalgambit.ui.main_window import MainWindow


def build_menus(window: MainWindow) -> tuple[QMenu, ...]:
    file_menu = window.menuBar().addMenu("&File")
    for label, slot in (
        ("&New game...", window._new_game),
        ("&Import a move...", window._import_move),
        ("&Re-send last email...", window._resend_last),
        ("&Delete game...", window._delete_game),
    ):
        action = QAction(label, window)
        action.triggered.connect(slot)
        file_menu.addAction(action)
    file_menu.addSeparator()
    exit_action = QAction("E&xit", window)
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)

    game_menu = window.menuBar().addMenu("&Game")
    for label, slot in (
        ("&Accept draw...", window._accept_draw),
        ("&Resign...", window._resign),
        ("&Your details...", window._edit_identity),
    ):
        action = QAction(label, window)
        action.triggered.connect(slot)
        game_menu.addAction(action)

    help_menu = window.menuBar().addMenu("&Help")
    licence_action = QAction("&Licence (GPL-3.0)", window)
    licence_action.triggered.connect(window._show_licence)
    about_action = QAction(f"&About {APP_NAME}", window)
    about_action.triggered.connect(lambda: AboutDialog(window).exec())
    help_menu.addAction(licence_action)
    help_menu.addAction(about_action)
    return (file_menu, game_menu, help_menu)
