"""Wire format v1 conformance tests, mirroring WIRE_FORMAT.md section by
section: block structure (s3), headers (s4), parsing rules (s6) and the
bare-SAN fallback (s7)."""

from __future__ import annotations

import pytest

from postalgambit.domain.errors import (
    BlockNotFoundError,
    MalformedBlockError,
    UnknownWireActionError,
    UnknownWireVersionError,
)
from postalgambit.domain.wire import (
    BEGIN_LINE,
    END_LINE,
    WireAction,
    WireMessage,
    extract_san,
    parse_block,
    render_block,
)

PGN = (
    '[Event "Postal Gambit correspondence game"]\n'
    '[Site "email"]\n'
    '[Date "2026.07.16"]\n'
    '[Round "-"]\n'
    '[White "Oliver"]\n'
    '[Black "Jane"]\n'
    '[Result "*"]\n'
    '[GameID "5f3a9c2e-8d41-4b7a-9e6f-2c1d0a8b7e55"]\n'
    "\n"
    "1. e4 e5 2. Nf3 Nc6 *"
)


class TestRender:
    def test_move_block_golden(self) -> None:
        block = render_block(WireMessage(WireAction.MOVE, PGN))
        lines = block.splitlines()
        assert lines[0] == BEGIN_LINE
        assert lines[1] == "Action: move"
        assert lines[2] == ""
        assert lines[-1] == END_LINE
        assert PGN in block

    def test_draw_offer_rides_with_a_move(self) -> None:
        block = render_block(WireMessage(WireAction.MOVE, PGN, offer_draw=True))
        assert "Offer: draw" in block.splitlines()

    @pytest.mark.parametrize(
        "action", [WireAction.INVITE, WireAction.DRAW_ACCEPT, WireAction.RESIGN]
    )
    def test_every_action_round_trips(self, action: WireAction) -> None:
        parsed = parse_block(render_block(WireMessage(action, PGN)))
        assert parsed == WireMessage(action, PGN)

    def test_from_header_rides_with_the_message(self) -> None:
        block = render_block(
            WireMessage(WireAction.MOVE, PGN, from_email="oliver@example.org")
        )
        assert "From: oliver@example.org" in block.splitlines()

    def test_from_header_is_omitted_when_blank(self) -> None:
        block = render_block(WireMessage(WireAction.MOVE, PGN))
        assert not any(line.startswith("From:") for line in block.splitlines())


class TestParse:
    def test_round_trip_with_offer(self) -> None:
        message = WireMessage(WireAction.MOVE, PGN, offer_draw=True)
        assert parse_block(render_block(message)) == message

    def test_round_trip_with_from_address(self) -> None:
        message = WireMessage(WireAction.INVITE, PGN, from_email="jane@example.org")
        assert parse_block(render_block(message)) == message

    def test_missing_from_header_parses_blank(self) -> None:
        text = f"{BEGIN_LINE}\nAction: move\n\n{PGN}\n{END_LINE}"
        assert parse_block(text).from_email == ""

    def test_block_embedded_in_full_email_body(self) -> None:
        body = (
            "Hi Jane,\n\nmy move is below.\n\n"
            + render_block(WireMessage(WireAction.MOVE, PGN))
            + "\nSent with Postal Gambit\n"
        )
        assert parse_block(body).action is WireAction.MOVE

    def test_quoted_reply_is_unwrapped(self) -> None:
        block = render_block(WireMessage(WireAction.MOVE, PGN))
        quoted = "\n".join("> " + line for line in block.splitlines())
        assert parse_block(quoted).pgn == PGN

    def test_doubly_quoted_reply_is_unwrapped(self) -> None:
        block = render_block(WireMessage(WireAction.RESIGN, PGN))
        quoted = "\n".join(">> " + line for line in block.splitlines())
        assert parse_block(quoted).action is WireAction.RESIGN

    def test_unknown_headers_are_ignored(self) -> None:
        text = f"{BEGIN_LINE}\nAction: move\nX-Future: something\n\n{PGN}\n{END_LINE}"
        assert parse_block(text).action is WireAction.MOVE

    def test_offer_is_ignored_on_non_move_actions(self) -> None:
        text = f"{BEGIN_LINE}\nAction: resign\nOffer: draw\n\n{PGN}\n{END_LINE}"
        assert parse_block(text).offer_draw is False

    def test_no_block_raises(self) -> None:
        with pytest.raises(BlockNotFoundError):
            parse_block("just an ordinary email about lunch")

    def test_unknown_version_raises(self) -> None:
        text = f"-----BEGIN POSTAL GAMBIT v9-----\nAction: move\n\n{PGN}\n{END_LINE}"
        with pytest.raises(UnknownWireVersionError):
            parse_block(text)

    def test_unknown_action_raises(self) -> None:
        text = f"{BEGIN_LINE}\nAction: teleport\n\n{PGN}\n{END_LINE}"
        with pytest.raises(UnknownWireActionError):
            parse_block(text)

    def test_missing_action_raises(self) -> None:
        text = f"{BEGIN_LINE}\nOffer: draw\n\n{PGN}\n{END_LINE}"
        with pytest.raises(MalformedBlockError):
            parse_block(text)

    def test_invalid_header_line_raises(self) -> None:
        text = f"{BEGIN_LINE}\nnot a header\n\n{PGN}\n{END_LINE}"
        with pytest.raises(MalformedBlockError):
            parse_block(text)

    def test_missing_blank_line_raises(self) -> None:
        text = f"{BEGIN_LINE}\nAction: move"
        with pytest.raises(MalformedBlockError):
            parse_block(text)

    def test_missing_end_line_raises(self) -> None:
        text = f"{BEGIN_LINE}\nAction: move\n\n{PGN}"
        with pytest.raises(MalformedBlockError):
            parse_block(text)

    def test_empty_pgn_raises(self) -> None:
        text = f"{BEGIN_LINE}\nAction: move\n\n\n{END_LINE}"
        with pytest.raises(MalformedBlockError):
            parse_block(text)


class TestExtractSan:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("Nf6", "Nf6"),
            ("my reply is 14... Nf6 thanks", "Nf6"),
            ("14.e4", "e4"),
            ("I castle: O-O", "O-O"),
            ("O-O-O", "O-O-O"),
            ("exd5", "exd5"),
            ("e8=Q", "e8=Q"),
            ("Qxe7+", "Qxe7+"),
            ("Rdxe1#", "Rdxe1#"),
        ],
    )
    def test_finds_the_move(self, text: str, expected: str) -> None:
        assert extract_san(text) == expected

    @pytest.mark.parametrize("text", ["hello there", "see you at 9", ""])
    def test_returns_none_when_no_move_present(self, text: str) -> None:
        assert extract_san(text) is None
