"""Constructs the main window's central widget: the three columns.

Pure arrangement: every widget is created and laid out here and handed
back unwired. The window connects the signals to its own handlers, so
behaviour stays with the window while geometry lives here.
"""

from __future__ import annotations

from typing import NamedTuple

from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from postalgambit.ui.board_widget import BoardWidget, TargetsProvider
from postalgambit.ui.side_panel import SidePanel

_LIST_MIN_WIDTH = 260


class CentralWidgets(NamedTuple):
    central: QWidget
    new_button: QPushButton
    import_button: QPushButton
    delete_button: QPushButton
    game_list: QListWidget
    turn_label: QLabel
    offer_draw_box: QCheckBox
    resend_button: QPushButton
    accept_draw_button: QPushButton
    resign_button: QPushButton
    board: BoardWidget
    side_panel: SidePanel


def build_central(targets_provider: TargetsProvider) -> CentralWidgets:
    central = QWidget()
    layout = QHBoxLayout(central)
    left = QVBoxLayout()
    # The action pills sit above the Games heading so the primary
    # actions read first, top-left, before the list they act on.
    new_button = QPushButton("New game")
    new_button.setObjectName("Primary")
    import_button = QPushButton("Import a move")
    delete_button = QPushButton("Delete game")
    delete_button.setObjectName("Danger")
    for button in (new_button, import_button, delete_button):
        left.addWidget(button)
    heading = QLabel("Games")
    heading.setObjectName("Heading")
    left.addWidget(heading)
    game_list = QListWidget()
    game_list.setMinimumWidth(_LIST_MIN_WIDTH)
    # Extended selection: the CURRENT item drives the board while the
    # full selection drives the bulk actions (resign, accept draw,
    # delete, re-send apply to every selected game they fit).
    game_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    left.addWidget(game_list, stretch=1)
    layout.addLayout(left)
    right = QVBoxLayout()
    # The middle column reads top-down: the status line first (it is
    # the column's headline and explains why actions are enabled),
    # then the in-game actions, then the board. This mirrors the left
    # column, which opens with its pills and the Games heading.
    turn_label = QLabel("")
    turn_label.setObjectName("Heading")
    right.addWidget(turn_label)
    actions = QHBoxLayout()
    offer_draw_box = QCheckBox("Offer a draw with this move")
    resend_button = QPushButton("Re-send last email")
    accept_draw_button = QPushButton("Accept draw")
    resign_button = QPushButton("Resign")
    resign_button.setObjectName("Danger")
    # The checkbox rides in the button row, so its pill height is
    # pinned to the buttons' own: its indicator gives it a different
    # natural height and no fixed padding matches across fonts.
    offer_draw_box.setFixedHeight(resend_button.sizeHint().height())
    actions.addWidget(offer_draw_box)
    actions.addWidget(resend_button)
    actions.addWidget(accept_draw_button)
    actions.addWidget(resign_button)
    actions.addStretch()
    right.addLayout(actions)
    board = BoardWidget(targets_provider)
    right.addWidget(board)
    layout.addLayout(right)
    side_panel = SidePanel()
    layout.addWidget(side_panel, stretch=1)
    return CentralWidgets(
        central=central,
        new_button=new_button,
        import_button=import_button,
        delete_button=delete_button,
        game_list=game_list,
        turn_label=turn_label,
        offer_draw_box=offer_draw_box,
        resend_button=resend_button,
        accept_draw_button=accept_draw_button,
        resign_button=resign_button,
        board=board,
        side_panel=side_panel,
    )
