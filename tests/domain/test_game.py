"""Unit tests for the core game model."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from postalgambit.domain.errors import DomainError
from postalgambit.domain.game import Colour, GameId, GameMeta, GameRecord, Player

GAME_UUID = "5f3a9c2e-8d41-4b7a-9e6f-2c1d0a8b7e55"
CREATED = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 7, 16, 13, 30, tzinfo=timezone.utc)


def make_meta(my_colour: Colour = Colour.WHITE) -> GameMeta:
    return GameMeta(
        game_id=GameId(GAME_UUID),
        white=Player("Oliver", "oliver@example.org"),
        black=Player("Jane", "jane@example.org"),
        my_colour=my_colour,
        created_at=CREATED,
        updated_at=CREATED,
    )


class TestGameId:
    def test_short_form_is_first_eight_characters(self) -> None:
        assert GameId(GAME_UUID).short == "5f3a9c2e"

    @pytest.mark.parametrize("bad", ["", "abc", "5f3a9c2e8d414b7a9e6f2c1d0a8b7e55"])
    def test_rejects_non_canonical_uuids(self, bad: str) -> None:
        with pytest.raises(DomainError):
            GameId(bad)


class TestColour:
    def test_other_flips_both_ways(self) -> None:
        assert Colour.WHITE.other is Colour.BLACK
        assert Colour.BLACK.other is Colour.WHITE


class TestPlayer:
    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(DomainError):
            Player("   ")

    def test_email_defaults_empty(self) -> None:
        assert Player("Jane").email == ""


class TestGameMeta:
    def test_me_and_opponent_as_white(self) -> None:
        meta = make_meta(Colour.WHITE)
        assert meta.me.name == "Oliver"
        assert meta.opponent.name == "Jane"

    def test_me_and_opponent_as_black(self) -> None:
        meta = make_meta(Colour.BLACK)
        assert meta.me.name == "Jane"
        assert meta.opponent.name == "Oliver"


class TestGameRecord:
    def test_with_pgn_updates_pgn_timestamp_and_offer(self) -> None:
        record = GameRecord(meta=make_meta(), pgn="old")
        updated = record.with_pgn("new", LATER, draw_offer_open=True)
        assert updated.pgn == "new"
        assert updated.meta.updated_at == LATER
        assert updated.meta.draw_offer_open is True
        assert updated.meta.created_at == CREATED
        assert record.pgn == "old"

    def test_with_pgn_clears_offer_by_default(self) -> None:
        record = GameRecord(meta=make_meta(), pgn="old")
        offered = record.with_pgn("mid", LATER, draw_offer_open=True)
        cleared = offered.with_pgn("new", LATER)
        assert cleared.meta.draw_offer_open is False
