"""Unit tests for the import service, simulating the opponent's side with
the real rules engine."""

from __future__ import annotations

import pytest

from postalgambit.application.dto import ImportKind
from postalgambit.application.game_service import GameService
from postalgambit.application.import_service import ImportService
from postalgambit.application.move_service import MoveService
from postalgambit.domain.errors import (
    BlockNotFoundError,
    DivergenceError,
    MalformedBlockError,
)
from postalgambit.domain.game import Colour, GameRecord
from postalgambit.domain.wire import WireAction, WireMessage, render_block
from tests.application.conftest import RULES, new_game


def sent_e4(game_service: GameService, move_service: MoveService) -> GameRecord:
    """A game where I am white and my 1. e4 has gone out by email."""
    record = new_game(game_service, Colour.WHITE)
    updated, _, _ = move_service.my_move(record.meta.game_id, "e2", "e4")
    return updated


def opponent_reply(pgn: str, san: str, offer_draw: bool = False) -> str:
    reply_pgn = RULES.apply_san(pgn, san).new_pgn
    return render_block(
        WireMessage(action=WireAction.MOVE, pgn=reply_pgn, offer_draw=offer_draw)
    )


class TestMoveImport:
    def test_opponent_move_is_applied(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        outcome = import_service.import_text(opponent_reply(record.pgn, "e5"))
        assert outcome.kind is ImportKind.APPLIED
        assert "e5" in outcome.detail
        assert RULES.moves(outcome.record.pgn) == ("e4", "e5")
        assert move_service.is_my_turn(outcome.record) is True

    def test_draw_offer_is_recorded(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        outcome = import_service.import_text(
            opponent_reply(record.pgn, "e5", offer_draw=True)
        )
        assert outcome.record.meta.draw_offer_open is True

    def test_checkmating_move_reports_game_over(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        pgn = RULES.apply_uci(record.pgn, "f2", "f3").new_pgn
        pgn = RULES.apply_san(pgn, "e5").new_pgn
        pgn = RULES.apply_uci(pgn, "g2", "g4").new_pgn
        move_service.store.save(record.with_pgn(pgn, record.meta.updated_at))
        block = opponent_reply(pgn, "Qh4#")
        outcome = import_service.import_text(block)
        assert outcome.kind is ImportKind.GAME_OVER
        assert "checkmate, Black wins" in outcome.detail
        assert RULES.status(outcome.record.pgn).is_over is True

    def test_same_pgn_again_is_divergence(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        reply = opponent_reply(record.pgn, "e5")
        import_service.import_text(reply)
        with pytest.raises(DivergenceError):
            import_service.import_text(reply)

    def test_non_extension_is_divergence(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        foreign = record.pgn.replace("1. e4", "1. d4")
        block = render_block(WireMessage(action=WireAction.MOVE, pgn=foreign))
        with pytest.raises(DivergenceError):
            import_service.import_text(block)

    def test_wrong_parity_extension_is_divergence(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        two_plies = RULES.apply_san(
            RULES.apply_san(record.pgn, "e5").new_pgn, "Nf3"
        ).new_pgn
        block = render_block(WireMessage(action=WireAction.MOVE, pgn=two_plies))
        with pytest.raises(DivergenceError):
            import_service.import_text(block)

    def test_move_for_finished_game_is_divergence(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        reply = opponent_reply(record.pgn, "e5")
        game_service.resign(record.meta.game_id)
        with pytest.raises(DivergenceError):
            import_service.import_text(reply)

    def test_invite_for_existing_game_is_divergence(
        self,
        game_service: GameService,
        import_service: ImportService,
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        block = render_block(WireMessage(action=WireAction.INVITE, pgn=record.pgn))
        with pytest.raises(DivergenceError):
            import_service.import_text(block)

    def test_missing_game_id_tag_is_malformed(
        self, import_service: ImportService
    ) -> None:
        pgn = (
            '[Event "x"]\n[Site "email"]\n[Date "2026.07.16"]\n[Round "-"]\n'
            '[White "A"]\n[Black "B"]\n[Result "*"]\n\n1. e4 *\n'
        )
        block = render_block(WireMessage(action=WireAction.MOVE, pgn=pgn))
        with pytest.raises(MalformedBlockError):
            import_service.import_text(block)


class TestUnknownGame:
    def test_unknown_move_message_offers_new_game(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        reply = opponent_reply(record.pgn, "e5")
        game_service.delete(record.meta.game_id)
        outcome = import_service.import_text(reply)
        assert outcome.kind is ImportKind.NEW_GAME
        assert outcome.message is not None
        assert outcome.record is None

    def test_unknown_resign_message_is_divergence(
        self,
        game_service: GameService,
        import_service: ImportService,
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        pgn = RULES.with_result(record.pgn, "0-1", "resignation")
        game_service.delete(record.meta.game_id)
        block = render_block(WireMessage(action=WireAction.RESIGN, pgn=pgn))
        with pytest.raises(DivergenceError):
            import_service.import_text(block)


class TestEndingImports:
    def test_opponent_resignation_ends_the_game(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        pgn = RULES.with_result(record.pgn, "1-0", "resignation")
        block = render_block(WireMessage(action=WireAction.RESIGN, pgn=pgn))
        outcome = import_service.import_text(block)
        assert outcome.kind is ImportKind.GAME_OVER
        assert "resignation" in outcome.detail

    def test_resignation_with_wrong_winner_is_divergence(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        pgn = RULES.with_result(record.pgn, "0-1", "resignation")
        block = render_block(WireMessage(action=WireAction.RESIGN, pgn=pgn))
        with pytest.raises(DivergenceError):
            import_service.import_text(block)

    def test_draw_acceptance_ends_the_game(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        pgn = RULES.with_result(record.pgn, "1/2-1/2", "agreed draw")
        block = render_block(WireMessage(action=WireAction.DRAW_ACCEPT, pgn=pgn))
        outcome = import_service.import_text(block)
        assert outcome.kind is ImportKind.GAME_OVER
        assert "agreed draw" in outcome.detail

    def test_ending_for_finished_game_is_divergence(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        game_service.resign(record.meta.game_id)
        pgn = RULES.with_result(record.pgn, "1-0", "resignation")
        block = render_block(WireMessage(action=WireAction.RESIGN, pgn=pgn))
        with pytest.raises(DivergenceError):
            import_service.import_text(block)

    def test_ending_that_drops_moves_is_divergence(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        truncated = record.pgn.replace("1. e4 *", "*").replace("1. e4  *", "*")
        pgn = RULES.with_result(truncated, "1-0", "resignation")
        block = render_block(WireMessage(action=WireAction.RESIGN, pgn=pgn))
        with pytest.raises(DivergenceError):
            import_service.import_text(block)


class TestAppLinkImport:
    def test_clicked_link_applies_the_move(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        from postalgambit.domain.applink import encode_import_link

        record = sent_e4(game_service, move_service)
        block = opponent_reply(record.pgn, "e5")
        outcome = import_service.import_text(encode_import_link(block))
        assert outcome.kind is ImportKind.APPLIED
        assert RULES.moves(outcome.record.pgn) == ("e4", "e5")

    def test_link_import_still_detects_divergence(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        from postalgambit.domain.applink import encode_import_link

        record = sent_e4(game_service, move_service)
        link = encode_import_link(opponent_reply(record.pgn, "e5"))
        import_service.import_text(link)
        with pytest.raises(DivergenceError):
            import_service.import_text(link)


class TestBareSanFallback:
    def test_without_a_chosen_game_asks_for_one(
        self, import_service: ImportService
    ) -> None:
        outcome = import_service.import_text("my move is Nf6")
        assert outcome.kind is ImportKind.NEEDS_GAME_CHOICE
        assert "Nf6" in outcome.detail

    def test_applies_to_the_chosen_game(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        outcome = import_service.import_text(
            "I'll reply 1... e5 then", chosen_game_id=record.meta.game_id
        )
        assert outcome.kind is ImportKind.APPLIED
        assert RULES.moves(outcome.record.pgn) == ("e4", "e5")

    def test_no_move_in_text_raises(self, import_service: ImportService) -> None:
        with pytest.raises(BlockNotFoundError):
            import_service.import_text("lovely weather today")

    def test_on_my_turn_is_divergence(
        self,
        game_service: GameService,
        import_service: ImportService,
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        with pytest.raises(DivergenceError):
            import_service.import_text("e5", chosen_game_id=record.meta.game_id)

    def test_for_finished_game_is_divergence(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        game_service.resign(record.meta.game_id)
        with pytest.raises(DivergenceError):
            import_service.import_text("e5", chosen_game_id=record.meta.game_id)

    def test_mating_san_reports_game_over(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        pgn = record.pgn
        for source, target in (("f2", "f3"),):
            pgn = RULES.apply_uci(pgn, source, target).new_pgn
        pgn = RULES.apply_san(pgn, "e5").new_pgn
        pgn = RULES.apply_uci(pgn, "g2", "g4").new_pgn
        updated = record.with_pgn(pgn, record.meta.updated_at)
        move_service.store.save(updated)
        outcome = import_service.import_text("Qh4#", chosen_game_id=record.meta.game_id)
        assert outcome.kind is ImportKind.GAME_OVER
        assert "checkmate, Black wins" in outcome.detail
