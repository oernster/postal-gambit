"""Help | About and the licence viewer."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout, QWidget

from postalgambit.ui.dialogs.neutral_dialog import NeutralDialog, close_row
from postalgambit.ui.icons import get_badge_png_path
from postalgambit.version import APP_AUTHOR, APP_NAME, APP_TAGLINE, __version__

_ICON_PX = 96
_DIALOG_MIN_WIDTH = 540
_BODY_MIN_HEIGHT = 320
_LICENCE_MIN_WIDTH = 680
_LICENCE_MIN_HEIGHT = 520
_LICENCE_FALLBACK = "Licence text not found. See the repository LICENSE file."

_CREDITS = (
    "<li><b>PySide6 (Qt for Python)</b> - LGPL-3.0.</li>"
    "<li><b>python-chess</b> - GPL-3.0 (rules, PGN, SAN).</li>"
    "<li><b>Python</b> - PSF licence.</li>"
    "<li><b>pytest, pytest-cov, black, flake8</b> - MIT (development).</li>"
    "<li><b>Pillow</b> - HPND (icon generation).</li>"
)

_ABOUT_HTML = f"""
<h2>{APP_NAME}</h2>
<p><b>{APP_TAGLINE}</b></p>
<p><b>Version:</b> {__version__}</p>
<p><b>Author:</b> {APP_AUTHOR}</p>
<p>Licensed under GPL-3.0. See the Help menu for the licence text.</p>
<hr>
<h3>Open source credits</h3>
<ul>{_CREDITS}</ul>
<p>Built on the Python and Qt ecosystems, with thanks to their
communities.</p>
"""


class AboutDialog(NeutralDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumWidth(_DIALOG_MIN_WIDTH)
        layout = QVBoxLayout(self)
        badge_path = get_badge_png_path()
        if badge_path is not None:
            badge = QLabel()
            badge.setPixmap(
                QPixmap(str(badge_path)).scaled(
                    _ICON_PX,
                    _ICON_PX,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            badge.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(badge)
        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setMinimumHeight(_BODY_MIN_HEIGHT)
        body.setHtml(_ABOUT_HTML)
        layout.addWidget(body)
        layout.addLayout(close_row(self))


class LicenceDialog(NeutralDialog):
    def __init__(
        self, title: str, path: Path | None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(_LICENCE_MIN_WIDTH, _LICENCE_MIN_HEIGHT)
        layout = QVBoxLayout(self)
        body = QTextBrowser()
        body.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        if path is not None and path.is_file():
            body.setPlainText(path.read_text(encoding="utf-8"))
        else:
            body.setPlainText(_LICENCE_FALLBACK)
        layout.addWidget(body)
        layout.addLayout(close_row(self))
