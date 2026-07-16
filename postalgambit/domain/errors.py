"""Typed exception hierarchy for Postal Gambit."""

from __future__ import annotations


class PostalGambitError(Exception):
    """Base for every application-defined error."""


class DomainError(PostalGambitError):
    """A domain rule was violated."""


class WireError(PostalGambitError):
    """The wire block could not be understood."""


class BlockNotFoundError(WireError):
    """No Postal Gambit block was found in the text."""


class UnknownWireVersionError(WireError):
    """The block declares a version this parser does not know."""


class UnknownWireActionError(WireError):
    """The block declares an action this parser does not know."""


class MalformedBlockError(WireError):
    """The block was found but its structure is invalid."""


class RulesError(PostalGambitError):
    """The rules engine rejected a position or a move."""


class IllegalPgnError(RulesError):
    """A PGN failed to replay legally from the initial position."""


class IllegalMoveError(RulesError):
    """A single move was rejected as illegal in the current position."""


class NotYourTurnError(DomainError):
    """A move was attempted out of turn."""


class DivergenceError(DomainError):
    """An inbound game state is not a legal extension of the local one."""


class StorageError(PostalGambitError):
    """A game or settings document could not be read or written."""
