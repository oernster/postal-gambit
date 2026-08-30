"""The one Qt application object the whole suite shares.

Qt permits exactly one application object per process and it cannot be
upgraded afterwards. Two suites here want one: the setup program's worker
tests need only an event loop, while the focus-chain tests need widgets. The
first of those to run would otherwise claim the singleton; since
``tests/installer`` sorts before ``tests/structural``, a bare
``QCoreApplication`` won the race and left every widget test erroring on a
missing ``setStyleSheet``.

So it is created once, here, before any test module is imported: a
``QApplication``, which IS a ``QCoreApplication`` and therefore satisfies both.
The worker tests keep their own fixture and their own meaning; they reuse
whatever instance exists. The claim their docstring makes, that the setup
program's plumbing needs no widget, is about the production code rather than
about this process.

The offscreen platform is selected first, so nothing here wants a display.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

# Built at import time rather than in a fixture, because a fixture runs only
# once a test has already asked for it, which is too late to win the race.
# Held in a module global so it outlives collection.
QT_APPLICATION = QApplication.instance() or QApplication([])
