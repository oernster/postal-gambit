"""Unit tests for boundary DTO validation and square lookup."""

from __future__ import annotations

import pytest

from postalgambit.application.dto import (
    BOARD_SQUARES,
    FILE_ORDER,
    RANK_ORDER,
    BoardView,
)
from postalgambit.domain.game import Colour


def _self_naming_board() -> BoardView:
    """A board where each square holds its own name.

    An index that is off by one then reads back a different square's name
    rather than a plausible piece, so the mapping is asserted rather than
    spot-checked.
    """
    squares = tuple(f"{file}{rank}" for rank in RANK_ORDER for file in FILE_ORDER)
    return BoardView(squares=squares, turn=Colour.WHITE, in_check=False)


class TestBoardView:
    def test_wrong_square_count_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            BoardView(
                squares=("",) * (BOARD_SQUARES - 1), turn=Colour.WHITE, in_check=False
            )


class TestPieceAt:
    def test_every_square_reads_back_its_own_contents(self) -> None:
        view = _self_naming_board()
        for rank in RANK_ORDER:
            for file in FILE_ORDER:
                assert view.piece_at(f"{file}{rank}") == f"{file}{rank}"

    def test_the_documented_corners_land_where_the_docstring_says(self) -> None:
        view = _self_naming_board()
        assert view.squares[0] == view.piece_at("a8")
        assert view.squares[BOARD_SQUARES - 1] == view.piece_at("h1")

    def test_an_empty_square_reads_as_empty(self) -> None:
        view = BoardView(
            squares=("",) * BOARD_SQUARES, turn=Colour.WHITE, in_check=False
        )
        assert view.piece_at("e4") == ""

    def test_an_unknown_file_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            _self_naming_board().piece_at("z1")

    def test_an_unknown_rank_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            _self_naming_board().piece_at("a9")
