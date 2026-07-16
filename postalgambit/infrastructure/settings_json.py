"""SettingsStore adapter: the user's identity in a single JSON document."""

from __future__ import annotations

import json
import os
from pathlib import Path

from postalgambit.domain.errors import StorageError
from postalgambit.domain.identity import Identity

SETTINGS_VERSION = 1
SETTINGS_FILE_NAME = "settings.json"
_TMP_SUFFIX = ".tmp"


class JsonSettingsStore:
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self._path = data_dir / SETTINGS_FILE_NAME

    def load(self) -> Identity:
        if not self._path.exists():
            return Identity()
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise StorageError(f"unreadable settings file: {error}") from error
        if document.get("version") != SETTINGS_VERSION:
            raise StorageError(f"unknown settings version: {document.get('version')!r}")
        return Identity(
            name=str(document.get("name", "")),
            email=str(document.get("email", "")),
        )

    def save(self, identity: Identity) -> None:
        payload = json.dumps(
            {
                "version": SETTINGS_VERSION,
                "name": identity.name,
                "email": identity.email,
            },
            indent=2,
        )
        tmp_path = self._path.with_suffix(self._path.suffix + _TMP_SUFFIX)
        tmp_path.write_text(payload, encoding="utf-8")
        os.replace(tmp_path, self._path)
