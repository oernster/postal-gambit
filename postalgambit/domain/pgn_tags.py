"""Initial PGN construction: pure string work, no chess knowledge.

Builds the Seven Tag Roster plus the GameID tag for a brand-new game. All
later PGN mutation happens through the rules engine, which replays and
re-exports; only the zero-move starting document is authored here.
"""

from __future__ import annotations

from datetime import date

from postalgambit.domain.game import GameMeta

PGN_EVENT = "Postal Gambit correspondence game"
PGN_SITE = "email"
PGN_ROUND = "-"
PGN_RESULT_ONGOING = "*"
GAME_ID_TAG = "GameID"


def escape_tag_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def format_pgn_date(when: date) -> str:
    return f"{when.year:04d}.{when.month:02d}.{when.day:02d}"


def new_game_pgn(meta: GameMeta, started_on: date) -> str:
    tags = (
        ("Event", PGN_EVENT),
        ("Site", PGN_SITE),
        ("Date", format_pgn_date(started_on)),
        ("Round", PGN_ROUND),
        ("White", meta.white.name),
        ("Black", meta.black.name),
        ("Result", PGN_RESULT_ONGOING),
        (GAME_ID_TAG, meta.game_id.value),
    )
    lines = [f'[{name} "{escape_tag_value(value)}"]' for name, value in tags]
    return "\n".join(lines) + f"\n\n{PGN_RESULT_ONGOING}\n"
