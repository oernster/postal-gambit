"""Email subject-line builder, per the non-normative WIRE_FORMAT convention."""

from __future__ import annotations

from postalgambit.domain.errors import DomainError
from postalgambit.domain.wire import WireAction

SUBJECT_PREFIX = "Postal Gambit"

_ACTION_PHRASES = {
    WireAction.INVITE: "invitation",
    WireAction.DRAW_ACCEPT: "draw accepted",
    WireAction.RESIGN: "resignation",
}


def build_subject(
    short_id: str,
    action: WireAction,
    move_number: int | None = None,
    san: str | None = None,
) -> str:
    prefix = f"[{SUBJECT_PREFIX} {short_id}]"
    if action is WireAction.MOVE:
        if move_number is None or san is None:
            raise DomainError("a move subject needs a move number and SAN")
        return f"{prefix} move {move_number}: {san}"
    return f"{prefix} {_ACTION_PHRASES[action]}"
