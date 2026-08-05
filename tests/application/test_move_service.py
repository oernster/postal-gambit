"""Unit tests for the move service."""

from __future__ import annotations

import pytest

from postalgambit.application.dto import RANK_ORDER
from postalgambit.application.game_service import GameService
from postalgambit.application.move_service import PROMOTION_RANKS, MoveService
from postalgambit.domain.errors import DomainError, NotYourTurnError
from postalgambit.domain.game import Colour, GameRecord
from postalgambit.domain.wire import WireAction
from tests.application.conftest import new_game

# White's c-pawn eats its way to b7, where b8 is blocked by the knight, so the
# promotion available is the capture bxa8. A real position rather than a
# contrived one, because the question being asked is about a real board.
PROMOTION_LINE = "1. e4 d5 2. exd5 c6 3. dxc6 Nf6 4. cxb7 e6 *"
EMPTY_MOVETEXT = "\n\n*\n"


def _pawn_ready_to_promote(
    game_service: GameService, move_service: MoveService
) -> GameRecord:
    record = new_game(game_service, Colour.WHITE)
    staged = record.with_pgn(
        record.pgn.replace(EMPTY_MOVETEXT, f"\n\n{PROMOTION_LINE}\n"),
        record.meta.updated_at,
    )
    move_service.store.save(staged)
    return staged


def _with_draw_offer(record: GameRecord) -> GameRecord:
    return record.with_pgn(record.pgn, record.meta.updated_at, draw_offer_open=True)


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


class TestIsPromotion:
    def test_both_ends_of_the_board_promote(self) -> None:
        assert PROMOTION_RANKS == (RANK_ORDER[0], RANK_ORDER[-1])

    def test_a_pawn_reaching_the_far_rank_promotes(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = _pawn_ready_to_promote(game_service, move_service)
        assert move_service.is_promotion(record.meta.game_id, "b7", "a8") is True

    def test_a_move_short_of_the_far_rank_does_not(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = _pawn_ready_to_promote(game_service, move_service)
        assert move_service.is_promotion(record.meta.game_id, "b7", "b6") is False

    def test_a_piece_that_is_not_a_pawn_does_not(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = _pawn_ready_to_promote(game_service, move_service)
        assert move_service.is_promotion(record.meta.game_id, "a1", "a8") is False


class TestEligibility:
    def test_in_progress_drops_a_finished_game(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        live = new_game(game_service)
        finished, _ = game_service.resign(new_game(game_service).meta.game_id)
        assert move_service.in_progress((live, finished)) == (live,)

    def test_draw_acceptable_needs_an_open_offer(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        plain = new_game(game_service)
        offered = _with_draw_offer(new_game(game_service))
        assert move_service.draw_acceptable((plain, offered)) == (offered,)

    def test_a_finished_game_cannot_be_drawn_however_it_was_offered(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        finished, _ = game_service.resign(new_game(game_service).meta.game_id)
        assert move_service.draw_acceptable((_with_draw_offer(finished),)) == ()

    def test_awaiting_opponent_is_the_games_i_cannot_move_in(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        mine = new_game(game_service, Colour.WHITE)
        theirs = new_game(game_service, Colour.BLACK)
        assert move_service.awaiting_opponent((mine, theirs)) == (theirs,)

    def test_a_finished_game_is_not_awaiting_anybody(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.BLACK)
        finished, _ = game_service.resign(record.meta.game_id)
        assert move_service.awaiting_opponent((finished,)) == ()


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

    def test_message_carries_my_reply_address(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        _, message, _ = move_service.my_move(record.meta.game_id, "e2", "e4")
        assert message.from_email == "o@example.org"

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
