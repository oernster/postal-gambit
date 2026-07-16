"""Unit tests for boundary DTO validation."""

from __future__ import annotations

import pytest

from postalgambit.application.dto import BoardView
from postalgambit.domain.game import Colour


class TestBoardView:
    def test_wrong_square_count_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            BoardView(squares=("",) * 63, turn=Colour.WHITE, in_check=False)
