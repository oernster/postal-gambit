"""The chess board: a QGraphicsView canvas with mouse and keyboard input.

Interaction is click-click: select a piece, then a destination. The widget
knows nothing about chess rules; a legal-targets provider is injected and a
moveRequested signal carries the chosen squares out to the window.

Keyboard model: all four arrows move the square cursor while the board has
focus (a chess board is genuinely two-dimensional, so the usual canvas rule
of keeping only vertical keys is relaxed here by design); Tab and Shift+Tab
still step the focus ring out. Enter selects and drops, Escape clears.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QKeyEvent, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from postalgambit.application.dto import BoardView
from postalgambit.domain.game import Colour
from postalgambit.ui.theme import TOKENS

BOARD_SIZE = 8
SQUARE_PX = 64
GLYPH_POINT_SIZE = 34
CURSOR_PEN_WIDTH = 3
TARGET_DOT_RATIO = 0.28
FILES = "abcdefgh"

PIECE_GLYPHS = {
    "K": "♔",
    "Q": "♕",
    "R": "♖",
    "B": "♗",
    "N": "♘",
    "P": "♙",
    "k": "♚",
    "q": "♛",
    "r": "♜",
    "b": "♝",
    "n": "♞",
    "p": "♟",
}

TargetsProvider = Callable[[str], tuple[str, ...]]


class BoardWidget(QGraphicsView):
    moveRequested = Signal(str, str)

    def __init__(self, targets_provider: TargetsProvider) -> None:
        super().__init__()
        self._targets_provider = targets_provider
        self._view: BoardView | None = None
        self._orientation = Colour.WHITE
        self._interactive = False
        self._selected: str | None = None
        self._targets: tuple[str, ...] = ()
        self._cursor_square = "e2"
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        side = BOARD_SIZE * SQUARE_PX
        self.setFixedSize(side + 4, side + 4)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_position(
        self, view: BoardView, orientation: Colour, interactive: bool
    ) -> None:
        self._view = view
        self._orientation = orientation
        self._interactive = interactive
        self._selected = None
        self._targets = ()
        self._redraw()

    def clear_board(self) -> None:
        self._view = None
        self._interactive = False
        self._selected = None
        self._targets = ()
        self._scene.clear()

    # Geometry -----------------------------------------------------------

    def _square_name(self, column: int, row: int) -> str:
        if self._orientation is Colour.WHITE:
            return f"{FILES[column]}{BOARD_SIZE - row}"
        return f"{FILES[BOARD_SIZE - 1 - column]}{row + 1}"

    def _square_index(self, name: str) -> int:
        file = FILES.index(name[0])
        rank = int(name[1])
        return (BOARD_SIZE - rank) * BOARD_SIZE + file

    def _square_rect(self, name: str) -> QRectF:
        file = FILES.index(name[0])
        rank = int(name[1])
        if self._orientation is Colour.WHITE:
            column, row = file, BOARD_SIZE - rank
        else:
            column, row = BOARD_SIZE - 1 - file, rank - 1
        return QRectF(column * SQUARE_PX, row * SQUARE_PX, SQUARE_PX, SQUARE_PX)

    # Painting -----------------------------------------------------------

    def _redraw(self) -> None:
        self._scene.clear()
        if self._view is None:
            return
        for row in range(BOARD_SIZE):
            for column in range(BOARD_SIZE):
                name = self._square_name(column, row)
                self._paint_square(name, (row + column) % 2 == 0)
        if self.hasFocus():
            self._paint_cursor()

    def _paint_square(self, name: str, is_light: bool) -> None:
        rect = self._square_rect(name)
        fill = TOKENS["square_light"] if is_light else TOKENS["square_dark"]
        if name == self._selected:
            fill = TOKENS["square_selected"]
        self._scene.addRect(rect, QPen(Qt.PenStyle.NoPen), QBrush(QColor(fill)))
        if name in self._targets:
            dot = rect.adjusted(
                SQUARE_PX * (1 - TARGET_DOT_RATIO) / 2,
                SQUARE_PX * (1 - TARGET_DOT_RATIO) / 2,
                -SQUARE_PX * (1 - TARGET_DOT_RATIO) / 2,
                -SQUARE_PX * (1 - TARGET_DOT_RATIO) / 2,
            )
            self._scene.addEllipse(
                dot,
                QPen(Qt.PenStyle.NoPen),
                QBrush(QColor(TOKENS["square_target"])),
            )
        piece = self._view.squares[self._square_index(name)]
        if piece:
            glyph = self._scene.addSimpleText(
                PIECE_GLYPHS[piece], QFont("Segoe UI Symbol", GLYPH_POINT_SIZE)
            )
            glyph.setBrush(QBrush(QColor("#f5f5f5" if piece.isupper() else "#1a1a1a")))
            bounds = glyph.boundingRect()
            glyph.setPos(
                rect.x() + (SQUARE_PX - bounds.width()) / 2,
                rect.y() + (SQUARE_PX - bounds.height()) / 2,
            )

    def _paint_cursor(self) -> None:
        rect = self._square_rect(self._cursor_square).adjusted(2, 2, -2, -2)
        pen = QPen(QColor(TOKENS["square_cursor"]))
        pen.setWidth(CURSOR_PEN_WIDTH)
        self._scene.addRect(rect, pen, QBrush(Qt.BrushStyle.NoBrush))

    # Interaction --------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self._interactive and self._view is not None:
            point = self.mapToScene(event.position().toPoint())
            column = int(point.x()) // SQUARE_PX
            row = int(point.y()) // SQUARE_PX
            if 0 <= column < BOARD_SIZE and 0 <= row < BOARD_SIZE:
                name = self._square_name(column, row)
                self._cursor_square = name
                self._activate_square(name)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        steps = {
            Qt.Key.Key_Left: (-1, 0),
            Qt.Key.Key_Right: (1, 0),
            Qt.Key.Key_Up: (0, 1),
            Qt.Key.Key_Down: (0, -1),
        }
        if key in steps:
            self._move_cursor(*steps[key])
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self._interactive:
                self._activate_square(self._cursor_square)
            event.accept()
            return
        if key == Qt.Key.Key_Escape and self._selected is not None:
            self._selected = None
            self._targets = ()
            self._redraw()
            event.accept()
            return
        super().keyPressEvent(event)

    def _move_cursor(self, file_step: int, rank_step: int) -> None:
        if self._orientation is Colour.BLACK:
            file_step, rank_step = -file_step, -rank_step
        file = FILES.index(self._cursor_square[0]) + file_step
        rank = int(self._cursor_square[1]) + rank_step
        file = max(0, min(BOARD_SIZE - 1, file))
        rank = max(1, min(BOARD_SIZE, rank))
        self._cursor_square = f"{FILES[file]}{rank}"
        self._redraw()

    def _activate_square(self, name: str) -> None:
        if self._selected is None or name not in self._targets:
            targets = self._targets_provider(name)
            self._selected = name if targets else None
            self._targets = targets
            self._redraw()
            return
        source, self._selected, self._targets = self._selected, None, ()
        self._redraw()
        self.moveRequested.emit(source, name)

    def focusInEvent(self, event) -> None:  # noqa: N802
        super().focusInEvent(event)
        self._redraw()

    def focusOutEvent(self, event) -> None:  # noqa: N802
        super().focusOutEvent(event)
        self._redraw()
