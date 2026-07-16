"""SettingsStore adapter: identity and preferences in one JSON document.

Every write is read-modify-write, so saving one setting never discards
another. An unreadable or unknown-version file raises StorageError on both
reads and writes; nothing is silently overwritten.
"""

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
        document = self._read_document()
        return Identity(
            name=str(document.get("name", "")),
            email=str(document.get("email", "")),
        )

    def save(self, identity: Identity) -> None:
        document = self._read_document()
        document["name"] = identity.name
        document["email"] = identity.email
        self._write_document(document)

    def load_theme(self) -> str:
        """The persisted theme name, or an empty string when unset."""
        return str(self._read_document().get("theme", ""))

    def save_theme(self, theme: str) -> None:
        document = self._read_document()
        document["theme"] = theme
        self._write_document(document)

    def _read_document(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise StorageError(f"unreadable settings file: {error}") from error
        if document.get("version") != SETTINGS_VERSION:
            raise StorageError(f"unknown settings version: {document.get('version')!r}")
        return document

    def _write_document(self, document: dict) -> None:
        document["version"] = SETTINGS_VERSION
        payload = json.dumps(document, indent=2)
        tmp_path = self._path.with_suffix(self._path.suffix + _TMP_SUFFIX)
        tmp_path.write_text(payload, encoding="utf-8")
        os.replace(tmp_path, self._path)
