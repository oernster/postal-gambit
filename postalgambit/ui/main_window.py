"""The main window: game list, board and the correspondence actions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
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
from postalgambit.ui.board_widget import BOARD_SIZE, FILES
from postalgambit.ui.central_layout import build_central
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
from postalgambit.ui.labels import (
    game_started,
    game_title,
    state_text,
    status_text,
)
from postalgambit.ui.menus import build_menus
from postalgambit.ui.theme import DEFAULT_THEME, THEMES, build_qss
from postalgambit.version import APP_NAME

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
        widgets = build_central(self._legal_targets)
        self.new_button = widgets.new_button
        self.import_button = widgets.import_button
        self.delete_button = widgets.delete_button
        self.game_list = widgets.game_list
        self.turn_label = widgets.turn_label
        self.offer_draw_box = widgets.offer_draw_box
        self.resend_button = widgets.resend_button
        self.accept_draw_button = widgets.accept_draw_button
        self.resign_button = widgets.resign_button
        self.board = widgets.board
        self.side_panel = widgets.side_panel
        self.setCentralWidget(widgets.central)
        self.new_button.clicked.connect(self._new_game)
        self.import_button.clicked.connect(lambda: self._import_move())
        self.delete_button.clicked.connect(self._delete_game)
        self.game_list.currentItemChanged.connect(self._on_selection)
        self.game_list.itemSelectionChanged.connect(self._on_selection)
        self.resend_button.clicked.connect(self._resend_last)
        self.accept_draw_button.clicked.connect(self._accept_draw)
        self.resign_button.clicked.connect(self._resign)
        self.board.moveRequested.connect(self._on_move_requested)

    def _build_navigator(self) -> None:
        self._navigator = KeyboardNavigator(
            window=self,
            menubar=self.menuBar(),
            menu_actions=tuple(menu.menuAction() for menu in self._menus),
            widget_stops=(
                self.new_button,
                self.import_button,
                self.delete_button,
                self.game_list,
                self.offer_draw_box,
                self.resend_button,
                self.accept_draw_button,
                self.resign_button,
                self.board,
                self.side_panel.move_list,
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
        self.game_list.blockSignals(True)
        self.game_list.clear()
        for record in records:
            # Two lines per game: players plus id, then state plus date.
            # One line truncated in the list's width; the date is the
            # part that fits worst, so it rides the second line.
            state = state_text(
                self._moves.status(record.meta.game_id),
                self._moves.is_my_turn(record),
            )
            item = QListWidgetItem(
                f"{game_title(record)}\n{state} ({game_started(record)})"
            )
            item.setData(Qt.ItemDataRole.UserRole, record.meta.game_id.value)
            self.game_list.addItem(item)
            if target is not None and record.meta.game_id == target:
                self.game_list.setCurrentItem(item)
        self.game_list.blockSignals(False)
        if self.game_list.currentItem() is None and self.game_list.count():
            self.game_list.setCurrentRow(0)
        else:
            self._show_selected()

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
            # An empty board is not a keyboard stop: it paints no cursor,
            # so landing on it reads as focus vanishing (the ring skips
            # disabled widgets, which this makes it).
            self.board.setEnabled(False)
            self.side_panel.clear_moves()
            self.turn_label.setText("No game selected.")
            self._set_actions_enabled(None)
            return
        self._selected_id = record.meta.game_id
        self.board.setEnabled(True)
        my_turn = self._moves.is_my_turn(record)
        self.board.set_position(
            self._moves.board(record.meta.game_id),
            record.meta.my_colour,
            interactive=my_turn,
        )
        status = self._moves.status(record.meta.game_id)
        self.turn_label.setText(
            status_text(status, my_turn, record.meta.draw_offer_open)
        )
        self.side_panel.show_moves(self._moves.moves(record.meta.game_id))
        self._set_actions_enabled(record)

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
            message = WireMessage(
                action=WireAction.INVITE,
                pgn=record.pgn,
                from_email=record.meta.me.email,
            )
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
