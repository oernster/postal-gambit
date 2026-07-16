"""Wire format v1 codec: render and parse the Postal Gambit email block.

Implements WIRE_FORMAT.md exactly. The codec understands structure only;
chess legality is the rules engine's job. Senders are conservative (one
exact format), receivers are liberal (quoted replies are unwrapped, unknown
headers are ignored).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from postalgambit.domain.errors import (
    BlockNotFoundError,
    MalformedBlockError,
    UnknownWireActionError,
    UnknownWireVersionError,
)

WIRE_VERSION = "1"
BEGIN_LINE = f"-----BEGIN POSTAL GAMBIT v{WIRE_VERSION}-----"
END_LINE = "-----END POSTAL GAMBIT-----"

ACTION_HEADER = "Action"
FROM_HEADER = "From"
OFFER_HEADER = "Offer"
OFFER_DRAW_VALUE = "draw"

_BEGIN_PATTERN = re.compile(r"^-----BEGIN POSTAL GAMBIT v(\S+)-----\s*$")
_END_PATTERN = re.compile(r"^-----END POSTAL GAMBIT-----\s*$")
_HEADER_PATTERN = re.compile(r"^([A-Za-z][A-Za-z-]*):\s*(.*?)\s*$")
_QUOTE_PREFIX_PATTERN = re.compile(r"^\s*(?:>\s*)+")

_SAN_PATTERN = re.compile(
    r"^(?:\d+\.(?:\.\.)?)?"
    r"(O-O(?:-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?)"
    r"[+#]?$"
)


class WireAction(Enum):
    INVITE = "invite"
    MOVE = "move"
    DRAW_ACCEPT = "draw-accept"
    RESIGN = "resign"


@dataclass(frozen=True, slots=True)
class WireMessage:
    action: WireAction
    pgn: str
    offer_draw: bool = False
    # The sender's email address, so the recipient's application can create
    # a game from an invite or first move without asking the user to type
    # the opponent's address. Optional: blank when the sender has not
    # configured one, and absent from blocks sent by older versions.
    from_email: str = ""


def render_block(message: WireMessage) -> str:
    lines = [BEGIN_LINE, f"{ACTION_HEADER}: {message.action.value}"]
    if message.from_email:
        lines.append(f"{FROM_HEADER}: {message.from_email}")
    if message.offer_draw:
        lines.append(f"{OFFER_HEADER}: {OFFER_DRAW_VALUE}")
    lines.append("")
    lines.append(message.pgn.strip())
    lines.append(END_LINE)
    return "\n".join(lines) + "\n"


def parse_block(text: str) -> WireMessage:
    lines = text.splitlines()
    start = _find_begin(lines)
    if start is None:
        lines = [_QUOTE_PREFIX_PATTERN.sub("", line) for line in lines]
        start = _find_begin(lines)
    if start is None:
        raise BlockNotFoundError("no Postal Gambit block found in the text")
    return _parse_from(lines, start)


def _find_begin(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        match = _BEGIN_PATTERN.match(line.strip())
        if match:
            if match.group(1) != WIRE_VERSION:
                raise UnknownWireVersionError(
                    f"unknown wire format version {match.group(1)!r}"
                )
            return index
    return None


def _parse_from(lines: list[str], start: int) -> WireMessage:
    headers: dict[str, str] = {}
    cursor = start + 1
    while cursor < len(lines):
        line = lines[cursor].strip()
        if line == "":
            break
        match = _HEADER_PATTERN.match(line)
        if match is None:
            raise MalformedBlockError(f"invalid header line: {lines[cursor]!r}")
        headers[match.group(1).lower()] = match.group(2)
        cursor += 1
    else:
        raise MalformedBlockError("block has no blank line after the headers")

    pgn_lines: list[str] = []
    cursor += 1
    while cursor < len(lines):
        if _END_PATTERN.match(lines[cursor].strip()):
            return _build_message(headers, "\n".join(pgn_lines).strip())
        pgn_lines.append(lines[cursor])
        cursor += 1
    raise MalformedBlockError("block has no END line")


def _build_message(headers: dict[str, str], pgn: str) -> WireMessage:
    action_value = headers.get(ACTION_HEADER.lower())
    if action_value is None:
        raise MalformedBlockError("block has no Action header")
    try:
        action = WireAction(action_value)
    except ValueError:
        raise UnknownWireActionError(f"unknown action {action_value!r}") from None
    if not pgn:
        raise MalformedBlockError("block carries no PGN")
    offer_draw = (
        action is WireAction.MOVE
        and headers.get(OFFER_HEADER.lower(), "").lower() == OFFER_DRAW_VALUE
    )
    return WireMessage(
        action=action,
        pgn=pgn,
        offer_draw=offer_draw,
        from_email=headers.get(FROM_HEADER.lower(), ""),
    )


def extract_san(text: str) -> str | None:
    """Find a bare SAN move in free text, the app-less opponent fallback."""
    for token in text.split():
        match = _SAN_PATTERN.match(token)
        if match:
            return match.group(1) + (token[-1] if token[-1] in "+#" else "")
    return None
