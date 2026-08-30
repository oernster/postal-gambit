"""The one place the application asks the desktop to open an address.

This is a seam rather than a call made straight from the window. Reaching for
Qt's opener inside a handler leaves no way to prove the right address is asked
for without either mocking Qt or opening a real browser in the middle of a
test run, so the ask is named here and the window depends on the name.

Nothing in this module fetches anything. The address is handed to whatever the
desktop opens links with and the browser does the asking, which is what leaves
the no-network invariant untouched: Postal Gambit still opens no connection of
its own. See tests/structural/test_no_network.py, which proves it.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def open_externally(address: str) -> bool:
    """Ask the desktop to open this address; False when it declined to."""
    return QDesktopServices.openUrl(QUrl(address))
