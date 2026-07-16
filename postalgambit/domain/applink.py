"""The postalgambit: import link: one click from email to import.

A non-normative companion to the wire format (WIRE_FORMAT.md s8): the email
body carries, besides the human-readable block, a link whose payload is the
same block compressed and base64url-encoded. Clicking it launches the
registered Postal Gambit, which decodes back to the block and runs the
ordinary import validation; the link never bypasses any of it. Clients that
strip unknown URI schemes lose only the shortcut, never the move.
"""

from __future__ import annotations

import base64
import binascii
import zlib
from urllib.parse import parse_qs, quote, unquote

from postalgambit.domain.errors import (
    MalformedLinkError,
    UnknownLinkVersionError,
)

LINK_SCHEME = "postalgambit"
LINK_ACTION = "import"
LINK_VERSION = "1"
_LINK_PREFIX = f"{LINK_SCHEME}:{LINK_ACTION}?"
_VERSION_PARAM = "v"
_DATA_PARAM = "d"


def is_app_link(text: str) -> bool:
    """True when the text is a postalgambit: URI (surrounding space ignored)."""
    return text.strip().lower().startswith(f"{LINK_SCHEME}:")


def encode_import_link(block: str) -> str:
    """Encode a wire block into a clickable import link."""
    compressed = zlib.compress(block.encode("utf-8"))
    data = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return (
        f"{_LINK_PREFIX}{_VERSION_PARAM}={LINK_VERSION}"
        f"&{_DATA_PARAM}={quote(data, safe='')}"
    )


def decode_import_link(uri: str) -> str:
    """Decode an import link back to its wire block text."""
    stripped = uri.strip()
    if not stripped.lower().startswith(f"{LINK_SCHEME}:"):
        raise MalformedLinkError(f"not a {LINK_SCHEME}: link")
    remainder = stripped[len(LINK_SCHEME) + 1 :]
    action, _, query = remainder.partition("?")
    if action.lower() != LINK_ACTION:
        raise MalformedLinkError(f"unknown link action {action!r}")
    params = parse_qs(query, keep_blank_values=True)
    version = params.get(_VERSION_PARAM, [""])[0]
    if version != LINK_VERSION:
        raise UnknownLinkVersionError(f"unknown link version {version!r}")
    data = params.get(_DATA_PARAM, [""])[0]
    if not data:
        raise MalformedLinkError("link carries no payload")
    padded = unquote(data)
    padded += "=" * (-len(padded) % 4)
    try:
        block = zlib.decompress(base64.urlsafe_b64decode(padded)).decode("utf-8")
    except (binascii.Error, ValueError, zlib.error) as error:
        raise MalformedLinkError(f"undecodable link payload: {error}") from error
    return block
