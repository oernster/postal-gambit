"""Human-facing game labels.

The GameID stays in the wire format and email subjects, where it routes
messages; people get the players and a humanised start date instead. When
two games in the same view would read identically the label gains the start
time, and only as a last resort the short id.
"""

from __future__ import annotations

from collections import Counter

from postalgambit.application.dto import GameStatus
from postalgambit.domain.game import GameMeta, GameRecord


def _date_label(meta: GameMeta) -> str:
    started = meta.created_at.astimezone()
    return (
        f"{meta.white.name} vs {meta.black.name} "
        f"(started {started.day} {started:%b %Y})"
    )


def _timed_label(meta: GameMeta) -> str:
    started = meta.created_at.astimezone()
    return (
        f"{meta.white.name} vs {meta.black.name} "
        f"(started {started.day} {started:%b %Y}, {started:%H:%M})"
    )


def game_labels(records: tuple[GameRecord, ...]) -> dict[str, str]:
    """Return a distinct human label per game id within this view."""
    base = {r.meta.game_id.value: _date_label(r.meta) for r in records}
    counts = Counter(base.values())
    labels: dict[str, str] = {}
    for record in records:
        meta = record.meta
        label = base[meta.game_id.value]
        if counts[label] > 1:
            label = _timed_label(meta)
        labels[meta.game_id.value] = label
    timed_counts = Counter(labels.values())
    for record in records:
        meta = record.meta
        if timed_counts[labels[meta.game_id.value]] > 1:
            labels[meta.game_id.value] += f" [{meta.game_id.short}]"
    return labels


def game_label(record: GameRecord) -> str:
    """The label for one game shown on its own (no sibling disambiguation)."""
    return _date_label(record.meta)


def status_text(status: GameStatus, my_turn: bool, draw_offer_open: bool) -> str:
    """The headline over the board: whose move, offers, or how it ended."""
    if status.is_over:
        return f"Game over: {status.description}."
    parts = ["Your move." if my_turn else "Waiting for your opponent."]
    if draw_offer_open:
        parts.append("A draw offer is open; you may accept it.")
    return " ".join(parts)
