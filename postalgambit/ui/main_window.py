"""The main window: game list, board and the correspondence actions."""

from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

from postalgambit.application.export_service import ExportService
from postalgambit.application.game_service import GameService
from postalgambit.application.import_service import ImportService
from postalgambit.application.move_service import MoveService
from postalgambit.application.ports import SettingsStore
from postalgambit.application.update_service import UpdateService
from postalgambit.domain.applink import decode_import_link
from postalgambit.domain.errors import PostalGambitError
from postalgambit.domain.game import Colour, GameId, GameRecord
from postalgambit.domain.wire import WireAction, WireMessage
from postalgambit.ui import game_view
from postalgambit.ui.actions import GameActions
from postalgambit.ui.central_layout import build_central
from postalgambit.ui.dialogs.about import LicenceDialog
from postalgambit.ui.dialogs.forms import (
    IdentityDialog,
    NewGameDialog,
    PromotionDialog,
)
from postalgambit.ui.dialogs.import_dialog import ImportDialog
from postalgambit.ui.icons import find_assets_dir, get_app_icon_path
from postalgambit.ui.keyboard_nav import KeyboardNavigator, NeutralStartWidget
from postalgambit.ui.links import open_externally
from postalgambit.ui.menus import build_menus
from postalgambit.ui.theme import DEFAULT_THEME, THEMES, build_qss
from postalgambit.ui.update_check import UpdateCheckController
from postalgambit.version import APP_NAME, DONATE_URL


class MainWindow(QMainWindow):
    def __init__(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
        export_service: ExportService,
        settings_store: SettingsStore,
        update_service: UpdateService | None = None,
    ) -> None:
        super().__init__()
        self._games = game_service
        self._moves = move_service
        self._imports = import_service
        self._exports = export_service
        self._settings = settings_store
        self._selected_id: GameId | None = None
        self._started = False
        self.update_controller = None
        if update_service is not None:
            self.update_controller = UpdateCheckController(
                self, update_service, settings_store
            )
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
        self.undo_button = widgets.undo_button
        self.resend_button = widgets.resend_button
        self.accept_draw_button = widgets.accept_draw_button
        self.resign_button = widgets.resign_button
        self.board = widgets.board
        self.side_panel = widgets.side_panel
        self.bottom_tray = widgets.bottom_tray
        self.setCentralWidget(widgets.central)
        self.new_button.clicked.connect(self._new_game)
        self.import_button.clicked.connect(lambda: self._import_move())
        self.delete_button.clicked.connect(self._delete_game)
        self.game_list.currentItemChanged.connect(self._on_selection)
        self.game_list.itemSelectionChanged.connect(self._on_selection)
        self.undo_button.clicked.connect(self._undo_move)
        self.resend_button.clicked.connect(self._resend_last)
        self.accept_draw_button.clicked.connect(self._accept_draw)
        self.resign_button.clicked.connect(self._resign)
        self.board.moveRequested.connect(self._on_move_requested)
        self.bottom_tray.donate_button.clicked.connect(self.open_donation)

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
                self.undo_button,
                self.resend_button,
                self.accept_draw_button,
                self.resign_button,
                self.board,
                self.side_panel.move_list,
                *self.bottom_tray.ring_stops(),
            ),
            board=self.board,
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._started:
            self._started = True
            self._neutral_start.setFocus()

    # State --------------------------------------------------------------

    def refresh_games(self, keep: GameId | None = None) -> None:
        game_view.refresh_games(self, keep)

    def _selected_records(self) -> tuple[GameRecord, ...]:
        return game_view.selected_records(self)

    def _on_selection(self, *_args) -> None:
        game_view.show_selected(self)

    # Actions ------------------------------------------------------------

    def _legal_targets(self, source: str) -> tuple[str, ...]:
        if self._selected_id is None:
            return ()
        return self._moves.legal_targets(self._selected_id, source)

    def _on_move_requested(self, source: str, target: str) -> None:
        if self._selected_id is None:
            return
        promotion = None
        if self._moves.is_promotion(self._selected_id, source, target):
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
        self._actions.show_export(
            record, self._exports.build_email(record, message, applied)
        )

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
            self._actions.show_export(
                record, self._exports.build_email(record, message)
            )

    def _import_move(self, initial_text: str = "") -> None:
        candidates = self._moves.awaiting_opponent(self._games.list_games())
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

    def _undo_move(self) -> None:
        self._actions.undo()

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

    def open_donation(self) -> None:
        """Hand the donation page to whatever the desktop opens links with.

        Nothing is fetched here. The address goes to the desktop and the
        browser does the asking, so the no-network invariant stands.
        """
        if not open_externally(DONATE_URL):
            QMessageBox.warning(
                self,
                "Donate",
                "Could not open a browser for the donation page.",
            )

    def _show_licence(self) -> None:
        assets = find_assets_dir()
        licence = None
        if assets is not None:
            candidate = assets.parent / "LICENSE"
            licence = candidate if candidate.is_file() else None
        LicenceDialog("Licence (GPL-3.0)", licence, self).exec()
