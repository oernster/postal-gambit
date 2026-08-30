"""No pane is reachable by Tab; the runtime half of the invariant.

The walk uses the toolkit's OWN focus chain, never the child list, which is
what makes the answer equal to what a real Tab press reaches. It is structure
rather than paint, so it is trustworthy with no display.

The stylesheet half is in `test_focus_rings.py`.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QAbstractScrollArea,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QGraphicsView,
    QLineEdit,
    QMenuBar,
    QPlainTextEdit,
    QTabBar,
    QTextEdit,
)

from postalgambit.application.dto import EmailDraft
from postalgambit.domain.identity import Identity
from postalgambit.ui.theme import DARK, build_qss

_CHAIN_LIMIT = 200
_LONG_ENOUGH_TO_OVERFLOW = 400
_SHORT_ENOUGH_TO_FIT = 1


@pytest.fixture(scope="session")
def app():
    """The suite's single application object, styled for these tests.

    Built in `tests/conftest.py` at import time, because Qt permits one
    application object per process and it cannot be upgraded from a bare
    QCoreApplication to a widget-capable one afterwards.
    """
    instance = QApplication.instance()
    assert isinstance(instance, QApplication), (
        "These tests need widgets. Something claimed the application "
        "singleton as a bare QCoreApplication before tests/conftest.py could "
        "build a QApplication."
    )
    instance.setStyleSheet(build_qss(DARK))
    return instance


def _focus_chain(root) -> list:
    """The widgets a real Tab press would reach, in order.

    Walked by identity rather than by waiting to return to the first stop:
    the neutral-start sink drops itself out of the chain once it loses focus,
    so a walk that waits to come back round never terminates.
    """
    root.focusNextChild()
    seen: set[int] = set()
    order = []
    for _ in range(_CHAIN_LIMIT):
        widget = root.focusWidget()
        if widget is None or id(widget) in seen:
            break
        seen.add(id(widget))
        order.append(widget)
        root.focusNextChild()
    return order


def _is_legitimate_stop(widget) -> bool:
    """True when the user can act on this stop."""
    controls = (
        QAbstractButton,
        QLineEdit,
        QComboBox,
        QAbstractSpinBox,
        QAbstractSlider,
        QTabBar,
        QMenuBar,
    )
    if isinstance(widget, controls):
        return True
    if isinstance(widget, (QTextEdit, QPlainTextEdit)) and not widget.isReadOnly():
        return True
    # An item view's selection drives the board, so it is actionable.
    if isinstance(widget, QAbstractItemView):
        return True
    # The board owns Up/Down as an internal square cursor.
    if isinstance(widget, QGraphicsView):
        return True
    # A read-only scrolling region earns a place only while it overflows.
    if isinstance(widget, QAbstractScrollArea):
        return (
            widget.verticalScrollBar().maximum() > 0
            or widget.horizontalScrollBar().maximum() > 0
        )
    # The 0x0 neutral-start sink takes the first focus so the window opens
    # with nothing highlighted, then drops itself out of the chain.
    return widget.size().isEmpty()


def _offending_stops(root) -> list[str]:
    return [
        f"{type(widget).__name__}#{widget.objectName()}"
        for widget in _focus_chain(root)
        if not _is_legitimate_stop(widget)
    ]


def _draft(line_count: int) -> EmailDraft:
    return EmailDraft(
        to="opponent@example.com",
        subject="[abc123] Postal Gambit",
        body="\n".join(f"line {index}" for index in range(line_count)),
        mailto_uri="mailto:opponent@example.com",
        mailto_ok=True,
    )


def _dialogs():
    from pathlib import Path

    from postalgambit.ui.dialogs.about import AboutDialog, LicenceDialog
    from postalgambit.ui.dialogs.export_dialog import ExportDialog
    from postalgambit.ui.dialogs.forms import (
        IdentityDialog,
        NewGameDialog,
        PromotionDialog,
    )
    from postalgambit.ui.dialogs.import_dialog import ImportDialog

    licence = Path(__file__).resolve().parents[2] / "LICENSE"
    return [
        ("AboutDialog", AboutDialog()),
        ("LicenceDialog", LicenceDialog("Licence (GPL-3.0)", licence)),
        ("ExportDialog", ExportDialog(_draft(_LONG_ENOUGH_TO_OVERFLOW))),
        ("NewGameDialog", NewGameDialog()),
        ("IdentityDialog", IdentityDialog(Identity(name="A", email="a@b.c"))),
        ("PromotionDialog", PromotionDialog()),
        (
            "ImportDialog",
            ImportDialog(
                run_import=lambda *args, **kwargs: None,
                create_new_game=lambda *args, **kwargs: None,
                candidate_games=(),
            ),
        ),
    ]


class TestNoPaneIsReachableByTab:
    def test_every_dialog_offers_only_controls(self, app) -> None:
        offences = {}
        for name, dialog in _dialogs():
            dialog.show()
            app.processEvents()
            found = _offending_stops(dialog)
            if found:
                offences[name] = found
            dialog.close()
            dialog.deleteLater()
        app.processEvents()
        assert offences == {}, (
            "A pane holds controls; it is not one. Set NoFocus on the widget "
            "AND on its viewport, which is a separate focusable child.\n"
            f"{offences}"
        )

    def test_the_main_window_offers_only_controls(self, app, tmp_path) -> None:
        from main import create_window
        from postalgambit.domain.game import Colour

        window = create_window(tmp_path)
        window._settings.save(Identity(name="Oliver", email="o@example.com"))
        window.resize(1150, 640)
        window.show()
        app.processEvents()
        record = window._games.create_game("Nelson", "n@example.com", Colour.WHITE)
        window.refresh_games(keep=record.meta.game_id)
        app.processEvents()
        found = _offending_stops(window)
        window.close()
        window.deleteLater()
        app.processEvents()
        assert found == [], (
            "A pane holds controls; it is not one. Set NoFocus on the widget "
            "AND on its viewport.\n"
            f"{found}"
        )


class TestAReadOnlyRegionIsAStopOnlyWhileItOverflows:
    """The exception is bounded by the thing that justifies it.

    A read-only preview is reachable so it can be scrolled from the keyboard.
    One that fits its box scrolls nowhere, so it is not actionable and would
    cost a dead Tab press. That makes the policy a function of the size right
    now, never a setting chosen once at construction.
    """

    def _preview(self, app, line_count: int):
        from postalgambit.ui.dialogs.export_dialog import ExportDialog

        dialog = ExportDialog(_draft(line_count))
        dialog.resize(640, 480)
        dialog.show()
        app.processEvents()
        return dialog, dialog.findChild(QPlainTextEdit)

    def test_a_preview_that_fits_is_not_a_stop(self, app) -> None:
        dialog, preview = self._preview(app, _SHORT_ENOUGH_TO_FIT)
        policy = preview.focusPolicy()
        viewport = preview.viewport().focusPolicy()
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        assert policy == Qt.FocusPolicy.NoFocus, (
            "A region that scrolls nowhere is not actionable, so it must not "
            "cost the user a Tab press."
        )
        assert viewport == Qt.FocusPolicy.NoFocus, (
            "The viewport is a separate focusable child: setting only the "
            "outer widget leaves it reachable."
        )

    def test_a_preview_that_overflows_is_a_stop(self, app) -> None:
        dialog, preview = self._preview(app, _LONG_ENOUGH_TO_OVERFLOW)
        policy = preview.focusPolicy()
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        assert policy == Qt.FocusPolicy.TabFocus, (
            "A region carrying more than fits is the one case where a pane "
            "earns a place on the ring: otherwise it cannot be read without "
            "a mouse."
        )


class TestTheMoveHistoryAlwaysShowsWhereFocusIs:
    """The list carries no ring, so its current row has to be there.

    Clearing a list drops its current row, so a refresh arriving while the
    user stands on the move history would otherwise leave a focused list
    showing nothing at all.
    """

    def test_a_refresh_keeps_the_current_row_while_focused(self, app) -> None:
        from postalgambit.ui.side_panel import SidePanel

        panel = SidePanel()
        panel.resize(220, 320)
        panel.show()
        panel.activateWindow()
        app.processEvents()
        panel.show_moves(("e4", "e5", "Nf3", "Nc6"))
        panel.move_list.setFocus(Qt.FocusReason.TabFocusReason)
        app.processEvents()
        assert panel.move_list.hasFocus()
        panel.show_moves(("e4", "e5", "Nf3", "Nc6", "Bb5", "a6"))
        app.processEvents()
        current = panel.move_list.currentRow()
        panel.close()
        panel.deleteLater()
        app.processEvents()
        assert current >= 0, (
            "A focused move history with no current row has no focus "
            "indicator at all, because the list carries no ring."
        )
