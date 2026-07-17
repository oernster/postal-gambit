"""Human-facing game labels.

Every label carries the short GameID in brackets, the same eight
characters the email subject prefix uses ([Postal Gambit d7d1450f]), so
a game row in the app and its email thread correlate at a glance. The
players and a humanised start date give the human context around it; the
id alone guarantees distinctness, so no further disambiguation is needed.
"""

from __future__ import annotations

from postalgambit.application.dto import GameStatus
from postalgambit.domain.game import GameRecord


def game_title(record: GameRecord) -> str:
    """The players and the short id, kept short enough for a list row."""
    meta = record.meta
    return f"{meta.white.name} vs {meta.black.name} [{meta.game_id.short}]"


def game_started(record: GameRecord) -> str:
    started = record.meta.created_at.astimezone()
    return f"started {started.day} {started:%b %Y}"


def game_label(record: GameRecord) -> str:
    return f"{game_title(record)} ({game_started(record)})"


def game_labels(records: tuple[GameRecord, ...]) -> dict[str, str]:
    """The label per game id for a view of several games."""
    return {record.meta.game_id.value: game_label(record) for record in records}


def state_text(status: GameStatus, my_turn: bool) -> str:
    """The short state under a game row: outcome, your move or waiting."""
    if status.is_over:
        return status.description
    return "your move" if my_turn else "waiting"


def status_text(status: GameStatus, my_turn: bool, draw_offer_open: bool) -> str:
    """The headline over the board: whose move, offers, or how it ended."""
    if status.is_over:
        return f"Game over: {status.description}."
    parts = ["Your move." if my_turn else "Waiting for your opponent."]
    if draw_offer_open:
        parts.append("A draw offer is open; you may accept it.")
    return " ".join(parts)
