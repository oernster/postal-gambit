"""Inbound messages written by a hostile or careless sender.

Every message here is something a correspondent can put in an email. Each
test plays it against the real rules engine and asserts the local game is
either refused untouched or advanced only by what the board itself allows.
"""

from __future__ import annotations

import pytest

from postalgambit.application.dto import RESULT_ONGOING, ImportKind
from postalgambit.application.export_service import ExportService
from postalgambit.application.game_service import GameService
from postalgambit.application.import_service import ImportService
from postalgambit.application.move_service import MoveService
from postalgambit.domain.errors import (
    BlockNotFoundError,
    DivergenceError,
    IllegalPgnError,
)
from postalgambit.domain.game import Colour, GameRecord
from postalgambit.domain.wire import WireAction, WireMessage, render_block
from tests.application.conftest import RULES, new_game

_UNKNOWN_ID = "00000000-0000-4000-8000-00000000abcd"
_QUEENLESS_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR b KQkq - 0 1"
_MARKUP = "<img src='file:///probe.png'>"


def sent_e4(
    game_service: GameService, move_service: MoveService, offer_draw: bool = False
) -> GameRecord:
    """A game where I am white and my 1. e4 has been played."""
    record = new_game(game_service, Colour.WHITE)
    updated, _, _ = move_service.my_move(
        record.meta.game_id, "e2", "e4", offer_draw=offer_draw
    )
    return move_service.mark_move_sent(updated.meta.game_id)


def block(action: WireAction, pgn: str) -> str:
    return render_block(WireMessage(action=action, pgn=pgn))


def played(pgn: str, *sans: str) -> str:
    for san in sans:
        pgn = RULES.apply_san(pgn, san).new_pgn
    return pgn


class TestMoveMessageCannotEndTheGame:
    """P-3: a move message's Result and Termination tags are the sender's
    words; only the board decides whether a move ended the game."""

    @pytest.mark.parametrize("claimed", ["0-1", "1/2-1/2"])
    def test_claimed_result_is_ignored(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
        claimed: str,
    ) -> None:
        record = sent_e4(game_service, move_service)
        pgn = RULES.with_result(played(record.pgn, "e5"), claimed, "checkmate")
        outcome = import_service.import_text(block(WireAction.MOVE, pgn))
        assert outcome.kind is ImportKind.APPLIED
        assert RULES.status(outcome.record.pgn).result == RESULT_ONGOING
        assert "Termination" not in RULES.headers(outcome.record.pgn)

    def test_a_game_created_from_the_wire_starts_unfinished(
        self, game_service: GameService
    ) -> None:
        pgn = new_game(game_service, Colour.BLACK).pgn
        pgn = pgn.replace(pgn.split('[GameID "')[1].split('"')[0], _UNKNOWN_ID)
        pgn = RULES.with_result(pgn, "1-0", "resignation")
        message = WireMessage(action=WireAction.INVITE, pgn=pgn)
        record = game_service.create_from_wire(message, "jane@example.org")
        assert RULES.status(record.pgn).is_over is False


class TestDrawAcceptNeedsAnOffer:
    """P-4: a draw can only be accepted when I offered one."""

    def test_unoffered_draw_accept_is_refused(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        pgn = RULES.with_result(record.pgn, "1/2-1/2", "agreed draw")
        with pytest.raises(DivergenceError):
            import_service.import_text(block(WireAction.DRAW_ACCEPT, pgn))
        stored = move_service.store.load(record.meta.game_id)
        assert RULES.status(stored.pgn).is_over is False

    def test_offered_draw_accept_ends_the_game(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service, offer_draw=True)
        pgn = RULES.with_result(record.pgn, "1/2-1/2", "agreed draw")
        outcome = import_service.import_text(block(WireAction.DRAW_ACCEPT, pgn))
        assert outcome.kind is ImportKind.GAME_OVER


class TestEndingTextIsOurOwn:
    """P-1, application half: the sender's Termination text never becomes
    the game's status line; the ending is described in our own words."""

    def test_resignation_termination_is_replaced(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        pgn = RULES.with_result(record.pgn, "1-0", _MARKUP)
        outcome = import_service.import_text(block(WireAction.RESIGN, pgn))
        description = RULES.status(outcome.record.pgn).description
        assert description == "resignation, White wins"
        assert "<" not in outcome.detail


class TestReplayStartsFromTheInitialPosition:
    """P-5 and P-6: every move legal from the initial position, so no pass
    and no position supplied by the sender."""

    def test_null_move_is_refused(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        pgn = record.pgn.replace("1. e4 *", "1. e4 -- *")
        assert "--" in pgn
        with pytest.raises(IllegalPgnError):
            import_service.import_text(block(WireAction.MOVE, pgn))

    def test_setup_position_is_refused(self, import_service: ImportService) -> None:
        pgn = (
            '[White "Jane"]\n[Black "Oliver"]\n[Result "*"]\n'
            f'[GameID "{_UNKNOWN_ID}"]\n[SetUp "1"]\n[FEN "{_QUEENLESS_FEN}"]\n\n*'
        )
        with pytest.raises(IllegalPgnError):
            import_service.import_text(block(WireAction.INVITE, pgn))


class TestOnlyTheOpponentMoves:
    """P-7, as ruled: multi-move catch-up stays. An inbound game may carry
    my moves only where they match, ply for ply, the moves stored here; a
    new or differing move for my side was written by someone else."""

    @staticmethod
    def my_nf3_waiting(
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> GameRecord:
        """Stored here: 1. e4 e5 2. Nf3, my Nf3 sent and unanswered."""
        record = sent_e4(game_service, move_service)
        import_service.import_text(block(WireAction.MOVE, played(record.pgn, "e5")))
        move_service.my_move(record.meta.game_id, "g1", "f3")
        return move_service.mark_move_sent(record.meta.game_id)

    def test_catch_up_replaying_my_stored_moves_is_accepted(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = self.my_nf3_waiting(game_service, move_service, import_service)
        full = played(record.pgn, "Nc6")
        outcome = import_service.import_text(block(WireAction.MOVE, full))
        assert outcome.kind is ImportKind.APPLIED
        assert RULES.moves(outcome.record.pgn) == ("e4", "e5", "Nf3", "Nc6")

    @pytest.mark.parametrize(
        "line",
        [("e4", "e5", "Nf3", "Nc6", "Bb5", "a6"), ("e4", "e5", "Nc3", "Nc6")],
        ids=["invents_a_move_for_me", "alters_my_stored_move"],
    )
    def test_a_new_or_altered_move_for_my_side_is_refused(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
        line: tuple[str, ...],
    ) -> None:
        record = self.my_nf3_waiting(game_service, move_service, import_service)
        start = record.pgn.split("\n\n")[0] + "\n\n*"
        with pytest.raises(DivergenceError):
            import_service.import_text(block(WireAction.MOVE, played(start, *line)))
        stored = move_service.store.load(record.meta.game_id)
        assert RULES.moves(stored.pgn) == ("e4", "e5", "Nf3")

    def test_extension_playing_my_side_is_refused(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        pgn = played(record.pgn, "e5", "Nf3", "Nc6")
        with pytest.raises(DivergenceError):
            import_service.import_text(block(WireAction.MOVE, pgn))
        stored = move_service.store.load(record.meta.game_id)
        assert RULES.moves(stored.pgn) == ("e4",)

    def test_resignation_playing_my_side_is_refused(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        pgn = RULES.with_result(played(record.pgn, "e5", "Nf3"), "1-0", "resignation")
        with pytest.raises(DivergenceError):
            import_service.import_text(block(WireAction.RESIGN, pgn))


class TestQuotedReplyFromAnAppLessOpponent:
    """P-9: a bare move typed above the quoted original email is the reply;
    the quoted block is my own email and routes it to the game."""

    @staticmethod
    def quoted_reply(reply: str, body: str) -> str:
        quoted = "\n".join(f"> {line}" for line in body.splitlines())
        return f"{reply}\n\nOn Tue, 3 Oct 2026, Oliver wrote:\n{quoted}\n"

    def test_reply_above_a_quoted_move_is_applied(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        message = WireMessage(action=WireAction.MOVE, pgn=record.pgn)
        body = ExportService(rules=RULES).build_email(record, message).body
        outcome = import_service.import_text(self.quoted_reply("e5", body))
        assert outcome.kind is ImportKind.APPLIED
        assert RULES.moves(outcome.record.pgn) == ("e4", "e5")

    def test_reply_above_a_quoted_invitation_is_applied(
        self, game_service: GameService, import_service: ImportService
    ) -> None:
        record = new_game(game_service, Colour.BLACK)
        message = WireMessage(action=WireAction.INVITE, pgn=record.pgn)
        body = ExportService(rules=RULES).build_email(record, message).body
        outcome = import_service.import_text(self.quoted_reply("e4", body))
        assert outcome.kind is ImportKind.APPLIED
        assert RULES.moves(outcome.record.pgn) == ("e4",)

    def test_a_quoted_block_with_a_new_move_still_wins(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        forwarded = self.quoted_reply(
            "d5", block(WireAction.MOVE, played(record.pgn, "e5"))
        )
        outcome = import_service.import_text(forwarded)
        assert RULES.moves(outcome.record.pgn) == ("e4", "e5")

    def test_quoted_email_without_a_reply_move_is_still_refused(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        message = WireMessage(action=WireAction.MOVE, pgn=record.pgn)
        body = ExportService(rules=RULES).build_email(record, message).body
        with pytest.raises(DivergenceError):
            import_service.import_text(self.quoted_reply("Thinking.", body))


class TestBarePgnIsNamed:
    """P-12: a PGN pasted without its block is said to be one, rather than
    mined for the first move-shaped word in it."""

    def test_pasted_pgn_without_a_block_is_refused_as_such(
        self,
        game_service: GameService,
        move_service: MoveService,
        import_service: ImportService,
    ) -> None:
        record = sent_e4(game_service, move_service)
        with pytest.raises(BlockNotFoundError, match="PGN"):
            import_service.import_text(played(record.pgn, "e5"))
