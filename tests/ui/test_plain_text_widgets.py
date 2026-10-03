"""P-1: text a correspondent wrote is shown as text, never as markup.

A QLabel left on AutoText renders anything that looks like HTML, so an
`<img>` naming a file makes Qt read that file every time it is painted; for
a UNC path on Windows that means a connection to the named host.
These build the real widgets offscreen and put such text where the sender's
words land: the status headline, the import result and the export "To:"
line. Nothing in Qt is mocked.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QLabel

from postalgambit.application.dto import EmailDraft
from postalgambit.ui.central_layout import build_central
from postalgambit.ui.dialogs.export_dialog import ExportDialog
from postalgambit.ui.dialogs.import_dialog import ImportDialog

_PROBE_SIDE = 300


def _probe_markup(tmp_path: Path) -> str:
    """An `<img>` naming a real picture large enough to show in a size hint."""
    picture = tmp_path / "probe.png"
    image = QImage(_PROBE_SIDE, _PROBE_SIDE, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    assert image.save(str(picture))
    return f"<img src='{picture.as_uri()}'>"


def _labels_are_plain(root) -> list[str]:
    return [
        label.text()
        for label in root.findChildren(QLabel)
        if label.textFormat() is not Qt.TextFormat.PlainText
    ]


class TestTheStatusHeadline:
    def test_markup_in_the_headline_loads_nothing(self, tmp_path: Path) -> None:
        widgets = build_central(lambda _source: ())
        label = widgets.turn_label
        label.setText(_probe_markup(tmp_path))
        assert label.textFormat() is Qt.TextFormat.PlainText
        # Measured: on AutoText the hint grows to hold the picture, which is
        # Qt reading the file. As plain text it is one line of characters.
        assert label.sizeHint().height() < _PROBE_SIDE


class TestDialogsShowPlainText:
    def test_every_import_dialog_label_is_plain(self) -> None:
        dialog = ImportDialog(
            run_import=lambda _text, _chosen: None,
            create_new_game=lambda _outcome, _email: None,
            candidate_games=(),
        )
        assert _labels_are_plain(dialog) == []

    def test_every_export_dialog_label_is_plain(self, tmp_path: Path) -> None:
        draft = EmailDraft(
            to=_probe_markup(tmp_path),
            subject="s",
            body="b",
            mailto_uri="mailto:x",
            mailto_ok=True,
        )
        dialog = ExportDialog(draft)
        assert _labels_are_plain(dialog) == []
