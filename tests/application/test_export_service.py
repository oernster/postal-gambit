"""Unit tests for the email draft builder."""

from __future__ import annotations

from postalgambit.application.dto import GameStatus, MoveApplied
from postalgambit.application.export_service import (
    MAILTO_URI_MAX,
    ExportService,
)
from postalgambit.application.game_service import GameService
from postalgambit.application.move_service import MoveService
from postalgambit.domain.game import Colour
from postalgambit.domain.wire import BEGIN_LINE, WireAction, WireMessage
from tests.application.conftest import RULES, new_game

export_service = ExportService(rules=RULES)


class _BlankBoardRules:
    """Hand-written fake for the one test that needs an oversized body."""

    def ascii_board(self, pgn: str) -> str:
        return ""


class TestMoveDraft:
    def test_draft_carries_subject_body_and_mailto(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        updated, message, applied = move_service.my_move(
            record.meta.game_id, "e2", "e4"
        )
        draft = export_service.build_email(updated, message, applied)
        short_id = updated.meta.game_id.short
        assert draft.to == "jane@example.org"
        assert draft.subject == f"[Postal Gambit {short_id}] move 1: e4"
        assert "Move 1 (White): e4" in draft.body
        assert "Your move." in draft.body
        assert BEGIN_LINE in draft.body
        assert "  a b c d e f g h" in draft.body
        assert "https://oernster.github.io/postal-gambit/open/#v=1&d=" in draft.body
        assert draft.body.rstrip().endswith(
            "Sent with Postal Gambit: https://github.com/oernster/postal-gambit"
        )
        assert draft.mailto_uri.startswith("mailto:jane@example.org?subject=")
        assert "%0D%0A" in draft.mailto_uri
        assert draft.mailto_ok is True

    def test_body_link_decodes_back_to_the_body_block(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        from postalgambit.domain.applink import WEB_LINK_BASE, decode_import_link
        from postalgambit.domain.wire import parse_block

        record = new_game(game_service, Colour.WHITE)
        updated, message, applied = move_service.my_move(
            record.meta.game_id, "e2", "e4"
        )
        draft = export_service.build_email(updated, message, applied)
        link_line = next(
            line for line in draft.body.splitlines() if line.startswith(WEB_LINK_BASE)
        )
        assert parse_block(decode_import_link(link_line)) == message

    def test_draw_offer_line(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        updated, message, applied = move_service.my_move(
            record.meta.game_id, "e2", "e4", offer_draw=True
        )
        draft = export_service.build_email(updated, message, applied)
        assert "A draw is offered with this move." in draft.body

    def test_game_over_line(self, game_service: GameService) -> None:
        record = new_game(game_service, Colour.WHITE)
        status = GameStatus(result="1-0", description="checkmate, White wins")
        applied = MoveApplied(
            new_pgn=record.pgn,
            san="Qh5#",
            move_number=9,
            mover=Colour.WHITE,
            status=status,
        )
        message = WireMessage(action=WireAction.MOVE, pgn=record.pgn)
        draft = export_service.build_email(record, message, applied)
        assert "Game over: checkmate, White wins." in draft.body


class TestOtherDrafts:
    def test_invite(self, game_service: GameService) -> None:
        record = new_game(game_service, Colour.BLACK)
        message = WireMessage(action=WireAction.INVITE, pgn=record.pgn)
        draft = export_service.build_email(record, message)
        assert draft.subject.endswith("] invitation")
        assert "Oliver invites you to a correspondence game." in draft.body

    def test_resign(self, game_service: GameService) -> None:
        record = new_game(game_service, Colour.WHITE)
        updated, message = game_service.resign(record.meta.game_id)
        draft = export_service.build_email(updated, message)
        assert draft.subject.endswith("] resignation")
        assert "Oliver resigns. You win." in draft.body

    def test_draw_accept(self, game_service: GameService) -> None:
        record = new_game(game_service, Colour.WHITE)
        offered = record.with_pgn(
            record.pgn, record.meta.updated_at, draw_offer_open=True
        )
        game_service.store.save(offered)
        updated, message = game_service.accept_draw(record.meta.game_id)
        draft = export_service.build_email(updated, message)
        assert draft.subject.endswith("] draw accepted")
        assert "Draw agreed. Thanks for the game." in draft.body


class TestReExport:
    def test_move_email_rebuilds_without_applied(
        self, game_service: GameService, move_service: MoveService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        updated, _, _ = move_service.my_move(record.meta.game_id, "e2", "e4")
        pgn = RULES.apply_san(updated.pgn, "e5").new_pgn
        message = WireMessage(action=WireAction.MOVE, pgn=pgn)
        draft = export_service.build_email(updated, message)
        assert draft.subject.endswith("] move 1: e5")
        assert "Move 1 (Black): e5" in draft.body
        assert "Your move." in draft.body

    def test_finished_game_rebuild_reports_game_over(
        self, game_service: GameService
    ) -> None:
        record = new_game(game_service, Colour.WHITE)
        pgn = RULES.apply_san(record.pgn, "f3").new_pgn
        pgn = RULES.apply_san(pgn, "e5").new_pgn
        pgn = RULES.apply_san(pgn, "g4").new_pgn
        pgn = RULES.apply_san(pgn, "Qh4#").new_pgn
        message = WireMessage(action=WireAction.MOVE, pgn=pgn)
        draft = export_service.build_email(record, message)
        assert "Game over: checkmate, Black wins." in draft.body

    def test_move_email_with_no_moves_is_rejected(
        self, game_service: GameService
    ) -> None:
        import pytest

        from postalgambit.domain.errors import DomainError

        record = new_game(game_service, Colour.WHITE)
        message = WireMessage(action=WireAction.MOVE, pgn=record.pgn)
        with pytest.raises(DomainError):
            export_service.build_email(record, message)


class TestMailtoLimit:
    def test_oversized_body_disables_mailto(self, game_service: GameService) -> None:
        record = new_game(game_service, Colour.WHITE)
        oversized_pgn = record.pgn + "\n" + ("x" * MAILTO_URI_MAX)
        message = WireMessage(action=WireAction.INVITE, pgn=oversized_pgn)
        oversized_export = ExportService(rules=_BlankBoardRules())
        draft = oversized_export.build_email(record, message)
        assert draft.mailto_ok is False
        assert len(draft.mailto_uri) > MAILTO_URI_MAX
