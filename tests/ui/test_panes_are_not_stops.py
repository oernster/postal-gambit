"""No reading pane is clicked into, stopped on while it fits or opened on.

Ported from latencylab `tests/test_ui_panes_are_not_stops.py`, itself from
NarrateX. The chain walk in `tests/structural/test_focus_chain.py` asks only
whether Tab reaches a pane; three more ways a pane gets focus are checked
here, over every app dialog AND the setup program, because a chain walk alone
passed in NarrateX while every licence opened ringed:

- the chain is walked FROM THE WINDOW, never from `focusWidget()`, since a walk
  from there skips the very widget the dialog opened on;
- a reading pane whose policy includes ClickFocus fails, whether or not it is
  in the chain, since a click would focus it;
- a dialog whose opening focus is a reading pane fails.

A reading pane is a scroll area that is read: not an item view (its selection
drives the board, so it is a control) and not an EDITABLE text view (the paste
box is typed into, so it is a control too).
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QDialog,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tests.structural.test_focus_chain import app_dialogs

_CHAIN_LIMIT = 200
_LONG_TEXT = "\n".join(f"line {n}" for n in range(400))


@pytest.fixture()
def app() -> QApplication:
    instance = QApplication.instance()
    assert isinstance(instance, QApplication)
    return instance


def is_reading_pane(widget) -> bool:
    """A scroll area that is read: not an item view, not editable text."""
    if not isinstance(widget, QAbstractScrollArea):
        return False
    if isinstance(widget, QAbstractItemView):
        return False
    if isinstance(widget, (QTextEdit, QPlainTextEdit)):
        return widget.isReadOnly()
    return True


def _overflows(area) -> bool:
    return (
        area.verticalScrollBar().maximum() > 0
        or area.horizontalScrollBar().maximum() > 0
    )


def _stops(window: QWidget) -> list[QWidget]:
    """Every Tab stop in the window's chain, walked from the window itself."""
    found, widget = [], window
    for _ in range(_CHAIN_LIMIT):
        widget = widget.nextInFocusChain()
        if widget is window:
            break
        if (
            widget.focusPolicy() & Qt.FocusPolicy.TabFocus
            and widget.isVisible()
            and widget.isEnabled()
        ):
            found.append(widget)
    return found


def opening_focus(surface: QWidget, stops: list[QWidget]):
    """The widget a dialog opens on.

    Offscreen never activates a window, so a dialog that leaves the choice to
    the platform reads `focusWidget()` None here. Measured on the Windows
    platform, activation hands focus to the first stop of the chain (the setup
    program's licence opened on its text), so that is what None is taken to be.
    """
    focused = surface.focusWidget()
    if focused is None and stops:
        return stops[0]
    return focused


def pane_offences(surface: QWidget) -> list[str]:
    name = type(surface).__name__
    found = []
    stops = _stops(surface)
    for pane in surface.findChildren(QAbstractScrollArea):
        if not is_reading_pane(pane) or not pane.isVisible():
            continue
        label = type(pane).__name__
        if pane.focusPolicy() & Qt.FocusPolicy.ClickFocus:
            found.append(f"{name}: {label} is a reading pane a click would focus")
        elif pane in stops and not _overflows(pane):
            found.append(f"{name}: {label} is a reading pane that scrolls nowhere")
    if isinstance(surface, QDialog) and is_reading_pane(opening_focus(surface, stops)):
        found.append(f"{name}: opens on its reading pane")
    return found


def surface_offences(surfaces: list[QWidget]) -> list[str]:
    found = []
    for surface in surfaces:
        surface.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        surface.show()
        QApplication.processEvents()
        found.extend(pane_offences(surface))
        surface.close()
        surface.deleteLater()
    QApplication.processEvents()
    return found


def _installer_surfaces(monkeypatch: pytest.MonkeyPatch) -> list[QWidget]:
    import installer.ui.main_window as installer_window
    from installer.ops.payload import installer_licence_text, licence_text
    from installer.state.model import InstallState, StateSnapshot
    from installer.ui.close_app_dialog import CloseAppDialog
    from installer.ui.licence_dialog import LicenceDialog
    from installer.ui.uninstall_dialog import UninstallDialog

    # Never read the registry: a fixed state that shows every action button.
    snapshot = StateSnapshot(
        state=InstallState.UPGRADE,
        bundled_version="2.0.0",
        installed_version="1.0.0",
        install_dir=installer_window.install_target(),
        autostart=False,
    )
    monkeypatch.setattr(installer_window, "detect", lambda *_args: snapshot)
    window = installer_window.InstallerWindow()
    return [
        window,
        LicenceDialog(licence_text(), "Licence", window),
        LicenceDialog(installer_licence_text(), "Notice", window),
        LicenceDialog("short", "Short", window),
        CloseAppDialog(window),
        UninstallDialog(window),
    ]


def test_no_app_dialog_offers_a_reading_pane(app: QApplication) -> None:
    del app
    assert surface_offences([dialog for _name, dialog in app_dialogs()]) == []


def test_no_installer_surface_offers_a_reading_pane(
    app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    del app
    assert surface_offences(_installer_surfaces(monkeypatch)) == []


def test_the_paste_box_is_a_control_not_a_reading_pane(app: QApplication) -> None:
    """The one ringed text view must be editable; otherwise its exemption lies."""
    from postalgambit.ui.theme import IMPORT_TEXT

    del app
    dialog = dict(app_dialogs())["ImportDialog"]
    box = dialog.findChild(QPlainTextEdit, IMPORT_TEXT)
    assert box is not None and not box.isReadOnly()
    assert not is_reading_pane(box)
    dialog.deleteLater()


def test_the_guard_catches_each_way_a_pane_takes_focus(app: QApplication) -> None:
    """The guard bites: each planted pane is named; the controls are spared."""
    del app
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    clickable = QTextBrowser(dialog)
    clickable.setPlainText(_LONG_TEXT)
    layout.addWidget(clickable)
    fits = QTextBrowser(dialog)
    fits.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    layout.addWidget(fits)
    page = QScrollArea(dialog)
    page.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    layout.addWidget(page)
    layout.addWidget(QPlainTextEdit(dialog))
    layout.addWidget(QPushButton("Close", dialog))
    assert surface_offences([dialog]) == [
        "QDialog: QTextBrowser is a reading pane a click would focus",
        "QDialog: QTextBrowser is a reading pane that scrolls nowhere",
        "QDialog: QScrollArea is a reading pane that scrolls nowhere",
        "QDialog: opens on its reading pane",
    ]
