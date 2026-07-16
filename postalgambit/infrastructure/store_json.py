"""GameStore adapter: one versioned JSON document per game, atomic writes."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from postalgambit.domain.errors import StorageError
from postalgambit.domain.game import Colour, GameId, GameMeta, GameRecord, Player

STORE_VERSION = 1
GAMES_DIR_NAME = "games"
_TMP_SUFFIX = ".tmp"


class JsonGameStore:
    def __init__(self, data_dir: Path) -> None:
        self._games_dir = data_dir / GAMES_DIR_NAME
        self._games_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: GameRecord) -> None:
        path = self._path_for(record.meta.game_id)
        payload = json.dumps(_to_document(record), indent=2)
        tmp_path = path.with_suffix(path.suffix + _TMP_SUFFIX)
        tmp_path.write_text(payload, encoding="utf-8")
        os.replace(tmp_path, path)

    def load(self, game_id: GameId) -> GameRecord:
        path = self._path_for(game_id)
        if not path.exists():
            raise StorageError(f"no stored game {game_id.short}")
        return self._read(path)

    def exists(self, game_id: GameId) -> bool:
        return self._path_for(game_id).exists()

    def list_all(self) -> tuple[GameRecord, ...]:
        return tuple(
            self._read(path) for path in sorted(self._games_dir.glob("*.json"))
        )

    def delete(self, game_id: GameId) -> None:
        path = self._path_for(game_id)
        if not path.exists():
            raise StorageError(f"no stored game {game_id.short}")
        path.unlink()

    def _path_for(self, game_id: GameId) -> Path:
        return self._games_dir / f"{game_id.value}.json"

    def _read(self, path: Path) -> GameRecord:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise StorageError(f"unreadable game file {path.name}: {error}") from error
        if document.get("version") != STORE_VERSION:
            raise StorageError(
                f"unknown store version in {path.name}: {document.get('version')!r}"
            )
        try:
            return _from_document(document)
        except (KeyError, TypeError, ValueError) as error:
            raise StorageError(f"malformed game file {path.name}: {error}") from error


def _to_document(record: GameRecord) -> dict:
    meta = record.meta
    return {
        "version": STORE_VERSION,
        "meta": {
            "game_id": meta.game_id.value,
            "white": {"name": meta.white.name, "email": meta.white.email},
            "black": {"name": meta.black.name, "email": meta.black.email},
            "my_colour": meta.my_colour.value,
            "created_at": meta.created_at.isoformat(),
            "updated_at": meta.updated_at.isoformat(),
            "draw_offer_open": meta.draw_offer_open,
        },
        "pgn": record.pgn,
    }


def _from_document(document: dict) -> GameRecord:
    meta = document["meta"]
    return GameRecord(
        meta=GameMeta(
            game_id=GameId(meta["game_id"]),
            white=Player(meta["white"]["name"], meta["white"]["email"]),
            black=Player(meta["black"]["name"], meta["black"]["email"]),
            my_colour=Colour(meta["my_colour"]),
            created_at=datetime.fromisoformat(meta["created_at"]),
            updated_at=datetime.fromisoformat(meta["updated_at"]),
            draw_offer_open=bool(meta["draw_offer_open"]),
        ),
        pgn=document["pgn"],
    )
