"""Every read-through surface reads itself; no working surface does.

Ported from latencylab's dialog tests asserting `findChild(AutoScroller)`. A
surface to READ THROUGH wears the scroller (the About body, the licences in the
application and in the setup program); a surface to ACT ON does not (the
Export body, the Import paste box, the games and moves lists): the reader's
own working text is theirs to pace.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QPlainTextEdit,
    QTextBrowser,
    QTextEdit,
)

from installer.ui.auto_scroller import AutoScroller as InstallerScroller
from postalgambit.ui.auto_scroller import AutoScroller
from tests.structural.test_focus_chain import app_dialogs

REPO = Path(__file__).resolve().parents[2]
READ_THROUGH_APP_DIALOGS = frozenset({"AboutDialog", "LicenceDialog"})
# The only modules allowed to attach a scroller, each to its own reading pane.
SCROLLER_HOMES = frozenset(
    {
        "postalgambit/ui/dialogs/about.py",
        "installer/ui/licence_dialog.py",
    }
)
SCROLLER_DEFINITIONS = frozenset(
    {"postalgambit/ui/auto_scroller.py", "installer/ui/auto_scroller.py"}
)


@pytest.fixture()
def app() -> QApplication:
    instance = QApplication.instance()
    assert isinstance(instance, QApplication)
    return instance


def _scrolling(dialog, scroller_type) -> list[str]:
    return [
        type(area).__name__
        for area in dialog.findChildren(QAbstractScrollArea)
        if area.findChild(scroller_type) is not None
    ]


def test_each_app_dialog_reads_itself_exactly_where_it_is_read(app) -> None:
    found = {}
    for name, dialog in app_dialogs():
        found[name] = _scrolling(dialog, AutoScroller)
        dialog.deleteLater()
    app.processEvents()
    for name, scrolling in found.items():
        expected = ["QTextBrowser"] if name in READ_THROUGH_APP_DIALOGS else []
        assert scrolling == expected, name


def test_the_about_and_licence_bodies_carry_the_scroller(app) -> None:
    dialogs = dict(app_dialogs())
    for name in READ_THROUGH_APP_DIALOGS:
        body = dialogs[name].findChild(QTextBrowser)
        assert body is not None
        assert body.findChild(AutoScroller) is not None, name
    for dialog in dialogs.values():
        dialog.deleteLater()
    app.processEvents()


def test_the_working_text_surfaces_do_not(app) -> None:
    dialogs = dict(app_dialogs())
    for name in ("ExportDialog", "ImportDialog"):
        box = dialogs[name].findChild(QPlainTextEdit)
        assert box is not None
        assert box.findChild(AutoScroller) is None, name
    for dialog in dialogs.values():
        dialog.deleteLater()
    app.processEvents()


def test_both_installer_licences_read_themselves(app) -> None:
    from installer.ops.payload import installer_licence_text, licence_text
    from installer.ui.licence_dialog import LicenceDialog

    for text in (licence_text(), installer_licence_text()):
        dialog = LicenceDialog(text, "Licence")
        view = dialog.findChild(QTextEdit)
        assert view is not None and not isinstance(view, QPlainTextEdit)
        assert view.findChild(InstallerScroller) is not None
        dialog.deleteLater()
    app.processEvents()


def test_only_the_reading_panes_attach_a_scroller() -> None:
    """Item views, the Export body and the paste box stay unscrolled by design."""
    attaching = set()
    for folder in ("postalgambit", "installer"):
        for path in (REPO / folder).rglob("*.py"):
            name = path.relative_to(REPO).as_posix()
            if name in SCROLLER_DEFINITIONS:
                continue
            if "AutoScroller(" in path.read_text(encoding="utf-8"):
                attaching.add(name)
    assert attaching == SCROLLER_HOMES
