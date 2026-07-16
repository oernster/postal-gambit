"""Integration tests for the python-chess rules adapter (real library)."""

from __future__ import annotations

import pytest

from postalgambit.application.dto import RESULT_ONGOING
from postalgambit.domain.errors import IllegalMoveError, IllegalPgnError
from postalgambit.domain.game import Colour
from postalgambit.infrastructure.rules_pychess import (
    PGN_EXPORT_COLUMNS,
    PythonChessRulesEngine,
)

HEADERS = (
    '[Event "Postal Gambit correspondence game"]\n'
    '[Site "email"]\n'
    '[Date "2026.07.16"]\n'
    '[Round "-"]\n'
    '[White "Oliver"]\n'
    '[Black "Jane"]\n'
    '[Result "*"]\n'
    '[GameID "5f3a9c2e-8d41-4b7a-9e6f-2c1d0a8b7e55"]\n'
)
EMPTY_PGN = HEADERS + "\n*\n"
OPENING_PGN = HEADERS + "\n1. e4 e5 2. Nf3 *\n"
FOOLS_MATE_SETUP = HEADERS + "\n1. f3 e5 2. g4 *\n"

engine = PythonChessRulesEngine()


class TestReadAndValidate:
    def test_empty_game_is_valid(self) -> None:
        engine.validate(EMPTY_PGN)

    def test_no_game_raises(self) -> None:
        with pytest.raises(IllegalPgnError):
            engine.validate("")

    def test_illegal_move_raises(self) -> None:
        with pytest.raises(IllegalPgnError):
            engine.validate(HEADERS + "\n1. e5 *\n")


class TestNormalize:
    def test_round_trip_preserves_moves_and_headers(self) -> None:
        normalized = engine.normalize(OPENING_PGN)
        assert engine.moves(normalized) == ("e4", "e5", "Nf3")
        assert engine.headers(normalized)["White"] == "Oliver"

    def test_lines_fit_the_export_column_limit(self) -> None:
        pgn = EMPTY_PGN
        knight_shuffle = ("Nf3", "Nc6", "Ng1", "Nb8")
        for ply in range(60):
            pgn = engine.apply_san(pgn, knight_shuffle[ply % 4]).new_pgn
        assert all(len(line) <= PGN_EXPORT_COLUMNS for line in pgn.splitlines())


class TestQueries:
    def test_moves_of_empty_game(self) -> None:
        assert engine.moves(EMPTY_PGN) == ()

    def test_turn_alternates(self) -> None:
        assert engine.turn(EMPTY_PGN) is Colour.WHITE
        assert engine.turn(OPENING_PGN) is Colour.BLACK

    def test_headers_include_game_id(self) -> None:
        assert engine.headers(EMPTY_PGN)["GameID"].startswith("5f3a9c2e")

    def test_board_view_initial_position(self) -> None:
        view = engine.board_view(EMPTY_PGN)
        assert len(view.squares) == 64
        assert view.squares[0] == "r"  # a8
        assert view.squares[4] == "k"  # e8
        assert view.squares[60] == "K"  # e1
        assert view.squares[27] == ""  # d5
        assert view.turn is Colour.WHITE
        assert view.in_check is False

    def test_ascii_board_has_labels_and_ranks(self) -> None:
        art = engine.ascii_board(EMPTY_PGN)
        lines = art.splitlines()
        assert lines[0] == "  a b c d e f g h"
        assert lines[1] == "8 r n b q k b n r 8"
        assert lines[8] == "1 R N B Q K B N R 1"
        assert lines[9] == "  a b c d e f g h"

    def test_legal_targets_for_a_knight(self) -> None:
        assert engine.legal_targets(EMPTY_PGN, "g1") == ("f3", "h3")

    def test_legal_targets_of_empty_square(self) -> None:
        assert engine.legal_targets(EMPTY_PGN, "d5") == ()


class TestApplyMoves:
    def test_apply_uci_records_san_number_and_mover(self) -> None:
        applied = engine.apply_uci(EMPTY_PGN, "e2", "e4")
        assert applied.san == "e4"
        assert applied.move_number == 1
        assert applied.mover is Colour.WHITE
        assert applied.status.result == RESULT_ONGOING
        assert engine.moves(applied.new_pgn) == ("e4",)

    def test_apply_uci_illegal_move_raises(self) -> None:
        with pytest.raises(IllegalMoveError):
            engine.apply_uci(EMPTY_PGN, "e2", "e5")

    def test_apply_uci_bad_square_raises(self) -> None:
        with pytest.raises(IllegalMoveError):
            engine.apply_uci(EMPTY_PGN, "z9", "e4")

    def test_apply_uci_bad_promotion_letter_raises(self) -> None:
        with pytest.raises(IllegalMoveError):
            engine.apply_uci(EMPTY_PGN, "e2", "e4", promotion="k")

    def test_promotion_to_queen(self) -> None:
        pgn = EMPTY_PGN
        for san in ("h4", "g5", "hxg5", "Nf6", "g6", "Nc6", "g7", "Ne5", "g8=Q"):
            pgn = engine.apply_san(pgn, san).new_pgn
        assert engine.moves(pgn)[-1] == "g8=Q"

    def test_apply_uci_promotion_letter(self) -> None:
        pgn = EMPTY_PGN
        for san in ("h4", "g5", "hxg5", "Nf6", "g6", "Nc6", "g7", "Ne5"):
            pgn = engine.apply_san(pgn, san).new_pgn
        applied = engine.apply_uci(pgn, "g7", "g8", promotion="n")
        assert applied.san == "g8=N"

    def test_apply_san_illegal_raises(self) -> None:
        with pytest.raises(IllegalMoveError):
            engine.apply_san(EMPTY_PGN, "Ke2")

    def test_checkmate_sets_result_and_status(self) -> None:
        applied = engine.apply_san(FOOLS_MATE_SETUP, "Qh4#")
        assert applied.status.result == "0-1"
        assert applied.status.description == "checkmate, Black wins"
        assert engine.status(applied.new_pgn).is_over is True


class TestStatus:
    def test_in_progress(self) -> None:
        status = engine.status(OPENING_PGN)
        assert status.is_over is False
        assert status.description == "in progress"

    def test_stalemate_reports_a_draw(self) -> None:
        pgn = EMPTY_PGN
        loyd_stalemate = (
            "e3",
            "a5",
            "Qh5",
            "Ra6",
            "Qxa5",
            "h5",
            "Qxc7",
            "Rah6",
            "h4",
            "f6",
            "Qxd7+",
            "Kf7",
            "Qxb7",
            "Qd3",
            "Qxb8",
            "Qh7",
            "Qxc8",
            "Kg6",
            "Qe6",
        )
        for san in loyd_stalemate:
            pgn = engine.apply_san(pgn, san).new_pgn
        status = engine.status(pgn)
        assert status.result == "1/2-1/2"
        assert status.description == "stalemate, draw"

    def test_resignation_result_white_wins(self) -> None:
        pgn = engine.with_result(OPENING_PGN, "1-0", "resignation")
        status = engine.status(pgn)
        assert status.result == "1-0"
        assert status.description == "resignation, White wins"

    def test_resignation_result_black_wins(self) -> None:
        pgn = engine.with_result(OPENING_PGN, "0-1", "resignation")
        assert engine.status(pgn).description == "resignation, Black wins"

    def test_agreed_draw(self) -> None:
        pgn = engine.with_result(OPENING_PGN, "1/2-1/2", "agreed draw")
        assert engine.status(pgn).description == "agreed draw"

    def test_decisive_tag_without_termination_reads_finished(self) -> None:
        pgn = OPENING_PGN.replace('[Result "*"]', '[Result "1-0"]')
        assert engine.status(pgn).description == "finished, White wins"
