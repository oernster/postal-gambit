"""Putting the stored games on screen: the list, the board and the panel.

Pure presentation, in the same shape as `menus.py`: functions over the
window rather than a second object owning its widgets. Everything here
answers one question, what the three widgets should show for the games as
they currently stand, so the window itself keeps only the commands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem

from postalgambit.domain.game import GameId, GameRecord
from postalgambit.ui.labels import (
    game_started,
    game_title,
    state_text,
    status_text,
)

NO_SELECTION_TEXT = "No game selected."

if TYPE_CHECKING:
    from postalgambit.ui.main_window import MainWindow


def refresh_games(window: MainWindow, keep: GameId | None = None) -> None:
    target = keep or window._selected_id
    records = window._games.list_games()
    window.game_list.blockSignals(True)
    window.game_list.clear()
    for record in records:
        # Two lines per game: players plus id, then state plus date.
        # One line truncated in the list's width; the date is the
        # part that fits worst, so it rides the second line.
        state = state_text(
            window._moves.status(record.meta.game_id),
            window._moves.is_my_turn(record),
            record.meta.unsent_move,
        )
        item = QListWidgetItem(
            f"{game_title(record)}\n{state} ({game_started(record)})"
        )
        item.setData(Qt.ItemDataRole.UserRole, record.meta.game_id.value)
        window.game_list.addItem(item)
        if target is not None and record.meta.game_id == target:
            window.game_list.setCurrentItem(item)
    window.game_list.blockSignals(False)
    if window.game_list.currentItem() is None and window.game_list.count():
        window.game_list.setCurrentRow(0)
    else:
        show_selected(window)


def selected_record(window: MainWindow) -> GameRecord | None:
    item = window.game_list.currentItem()
    if item is None:
        return None
    return window._games.get(GameId(item.data(Qt.ItemDataRole.UserRole)))


def selected_records(window: MainWindow) -> tuple[GameRecord, ...]:
    return tuple(
        window._games.get(GameId(item.data(Qt.ItemDataRole.UserRole)))
        for item in window.game_list.selectedItems()
    )


def show_selected(window: MainWindow) -> None:
    record = selected_record(window)
    if record is None:
        window._selected_id = None
        window.board.clear_board()
        # An empty board is not a keyboard stop: it paints no cursor,
        # so landing on it reads as focus vanishing (the ring skips
        # disabled widgets, which this makes it).
        window.board.setEnabled(False)
        window.side_panel.clear_moves()
        window.turn_label.setText(NO_SELECTION_TEXT)
        set_actions_enabled(window, None)
        return
    window._selected_id = record.meta.game_id
    window.board.setEnabled(True)
    my_turn = window._moves.is_my_turn(record)
    window.board.set_position(
        window._moves.board(record.meta.game_id),
        record.meta.my_colour,
        interactive=my_turn,
    )
    window.turn_label.setText(
        status_text(
            window._moves.status(record.meta.game_id),
            my_turn,
            record.meta.draw_offer_open,
            record.meta.unsent_move,
            record.meta.my_draw_offer,
        )
    )
    window.side_panel.show_moves(window._moves.moves(record.meta.game_id))
    set_actions_enabled(window, record)


def set_actions_enabled(window: MainWindow, record: GameRecord | None) -> None:
    selected = selected_records(window)
    window.delete_button.setEnabled(bool(selected))
    # Both act on a move that has not gone out, so one answer drives both.
    waiting = bool(window._actions.unsent())
    window.send_button.setEnabled(waiting)
    window.undo_button.setEnabled(waiting)
    window.resign_button.setEnabled(bool(window._actions.resignable()))
    window.accept_draw_button.setEnabled(bool(window._actions.draw_acceptable()))
    window.offer_draw_box.setEnabled(
        record is not None and window._moves.is_my_turn(record)
    )
