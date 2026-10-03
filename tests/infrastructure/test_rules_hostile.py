"""The rules adapter refuses games that do not start from the initial
position or that contain a pass, against the real python-chess."""

from __future__ import annotations

import pytest

from postalgambit.application.dto import RESULT_ONGOING
from postalgambit.domain.errors import IllegalMoveError, IllegalPgnError
from postalgambit.infrastructure.rules_pychess import PythonChessRulesEngine

RULES = PythonChessRulesEngine()
_QUEENLESS_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1"
_FOOLS_MATE = "1. f3 e5 2. g4 Qh4#"


class TestOnlyTheInitialPosition:
    @pytest.mark.parametrize(
        "tags",
        [
            f'[SetUp "1"]\n[FEN "{_QUEENLESS_FEN}"]',
            f'[FEN "{_QUEENLESS_FEN}"]',
            '[Variant "Atomic"]',
            '[Variant "Chess960"]',
        ],
    )
    def test_a_supplied_start_is_refused(self, tags: str) -> None:
        with pytest.raises(IllegalPgnError):
            RULES.validate(f'[Result "*"]\n{tags}\n\n1. e4 *')

    def test_a_null_move_in_the_movetext_is_refused(self) -> None:
        with pytest.raises(IllegalPgnError):
            RULES.validate('[Result "*"]\n\n1. e4 -- 2. d4 *')

    def test_a_null_move_cannot_be_applied(self) -> None:
        with pytest.raises(IllegalMoveError):
            RULES.apply_san('[Result "*"]\n\n1. e4 *', "--")


class TestResultFromTheBoard:
    """P-3: a move message's ending is the board's, never the sender's."""

    def test_claimed_ending_is_dropped(self) -> None:
        pgn = RULES.with_result('[Result "*"]\n\n1. e4 *', "0-1", "checkmate")
        cleared = RULES.with_board_result(pgn)
        assert RULES.status(cleared).result == RESULT_ONGOING
        assert "Termination" not in RULES.headers(cleared)

    def test_a_real_mate_keeps_its_result(self) -> None:
        pgn = RULES.with_result(f'[Result "*"]\n\n{_FOOLS_MATE} *', "1-0", "lies")
        cleared = RULES.with_board_result(pgn)
        assert RULES.headers(cleared)["Result"] == "0-1"
        assert RULES.status(cleared).description == "checkmate, Black wins"
