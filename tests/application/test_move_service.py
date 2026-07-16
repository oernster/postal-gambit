"""Unit tests for the move service."""

from __future__ import annotations

import pytest

from postalgambit.application.game_service import GameService
from postalgambit.application.move_service import MoveService
from postalgambit.domain.errors import DomainError, NotYourTurnError
from postalgambit.domain.game import Colour
from postalgambit.domain.wire import WireAction
from tests.application.conftest import new_game


class TestQueries:
    def test_board_and_status(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service)
        view = move_service.board(record.meta.game_id)
        assert view.turn is Colour.WHITE
        assert move_service.status(record.meta.game_id).is_over is False

    def test_moves_lists_the_mainline(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        assert move_service.moves(record.meta.game_id) == ()
        move_service.my_move(record.meta.game_id, "e2", "e4")
        assert move_service.moves(record.meta.game_id) == ("e4",)

    def test_is_my_turn(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        as_white = new_game(game_service, Colour.WHITE)
        as_black = new_game(game_service, Colour.BLACK)
        assert move_service.is_my_turn(as_white) is True
        assert move_service.is_my_turn(as_black) is False

    def test_is_my_turn_is_false_when_over(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service)
        updated, _ = game_service.resign(record.meta.game_id)
        assert move_service.is_my_turn(updated) is False

    def test_legal_targets_on_my_turn(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        assert move_service.legal_targets(record.meta.game_id, "e2") == ("e3", "e4")

    def test_legal_targets_off_turn_are_empty(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.BLACK)
        assert move_service.legal_targets(record.meta.game_id, "e2") == ()


class TestMyMove:
    def test_happy_path_persists_and_builds_message(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        updated, message, applied = move_service.my_move(
            record.meta.game_id, "e2", "e4", offer_draw=True
        )
        assert applied.san == "e4"
        assert applied.move_number == 1
        assert message.action is WireAction.MOVE
        assert message.offer_draw is True
        assert message.pgn == updated.pgn
        assert game_service.get(record.meta.game_id).pgn == updated.pgn

    def test_my_move_clears_a_standing_draw_offer(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        offered = record.with_pgn(
            record.pgn, record.meta.updated_at, draw_offer_open=True
        )
        move_service.store.save(offered)
        updated, _, _ = move_service.my_move(record.meta.game_id, "e2", "e4")
        assert updated.meta.draw_offer_open is False

    def test_off_turn_move_is_rejected(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.BLACK)
        with pytest.raises(NotYourTurnError):
            move_service.my_move(record.meta.game_id, "e2", "e4")

    def test_move_in_finished_game_is_rejected(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        game_service.resign(record.meta.game_id)
        with pytest.raises(DomainError):
            move_service.my_move(record.meta.game_id, "e2", "e4")
