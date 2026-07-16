"""Turning a wire message into a ready-to-send email draft."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from postalgambit.application.dto import EmailDraft, MoveApplied
from postalgambit.application.ports import RulesEngine
from postalgambit.domain.applink import encode_import_link
from postalgambit.domain.game import Colour, GameRecord
from postalgambit.domain.subject import build_subject
from postalgambit.domain.wire import WireAction, WireMessage, render_block

MAILTO_URI_MAX = 6000
LINK_LEAD_IN = "With Postal Gambit installed, one click imports this move:"
FOOTER = "Sent with Postal Gambit: https://github.com/oernster/postal-gambit"

_COLOUR_LABELS = {Colour.WHITE: "White", Colour.BLACK: "Black"}


@dataclass(frozen=True, slots=True)
class ExportService:
    rules: RulesEngine

    def build_email(
        self,
        record: GameRecord,
        message: WireMessage,
        applied: MoveApplied | None = None,
    ) -> EmailDraft:
        subject = self._subject(record, message, applied)
        body = self._body(record, message, applied)
        to = record.meta.opponent.email
        uri = (
            f"mailto:{quote(to, safe='@')}"
            f"?subject={quote(subject, safe='')}"
            f"&body={quote(body.replace(chr(10), chr(13) + chr(10)), safe='')}"
        )
        return EmailDraft(
            to=to,
            subject=subject,
            body=body,
            mailto_uri=uri,
            mailto_ok=len(uri) <= MAILTO_URI_MAX,
        )

    def _subject(
        self,
        record: GameRecord,
        message: WireMessage,
        applied: MoveApplied | None,
    ) -> str:
        short_id = record.meta.game_id.short
        if message.action is WireAction.MOVE:
            last = self._last_move(message, applied)
            if last is not None:
                move_number, mover, san = last
                return build_subject(short_id, message.action, move_number, san)
        return build_subject(short_id, message.action)

    def _last_move(
        self, message: WireMessage, applied: MoveApplied | None
    ) -> tuple[int, Colour, str] | None:
        """The latest move as (number, mover, san), from the applied result
        or rederived from the PGN when a move email is rebuilt later."""
        if applied is not None:
            return applied.move_number, applied.mover, applied.san
        moves = self.rules.moves(message.pgn)
        if not moves:
            return None
        plies = len(moves)
        mover = Colour.WHITE if plies % 2 == 1 else Colour.BLACK
        return (plies + 1) // 2, mover, moves[-1]

    def _body(
        self,
        record: GameRecord,
        message: WireMessage,
        applied: MoveApplied | None,
    ) -> str:
        meta = record.meta
        lines = [
            f"Postal Gambit: {meta.white.name} (White) vs {meta.black.name} (Black)",
            "",
        ]
        lines.extend(self._narrative(meta.me.name, message, applied))
        lines.extend(["", self.rules.ascii_board(message.pgn), ""])
        block = render_block(message).rstrip("\n")
        lines.append(block)
        lines.extend(["", LINK_LEAD_IN, encode_import_link(block)])
        lines.extend(["", FOOTER, ""])
        return "\n".join(lines)

    def _narrative(
        self, my_name: str, message: WireMessage, applied: MoveApplied | None
    ) -> list[str]:
        if message.action is WireAction.INVITE:
            return [f"{my_name} invites you to a correspondence game. Your move."]
        if message.action is WireAction.RESIGN:
            return [f"{my_name} resigns. You win."]
        if message.action is WireAction.DRAW_ACCEPT:
            return ["Draw agreed. Thanks for the game."]
        lines = []
        last = self._last_move(message, applied)
        if last is not None:
            move_number, mover, san = last
            lines.append(f"Move {move_number} ({_COLOUR_LABELS[mover]}): {san}")
            status = (
                applied.status
                if applied is not None
                else self.rules.status(message.pgn)
            )
            if status.is_over:
                lines.append(f"Game over: {status.description}.")
            else:
                lines.append("Your move.")
        if message.offer_draw:
            lines.append("A draw is offered with this move.")
        return lines
