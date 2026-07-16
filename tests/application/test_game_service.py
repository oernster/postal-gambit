"""Unit tests for the game lifecycle service."""

from __future__ import annotations

import pytest

from postalgambit.application.game_service import GameService
from postalgambit.domain.errors import DivergenceError, DomainError, StorageError
from postalgambit.domain.game import Colour
from postalgambit.domain.identity import Identity
from postalgambit.domain.wire import WireAction, WireMessage
from tests.application.conftest import RULES, new_game
from tests.fakes import InMemoryGameStore, InMemorySettingsStore


class TestCreateGame:
    def test_create_as_white(self, game_service: GameService) -> None:
        record = new_game(game_service, Colour.WHITE)
        assert record.meta.white.name == "Oliver"
        assert record.meta.black.name == "Jane"
        assert record.meta.opponent.email == "jane@example.org"
        assert RULES.moves(record.pgn) == ()
        assert RULES.headers(record.pgn)["GameID"] == record.meta.game_id.value

    def test_create_as_black(self, game_service: GameService) -> None:
        record = new_game(game_service, Colour.BLACK)
        assert record.meta.white.name == "Jane"
        assert record.meta.black.name == "Oliver"

    def test_unconfigured_identity_is_rejected(
        self, store: InMemoryGameStore, game_service: GameService
    ) -> None:
        bare = GameService(
            store=store,
            rules=game_service.rules,
            settings=InMemorySettingsStore(Identity()),
            clock=game_service.clock,
            ids=game_service.ids,
        )
        with pytest.raises(DomainError):
            bare.create_game("Jane", "jane@example.org", Colour.WHITE)


class TestListGetDelete:
    def test_list_is_sorted_newest_first(self, game_service: GameService) -> None:
        first = new_game(game_service)
        second = new_game(game_service)
        listed = game_service.list_games()
        assert [r.meta.game_id for r in listed] == [
            second.meta.game_id,
            first.meta.game_id,
        ]

    def test_get_and_delete(self, game_service: GameService) -> None:
        record = new_game(game_service)
        assert game_service.get(record.meta.game_id) == record
        game_service.delete(record.meta.game_id)
        with pytest.raises(StorageError):
            game_service.get(record.meta.game_id)


class TestResign:
    def test_resign_as_white_gives_black_the_win(
        self, game_service: GameService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        updated, message = game_service.resign(record.meta.game_id)
        status = RULES.status(updated.pgn)
        assert status.result == "0-1"
        assert status.description == "resignation, Black wins"
        assert message.action is WireAction.RESIGN
        assert game_service.get(record.meta.game_id).pgn == updated.pgn

    def test_resign_as_black_gives_white_the_win(
        self, game_service: GameService
    ) -> None:
        record = new_game(game_service, Colour.BLACK)
        updated, _ = game_service.resign(record.meta.game_id)
        assert RULES.status(updated.pgn).result == "1-0"

    def test_resigning_a_finished_game_is_rejected(
        self, game_service: GameService
    ) -> None:
        record = new_game(game_service)
        game_service.resign(record.meta.game_id)
        with pytest.raises(DomainError):
            game_service.resign(record.meta.game_id)


class TestAcceptDraw:
    def test_accept_open_offer(
        self, game_service: GameService, store: InMemoryGameStore
    ) -> None:
        record = new_game(game_service)
        offered = record.with_pgn(
            record.pgn, record.meta.updated_at, draw_offer_open=True
        )
        store.save(offered)
        updated, message = game_service.accept_draw(record.meta.game_id)
        assert RULES.status(updated.pgn).description == "agreed draw"
        assert message.action is WireAction.DRAW_ACCEPT

    def test_accept_without_offer_is_rejected(self, game_service: GameService) -> None:
        record = new_game(game_service)
        with pytest.raises(DomainError):
            game_service.accept_draw(record.meta.game_id)


class TestCreateFromWire:
    def make_invite(self, game_service: GameService) -> WireMessage:
        inviter = new_game(game_service, Colour.BLACK)
        message = WireMessage(action=WireAction.INVITE, pgn=inviter.pgn)
        game_service.delete(inviter.meta.game_id)
        return message

    def test_create_from_invite_derives_my_colour_from_turn(
        self, game_service: GameService
    ) -> None:
        message = self.make_invite(game_service)
        record = game_service.create_from_wire(message, "jane@example.org")
        assert record.meta.my_colour is Colour.WHITE
        assert record.meta.me.email == "o@example.org"
        assert record.meta.opponent.email == "jane@example.org"
        assert record.meta.white.name == "Jane"
        assert record.meta.black.name == "Oliver"

    def test_create_from_move_message_carries_draw_offer(
        self, game_service: GameService
    ) -> None:
        inviter = new_game(game_service, Colour.WHITE)
        applied = RULES.apply_uci(inviter.pgn, "e2", "e4")
        game_service.delete(inviter.meta.game_id)
        message = WireMessage(
            action=WireAction.MOVE, pgn=applied.new_pgn, offer_draw=True
        )
        record = game_service.create_from_wire(message, "jane@example.org")
        assert record.meta.my_colour is Colour.BLACK
        assert record.meta.draw_offer_open is True

    def test_existing_game_is_rejected(self, game_service: GameService) -> None:
        record = new_game(game_service)
        message = WireMessage(action=WireAction.INVITE, pgn=record.pgn)
        with pytest.raises(DivergenceError):
            game_service.create_from_wire(message, "jane@example.org")

    def test_ending_actions_cannot_start_a_game(
        self, game_service: GameService
    ) -> None:
        message = WireMessage(
            action=WireAction.RESIGN, pgn=self.make_invite(game_service).pgn
        )
        with pytest.raises(DivergenceError):
            game_service.create_from_wire(message, "jane@example.org")
