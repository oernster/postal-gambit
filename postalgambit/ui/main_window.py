"""The main window: game list, board and the correspondence actions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from postalgambit.application.export_service import ExportService
from postalgambit.application.game_service import GameService
from postalgambit.application.import_service import ImportService
from postalgambit.application.move_service import MoveService
from postalgambit.application.ports import SettingsStore
from postalgambit.domain.applink import decode_import_link
from postalgambit.domain.errors import PostalGambitError
from postalgambit.domain.game import Colour, GameId, GameRecord
from postalgambit.domain.wire import WireAction, WireMessage
from postalgambit.ui.actions import GameActions
from postalgambit.ui.board_widget import BOARD_SIZE, FILES, BoardWidget
from postalgambit.ui.dialogs.about import LicenceDialog
from postalgambit.ui.dialogs.export_dialog import ExportDialog
from postalgambit.ui.dialogs.forms import (
    IdentityDialog,
    NewGameDialog,
    PromotionDialog,
)
from postalgambit.ui.dialogs.import_dialog import ImportDialog
from postalgambit.ui.icons import find_assets_dir, get_app_icon_path
from postalgambit.ui.keyboard_nav import KeyboardNavigator, NeutralStartWidget
from postalgambit.ui.labels import game_labels
from postalgambit.ui.menus import build_menus
from postalgambit.ui.side_panel import SidePanel
from postalgambit.ui.theme import DEFAULT_THEME, THEMES, build_qss
from postalgambit.version import APP_NAME

_LIST_MIN_WIDTH = 260
_LAST_RANKS = ("8", "1")


class MainWindow(QMainWindow):
    def __init__(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
        export_service: ExportService,
        settings_store: SettingsStore,
    ) -> None:
        super().__init__()
        self._games = game_service
        self._moves = move_service
        self._imports = import_service
        self._exports = export_service
        self._settings = settings_store
        self._selected_id: GameId | None = None
        self._started = False
        self.setWindowTitle(APP_NAME)
        icon_path = get_app_icon_path()
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))
        self._neutral_start = NeutralStartWidget(self)
        self._build_widgets()
        self._actions = GameActions(
            parent=self,
            games=self._games,
            moves=self._moves,
            exports=self._exports,
            selection=self._selected_records,
            refresh=self.refresh_games,
        )
        self._menus = build_menus(self)
        self._build_navigator()
        self._apply_theme(self._settings.load_theme(), persist=False)
        self.refresh_games()

    # Construction -------------------------------------------------------

    def _build_widgets(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        left = QVBoxLayout()
        heading = QLabel("Games")
        heading.setObjectName("Heading")
        left.addWidget(heading)
        self.game_list = QListWidget()
        self.game_list.setMinimumWidth(_LIST_MIN_WIDTH)
        # Extended selection: the CURRENT item drives the board while the
        # full selection drives the bulk actions (resign, accept draw,
        # delete, re-send apply to every selected game they fit).
        self.game_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.game_list.currentItemChanged.connect(self._on_selection)
        self.game_list.itemSelectionChanged.connect(self._on_selection)
        left.addWidget(self.game_list, stretch=1)
        self.new_button = QPushButton("New game")
        self.new_button.setObjectName("Primary")
        self.new_button.clicked.connect(self._new_game)
        self.import_button = QPushButton("Import a move")
        self.import_button.clicked.connect(lambda: self._import_move())
        self.delete_button = QPushButton("Delete game")
        self.delete_button.setObjectName("Danger")
        self.delete_button.clicked.connect(self._delete_game)
        for button in (self.new_button, self.import_button, self.delete_button):
            left.addWidget(button)
        layout.addLayout(left)
        right = QVBoxLayout()
        self.board = BoardWidget(self._legal_targets)
        self.board.moveRequested.connect(self._on_move_requested)
        right.addWidget(self.board)
        self.turn_label = QLabel("")
        right.addWidget(self.turn_label)
        actions = QHBoxLayout()
        self.offer_draw_box = QCheckBox("Offer a draw with this move")
        self.resend_button = QPushButton("Re-send last email")
        self.resend_button.clicked.connect(self._resend_last)
        self.accept_draw_button = QPushButton("Accept draw")
        self.accept_draw_button.clicked.connect(self._accept_draw)
        self.resign_button = QPushButton("Resign")
        self.resign_button.setObjectName("Danger")
        self.resign_button.clicked.connect(self._resign)
        actions.addWidget(self.offer_draw_box)
        actions.addWidget(self.resend_button)
        actions.addWidget(self.accept_draw_button)
        actions.addWidget(self.resign_button)
        actions.addStretch()
        right.addLayout(actions)
        layout.addLayout(right)
        self.side_panel = SidePanel()
        layout.addWidget(self.side_panel, stretch=1)
        self.setCentralWidget(central)

    def _build_navigator(self) -> None:
        self._navigator = KeyboardNavigator(
            window=self,
            menubar=self.menuBar(),
            menu_actions=tuple(menu.menuAction() for menu in self._menus),
            widget_stops=(
                self.game_list,
                self.new_button,
                self.import_button,
                self.delete_button,
                self.board,
                self.side_panel.move_list,
                self.offer_draw_box,
                self.resend_button,
                self.accept_draw_button,
                self.resign_button,
            ),
            board=self.board,
        )

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        if not self._started:
            self._started = True
            self._neutral_start.setFocus()

    # State --------------------------------------------------------------

    def refresh_games(self, keep: GameId | None = None) -> None:
        target = keep or self._selected_id
        records = self._games.list_games()
        labels = game_labels(records)
        self.game_list.blockSignals(True)
        self.game_list.clear()
        for record in records:
            label = labels[record.meta.game_id.value]
            # Two lines per game: the label, then its state. One line
            # truncated in the list's width (the state vanished first).
            item = QListWidgetItem(f"{label}\n{self._state_of(record)}")
            item.setData(Qt.ItemDataRole.UserRole, record.meta.game_id.value)
            self.game_list.addItem(item)
            if target is not None and record.meta.game_id == target:
                self.game_list.setCurrentItem(item)
        self.game_list.blockSignals(False)
        if self.game_list.currentItem() is None and self.game_list.count():
            self.game_list.setCurrentRow(0)
        else:
            self._show_selected()

    def _state_of(self, record: GameRecord) -> str:
        status = self._moves.status(record.meta.game_id)
        if status.is_over:
            return status.description
        if self._moves.is_my_turn(record):
            return "your move"
        return "waiting"

    def _selected_record(self) -> GameRecord | None:
        item = self.game_list.currentItem()
        if item is None:
            return None
        return self._games.get(GameId(item.data(Qt.ItemDataRole.UserRole)))

    def _selected_records(self) -> tuple[GameRecord, ...]:
        return tuple(
            self._games.get(GameId(item.data(Qt.ItemDataRole.UserRole)))
            for item in self.game_list.selectedItems()
        )

    def _on_selection(self, *_args) -> None:
        self._show_selected()

    def _show_selected(self) -> None:
        record = self._selected_record()
        if record is None:
            self._selected_id = None
            self.board.clear_board()
            self.side_panel.clear_moves()
            self.turn_label.setText("No game selected.")
            self._set_actions_enabled(None)
            return
        self._selected_id = record.meta.game_id
        my_turn = self._moves.is_my_turn(record)
        self.board.set_position(
            self._moves.board(record.meta.game_id),
            record.meta.my_colour,
            interactive=my_turn,
        )
        self.turn_label.setText(self._status_text(record, my_turn))
        self.side_panel.show_moves(self._moves.moves(record.meta.game_id))
        self._set_actions_enabled(record)

    def _status_text(self, record: GameRecord, my_turn: bool) -> str:
        status = self._moves.status(record.meta.game_id)
        if status.is_over:
            return f"Game over: {status.description}."
        parts = ["Your move." if my_turn else "Waiting for your opponent."]
        if record.meta.draw_offer_open:
            parts.append("A draw offer is open; you may accept it.")
        return " ".join(parts)

    def _set_actions_enabled(self, record: GameRecord | None) -> None:
        selected = self._selected_records()
        self.delete_button.setEnabled(bool(selected))
        self.resend_button.setEnabled(bool(selected))
        self.resign_button.setEnabled(bool(self._actions.resignable()))
        self.accept_draw_button.setEnabled(bool(self._actions.draw_acceptable()))
        self.offer_draw_box.setEnabled(
            record is not None and self._moves.is_my_turn(record)
        )

    # Actions ------------------------------------------------------------

    def _legal_targets(self, source: str) -> tuple[str, ...]:
        if self._selected_id is None:
            return ()
        return self._moves.legal_targets(self._selected_id, source)

    def _on_move_requested(self, source: str, target: str) -> None:
        if self._selected_id is None:
            return
        promotion = None
        if self._is_promotion(source, target):
            dialog = PromotionDialog(self)
            if not dialog.exec():
                return
            promotion = dialog.letter
        try:
            record, message, applied = self._moves.my_move(
                self._selected_id,
                source,
                target,
                promotion=promotion,
                offer_draw=self.offer_draw_box.isChecked(),
            )
        except PostalGambitError as error:
            QMessageBox.warning(self, "Move rejected", str(error))
            return
        self.offer_draw_box.setChecked(False)
        self.refresh_games()
        ExportDialog(self._exports.build_email(record, message, applied), self).exec()

    def _is_promotion(self, source: str, target: str) -> bool:
        if self._selected_id is None or target[1] not in _LAST_RANKS:
            return False
        view = self._moves.board(self._selected_id)
        index = (BOARD_SIZE - int(source[1])) * BOARD_SIZE + FILES.index(source[0])
        return view.squares[index] in ("P", "p")

    def _new_game(self) -> None:
        dialog = NewGameDialog(self)
        if not dialog.exec():
            return
        name = dialog.opponent_name.text().strip()
        email = dialog.opponent_email.text().strip()
        if not name:
            QMessageBox.warning(self, "New game", "An opponent name is needed.")
            return
        try:
            record = self._games.create_game(name, email, dialog.my_colour)
        except PostalGambitError as error:
            QMessageBox.warning(self, "New game", str(error))
            return
        self.refresh_games(keep=record.meta.game_id)
        if record.meta.my_colour is Colour.BLACK:
            message = WireMessage(action=WireAction.INVITE, pgn=record.pgn)
            ExportDialog(self._exports.build_email(record, message), self).exec()

    def _import_move(self, initial_text: str = "") -> None:
        candidates = tuple(
            record
            for record in self._games.list_games()
            if not self._moves.status(record.meta.game_id).is_over
            and not self._moves.is_my_turn(record)
        )
        dialog = ImportDialog(
            run_import=self._imports.import_text,
            create_new_game=lambda outcome, email: self._games.create_from_wire(
                outcome.message, email
            ),
            candidate_games=candidates,
            parent=self,
            initial_text=initial_text,
        )
        dialog.exec()
        self.refresh_games()

    def open_app_link(self, uri: str) -> None:
        """Handle a clicked postalgambit: link: decode it and open the
        import dialog prefilled with the block, so the same validation and
        the same explicit Import click apply as for a paste."""
        try:
            block = decode_import_link(uri)
        except PostalGambitError as error:
            QMessageBox.warning(self, "Import link", str(error))
            return
        self._import_move(initial_text=block)

    def handle_instance_payload(self, payload: str) -> None:
        """A later launch forwarded its command line: reveal the window
        and open any link it carried."""
        self.show()
        self.raise_()
        self.activateWindow()
        if payload:
            self.open_app_link(payload)

    def _resend_last(self) -> None:
        self._actions.resend()

    def _resign(self) -> None:
        self._actions.resign()

    def _accept_draw(self) -> None:
        self._actions.accept_draw()

    def _delete_game(self) -> None:
        self._actions.delete()
        self._selected_id = None
        self.refresh_games()

    def _set_theme(self, name: str) -> None:
        self._apply_theme(name)

    def _apply_theme(self, name: str, persist: bool = True) -> None:
        if name not in THEMES:
            name = DEFAULT_THEME
        tokens = THEMES[name]
        QApplication.instance().setStyleSheet(build_qss(tokens))
        self.board.set_tokens(tokens)
        for theme_name, action in self.theme_actions.items():
            action.setChecked(theme_name == name)
        if persist:
            self._settings.save_theme(name)

    def _edit_identity(self) -> None:
        dialog = IdentityDialog(self._settings.load(), self)
        if dialog.exec():
            self._settings.save(dialog.identity)

    def _show_licence(self) -> None:
        assets = find_assets_dir()
        licence = None
        if assets is not None:
            candidate = assets.parent / "LICENSE"
            licence = candidate if candidate.is_file() else None
        LicenceDialog("Licence (GPL-3.0)", licence, self).exec()
