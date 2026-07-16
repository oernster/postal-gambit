"""Integration tests for the JSON game store, on a real tmp filesystem."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from postalgambit.domain.errors import StorageError
from postalgambit.domain.game import Colour, GameId, GameRecord
from postalgambit.infrastructure.store_json import JsonGameStore
from tests.domain.test_game import GAME_UUID, LATER, make_meta

OTHER_UUID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


@pytest.fixture()
def store(tmp_path: Path) -> JsonGameStore:
    return JsonGameStore(tmp_path)


def make_record(pgn: str = "stub pgn") -> GameRecord:
    return GameRecord(meta=make_meta(Colour.BLACK), pgn=pgn)


class TestRoundTrip:
    def test_save_then_load(self, store: JsonGameStore) -> None:
        record = make_record()
        store.save(record)
        assert store.load(GameId(GAME_UUID)) == record

    def test_save_overwrites_atomically(self, store: JsonGameStore) -> None:
        record = make_record()
        store.save(record)
        updated = record.with_pgn("new pgn", LATER, draw_offer_open=True)
        store.save(updated)
        loaded = store.load(GameId(GAME_UUID))
        assert loaded.pgn == "new pgn"
        assert loaded.meta.draw_offer_open is True

    def test_exists(self, store: JsonGameStore) -> None:
        assert store.exists(GameId(GAME_UUID)) is False
        store.save(make_record())
        assert store.exists(GameId(GAME_UUID)) is True

    def test_list_all(self, store: JsonGameStore) -> None:
        store.save(make_record())
        assert len(store.list_all()) == 1

    def test_delete(self, store: JsonGameStore) -> None:
        store.save(make_record())
        store.delete(GameId(GAME_UUID))
        assert store.exists(GameId(GAME_UUID)) is False


class TestErrors:
    def test_load_missing_raises(self, store: JsonGameStore) -> None:
        with pytest.raises(StorageError):
            store.load(GameId(OTHER_UUID))

    def test_delete_missing_raises(self, store: JsonGameStore) -> None:
        with pytest.raises(StorageError):
            store.delete(GameId(OTHER_UUID))

    def test_corrupt_json_raises(self, store: JsonGameStore, tmp_path: Path) -> None:
        (tmp_path / "games" / f"{GAME_UUID}.json").write_text("{oops", "utf-8")
        with pytest.raises(StorageError):
            store.load(GameId(GAME_UUID))

    def test_unknown_version_raises(self, store: JsonGameStore, tmp_path: Path) -> None:
        (tmp_path / "games" / f"{GAME_UUID}.json").write_text(
            json.dumps({"version": 99}), "utf-8"
        )
        with pytest.raises(StorageError):
            store.load(GameId(GAME_UUID))

    def test_malformed_document_raises(
        self, store: JsonGameStore, tmp_path: Path
    ) -> None:
        (tmp_path / "games" / f"{GAME_UUID}.json").write_text(
            json.dumps({"version": 1, "meta": {}}), "utf-8"
        )
        with pytest.raises(StorageError):
            store.load(GameId(GAME_UUID))
