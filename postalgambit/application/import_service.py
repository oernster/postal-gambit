"""Importing the opponent's email: block first, bare SAN as fallback."""

from __future__ import annotations

from dataclasses import dataclass

from postalgambit.application.dto import (
    RESULT_BLACK_WINS,
    RESULT_DRAW,
    RESULT_WHITE_WINS,
    TERMINATION_AGREED_DRAW,
    TERMINATION_RESIGNATION,
    ImportKind,
    ImportOutcome,
)
from postalgambit.application.ports import Clock, GameStore, RulesEngine
from postalgambit.domain.applink import (
    decode_import_link,
    is_app_link,
    is_web_import_link,
)
from postalgambit.domain.errors import (
    BlockNotFoundError,
    DivergenceError,
    MalformedBlockError,
)
from postalgambit.domain.game import Colour, GameId, GameRecord
from postalgambit.domain.pgn_tags import GAME_ID_TAG
from postalgambit.domain.wire import (
    WireAction,
    WireMessage,
    extract_san,
    looks_like_pgn,
    parse_block,
    quoted_reply_text,
)


@dataclass(frozen=True, slots=True)
class ImportService:
    store: GameStore
    rules: RulesEngine
    clock: Clock

    def import_text(
        self, text: str, chosen_game_id: GameId | None = None
    ) -> ImportOutcome:
        # A pasted or clicked import link (postalgambit: scheme or its
        # https wrapper) decodes to the wire block it carries, then follows
        # exactly the same validation as a paste.
        if is_app_link(text) or is_web_import_link(text):
            text = decode_import_link(text)
        try:
            message = parse_block(text)
        except BlockNotFoundError:
            return self._import_bare_san(text, chosen_game_id)
        self.rules.validate(message.pgn)
        game_id = self._game_id_of(message.pgn)
        if not self.store.exists(game_id):
            return self._unknown_game(message, game_id)
        record = self.store.load(game_id)
        reply = self._typed_reply(text, record, message)
        if reply is not None:
            return self._import_bare_san(reply, game_id)
        if message.action is WireAction.INVITE:
            raise DivergenceError(f"game {game_id.short} already exists")
        if message.action is WireAction.MOVE:
            return self._apply_move_message(record, message)
        return self._apply_ending_message(record, message)

    def _typed_reply(
        self, text: str, record: GameRecord, message: WireMessage
    ) -> str | None:
        """The move an app-less opponent typed above my quoted email.

        A mail client's reply quotes the original, block and all. When that
        quoted block is my own last email (it adds nothing to the local game)
        and the reply above it names a move, the reply is the message; the
        quoted block only says which game it belongs to.
        """
        reply = quoted_reply_text(text)
        if reply is None or extract_san(reply) is None:
            return None
        if self.rules.moves(message.pgn) != self.rules.moves(record.pgn):
            return None
        return reply

    def _opponent_moves(
        self, record: GameRecord, message: WireMessage
    ) -> tuple[str, ...]:
        """The moves the inbound game adds to the local one.

        Multi-move catch-up is accepted: the inbound game may replay the
        whole game so far, my moves included. My moves in it must match,
        ply for ply, the ones stored here (the prefix check); every move
        beyond the stored game must be the opponent's. My own moves are
        always played here first, so a new or differing move for my side was
        written by someone else, however legal it is.
        """
        if self.rules.status(record.pgn).is_over:
            raise DivergenceError("the local game is already over")
        local_moves = self.rules.moves(record.pgn)
        inbound_moves = self.rules.moves(message.pgn)
        if inbound_moves[: len(local_moves)] != local_moves:
            raise DivergenceError("the inbound game does not extend the local moves")
        added = range(len(local_moves), len(inbound_moves))
        if any(Colour.of_ply(ply) is record.meta.my_colour for ply in added):
            raise DivergenceError(
                "the inbound game plays a new move for your side that is not "
                "stored here"
            )
        return inbound_moves[len(local_moves) :]

    def _game_id_of(self, pgn: str) -> GameId:
        value = self.rules.headers(pgn).get(GAME_ID_TAG)
        if value is None:
            raise MalformedBlockError("the PGN has no GameID tag")
        return GameId(value)

    def _unknown_game(self, message: WireMessage, game_id: GameId) -> ImportOutcome:
        if message.action not in (WireAction.INVITE, WireAction.MOVE):
            raise DivergenceError(
                f"game {game_id.short} is unknown; a {message.action.value} "
                "message cannot start one"
            )
        return ImportOutcome(
            kind=ImportKind.NEW_GAME,
            detail=f"new game {game_id.short} offered",
            message=message,
        )

    def _apply_move_message(
        self, record: GameRecord, message: WireMessage
    ) -> ImportOutcome:
        added = self._opponent_moves(record, message)
        if not added:
            raise DivergenceError("the inbound game carries no new moves")
        # A move ends the game only when the board says so; the sender's
        # Result and Termination tags are not kept.
        pgn = self.rules.with_board_result(message.pgn)
        status = self.rules.status(pgn)
        updated = record.with_pgn(
            pgn, self.clock.now(), draw_offer_open=message.offer_draw
        )
        self.store.save(updated)
        if status.is_over:
            return ImportOutcome(
                kind=ImportKind.GAME_OVER,
                detail=f"game over: {status.description}",
                record=updated,
            )
        return ImportOutcome(
            kind=ImportKind.APPLIED,
            detail=f"move applied: {added[-1]}",
            record=updated,
        )

    def _apply_ending_message(
        self, record: GameRecord, message: WireMessage
    ) -> ImportOutcome:
        self._opponent_moves(record, message)
        if message.action is WireAction.DRAW_ACCEPT and not record.meta.my_draw_offer:
            raise DivergenceError("a draw was accepted that you did not offer")
        expected, termination = self._expected_ending(record, message)
        claimed = self.rules.status(message.pgn).result
        if claimed != expected:
            raise DivergenceError(
                f"a {message.action.value} should carry result {expected}, "
                f"got {claimed}"
            )
        # Restated in our own words: the sender's Termination text is shown
        # to the user as the ending, so it is not trusted to be text at all.
        pgn = self.rules.with_result(message.pgn, expected, termination)
        status = self.rules.status(pgn)
        updated = record.with_pgn(pgn, self.clock.now())
        self.store.save(updated)
        return ImportOutcome(
            kind=ImportKind.GAME_OVER,
            detail=f"game over: {status.description}",
            record=updated,
        )

    def _expected_ending(
        self, record: GameRecord, message: WireMessage
    ) -> tuple[str, str]:
        """The result and our own description of an inbound ending."""
        if message.action is WireAction.DRAW_ACCEPT:
            return RESULT_DRAW, TERMINATION_AGREED_DRAW
        winner = (
            RESULT_WHITE_WINS
            if record.meta.my_colour is Colour.WHITE
            else RESULT_BLACK_WINS
        )
        return winner, TERMINATION_RESIGNATION

    def _import_bare_san(
        self, text: str, chosen_game_id: GameId | None
    ) -> ImportOutcome:
        if looks_like_pgn(text):
            raise BlockNotFoundError(
                "this is a PGN game without its Postal Gambit block; paste the "
                "whole email, including the lines from BEGIN to END"
            )
        san = extract_san(text)
        if san is None:
            raise BlockNotFoundError(
                "no Postal Gambit block and no chess move found in the text"
            )
        if chosen_game_id is None:
            return ImportOutcome(
                kind=ImportKind.NEEDS_GAME_CHOICE,
                detail=f"found move {san}; choose the game it belongs to",
            )
        record = self.store.load(chosen_game_id)
        if self.rules.status(record.pgn).is_over:
            raise DivergenceError("the local game is already over")
        if self.rules.turn(record.pgn) is record.meta.my_colour:
            raise DivergenceError("it is your move; there is nothing to import")
        applied = self.rules.apply_san(record.pgn, san)
        updated = record.with_pgn(applied.new_pgn, self.clock.now())
        self.store.save(updated)
        if applied.status.is_over:
            return ImportOutcome(
                kind=ImportKind.GAME_OVER,
                detail=f"game over: {applied.status.description}",
                record=updated,
            )
        return ImportOutcome(
            kind=ImportKind.APPLIED,
            detail=f"move applied: {applied.san}",
            record=updated,
        )
