"""Conformance tests for the postalgambit: import link (WIRE_FORMAT.md s8)."""

from __future__ import annotations

import pytest

from postalgambit.domain.applink import (
    WEB_LINK_BASE,
    decode_import_link,
    encode_import_link,
    encode_web_import_link,
    is_app_link,
    is_web_import_link,
)
from postalgambit.domain.errors import (
    MalformedLinkError,
    UnknownLinkVersionError,
)
from postalgambit.domain.wire import WireAction, WireMessage, render_block
from tests.domain.test_wire import PGN


class TestRoundTrip:
    def test_block_round_trips_through_the_link(self) -> None:
        block = render_block(WireMessage(WireAction.MOVE, PGN, offer_draw=True))
        link = encode_import_link(block)
        assert link.startswith("postalgambit:import?v=1&d=")
        assert decode_import_link(link) == block

    def test_unicode_survives(self) -> None:
        block = render_block(WireMessage(WireAction.MOVE, PGN.replace("Jane", "Zoë")))
        assert decode_import_link(encode_import_link(block)) == block

    def test_surrounding_whitespace_is_tolerated(self) -> None:
        block = render_block(WireMessage(WireAction.INVITE, PGN))
        link = encode_import_link(block)
        assert decode_import_link(f"  {link}\n") == block


class TestWebLink:
    def test_web_link_wraps_the_scheme_query_in_the_fragment(self) -> None:
        block = render_block(WireMessage(WireAction.MOVE, PGN))
        link = encode_web_import_link(block)
        assert link.startswith(f"{WEB_LINK_BASE}#v=1&d=")

    def test_block_round_trips_through_the_web_link(self) -> None:
        block = render_block(WireMessage(WireAction.MOVE, PGN, offer_draw=True))
        assert decode_import_link(encode_web_import_link(block)) == block

    def test_detects_web_links_case_insensitively(self) -> None:
        block = render_block(WireMessage(WireAction.MOVE, PGN))
        link = encode_web_import_link(block)
        assert is_web_import_link(f"  {link.upper()} ")
        assert not is_web_import_link("https://example.org/#v=1&d=x")

    def test_web_link_without_fragment_is_rejected(self) -> None:
        with pytest.raises(MalformedLinkError):
            decode_import_link(WEB_LINK_BASE)
        with pytest.raises(MalformedLinkError):
            decode_import_link(f"{WEB_LINK_BASE}#")


class TestIsAppLink:
    def test_detects_links_case_insensitively(self) -> None:
        assert is_app_link(" POSTALGAMBIT:import?v=1&d=x ")
        assert not is_app_link("mailto:jane@example.org")
        assert not is_app_link("just an email body")


class TestRejection:
    def test_wrong_scheme_is_rejected(self) -> None:
        with pytest.raises(MalformedLinkError):
            decode_import_link("mailto:jane@example.org")

    def test_unknown_action_is_rejected(self) -> None:
        with pytest.raises(MalformedLinkError):
            decode_import_link("postalgambit:teleport?v=1&d=x")

    def test_unknown_version_is_rejected(self) -> None:
        with pytest.raises(UnknownLinkVersionError):
            decode_import_link("postalgambit:import?v=9&d=x")

    def test_missing_payload_is_rejected(self) -> None:
        with pytest.raises(MalformedLinkError):
            decode_import_link("postalgambit:import?v=1")

    def test_garbage_payload_is_rejected(self) -> None:
        with pytest.raises(MalformedLinkError):
            decode_import_link("postalgambit:import?v=1&d=not-a-payload")
