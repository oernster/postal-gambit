"""Unit tests for initial PGN construction."""

from __future__ import annotations

from datetime import date

from postalgambit.domain.pgn_tags import (
    escape_tag_value,
    format_pgn_date,
    new_game_pgn,
)
from tests.domain.test_game import GAME_UUID, make_meta


class TestEscaping:
    def test_quotes_and_backslashes_are_escaped(self) -> None:
        assert escape_tag_value('Jane "The Rook" O\\Neil') == (
            'Jane \\"The Rook\\" O\\\\Neil'
        )


class TestDate:
    def test_pgn_date_format(self) -> None:
        assert format_pgn_date(date(2026, 7, 6)) == "2026.07.06"


class TestNewGamePgn:
    def test_builds_seven_tag_roster_plus_game_id(self) -> None:
        pgn = new_game_pgn(make_meta(), date(2026, 7, 16))
        assert pgn == (
            '[Event "Postal Gambit correspondence game"]\n'
            '[Site "email"]\n'
            '[Date "2026.07.16"]\n'
            '[Round "-"]\n'
            '[White "Oliver"]\n'
            '[Black "Jane"]\n'
            '[Result "*"]\n'
            f'[GameID "{GAME_UUID}"]\n'
            "\n"
            "*\n"
        )
