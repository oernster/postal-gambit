"""The JSON store facing foreign ids and damaged files, on real files.

The in-memory fake keys by string, so it cannot show a path escaping the
games folder or a file the disk cannot read; these run against the real
adapter in a pytest temporary directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from postalgambit.application.game_service import GameService
from postalgambit.application.import_service import ImportService
from postalgambit.application.move_service import MoveService
from postalgambit.domain.errors import DomainError, PostalGambitError
from postalgambit.domain.game import Colour, GameId
from postalgambit.domain.identity import Identity
from postalgambit.domain.wire import WireAction, WireMessage, render_block
from postalgambit.infrastructure.rules_pychess import PythonChessRulesEngine
from postalgambit.infrastructure.store_json import GAMES_DIR_NAME, JsonGameStore
from tests.fakes import InMemorySettingsStore, SequenceIdGenerator, TickingClock

RULES = PythonChessRulesEngine()
_TRAVERSAL_ID = "../../escaped-a-b-c-xxxxxxxxxxxxxxxx"
_VALID_ID = "5f3a9c2e-8d41-4b7a-9e6f-2c1d0a8b7e55"


def services(data_dir: Path) -> tuple[JsonGameStore, GameService, ImportService]:
    store = JsonGameStore(data_dir)
    games = GameService(
        store=store,
        rules=RULES,
        settings=InMemorySettingsStore(Identity(name="Oliver", email="o@e.org")),
        clock=TickingClock(),
        ids=SequenceIdGenerator(),
    )
    return store, games, ImportService(store=store, rules=RULES, clock=TickingClock())


def invite_with_id(game_id: str) -> str:
    pgn = (
        '[White "Jane"]\n[Black "Oliver"]\n[Result "*"]\n' f'[GameID "{game_id}"]\n\n*'
    )
    return render_block(WireMessage(action=WireAction.INVITE, pgn=pgn))


class TestGameIdIsACanonicalUuid:
    """P-2 and P-13: a GameID is a file name, so only the one spelling a
    uuid has may be one."""

    @pytest.mark.parametrize(
        "bad",
        [
            _TRAVERSAL_ID,
            _VALID_ID.upper(),
            "5f3a9c2e-8d41-4b7a-9e6f-2c1d0a8b7e5g",
            "5f3a9c2e8-d41-4b7a-9e6f-2c1d0a8b7e55",
            "/f3a9c2e-8d41-4b7a-9e6f-2c1d0a8b7e55",
        ],
    )
    def test_anything_but_lowercase_canonical_form_is_refused(self, bad: str) -> None:
        with pytest.raises(DomainError):
            GameId(bad)

    def test_traversal_invite_writes_nothing_anywhere(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "deep" / "data"
        _, games, imports = services(data_dir)
        text = invite_with_id(_TRAVERSAL_ID)
        with pytest.raises(PostalGambitError):
            outcome = imports.import_text(text)
            games.create_from_wire(outcome.message, "jane@example.org")
        assert [p.name for p in tmp_path.rglob("*.json")] == []

    def test_case_variant_cannot_reach_a_stored_game(self, tmp_path: Path) -> None:
        store, games, imports = services(tmp_path)
        games.create_from_wire(
            WireMessage(
                action=WireAction.INVITE,
                pgn=(
                    '[White "Jane"]\n[Black "Oliver"]\n[Result "*"]\n'
                    f'[GameID "{_VALID_ID}"]\n\n*'
                ),
            ),
            "jane@example.org",
        )
        MoveService(store=store, rules=RULES, clock=TickingClock()).my_move(
            GameId(_VALID_ID), "e2", "e4"
        )
        before = (tmp_path / GAMES_DIR_NAME / f"{_VALID_ID}.json").read_bytes()
        mine = store.load(GameId(_VALID_ID)).pgn
        reply = RULES.apply_san(mine.replace(_VALID_ID, _VALID_ID.upper()), "e5")
        reply = reply.new_pgn
        with pytest.raises(PostalGambitError):
            imports.import_text(
                render_block(WireMessage(action=WireAction.MOVE, pgn=reply))
            )
        after = (tmp_path / GAMES_DIR_NAME / f"{_VALID_ID}.json").read_bytes()
        assert after == before


class TestOneDamagedFileDoesNotHideTheRest:
    """P-8: a file the store cannot read is reported and left untouched;
    the games beside it still list."""

    @pytest.mark.parametrize(
        "damage",
        [
            "{ not json",
            "[]",
            '{"version": 1, "meta": {"game_id": "nope"}, "pgn": "*"}',
            '{"version": 1, "meta": [], "pgn": "*"}',
        ],
    )
    def test_good_games_still_list(self, tmp_path: Path, damage: str) -> None:
        _, games, _ = services(tmp_path)
        good = games.create_game("Jane", "jane@example.org", Colour.WHITE)
        damaged = tmp_path / GAMES_DIR_NAME / "zz-damaged.json"
        damaged.write_text(damage, encoding="utf-8")
        listed = games.list_games()
        assert [r.meta.game_id for r in listed] == [good.meta.game_id]
        assert games.unreadable_games() == (str(damaged),)
        assert damaged.read_text(encoding="utf-8") == damage

    def test_a_clean_folder_reports_nothing_unreadable(self, tmp_path: Path) -> None:
        _, games, _ = services(tmp_path)
        games.create_game("Jane", "jane@example.org", Colour.WHITE)
        assert games.unreadable_games() == ()
