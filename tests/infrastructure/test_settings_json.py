"""Integration tests for the JSON settings store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from postalgambit.domain.errors import StorageError
from postalgambit.domain.identity import Identity
from postalgambit.infrastructure.settings_json import (
    SETTINGS_FILE_NAME,
    JsonSettingsStore,
)


class TestSettings:
    def test_missing_file_yields_default_identity(self, tmp_path: Path) -> None:
        assert JsonSettingsStore(tmp_path).load() == Identity()

    def test_round_trip(self, tmp_path: Path) -> None:
        store = JsonSettingsStore(tmp_path)
        identity = Identity(name="Oliver", email="o@example.org")
        store.save(identity)
        assert JsonSettingsStore(tmp_path).load() == identity

    def test_corrupt_file_raises(self, tmp_path: Path) -> None:
        (tmp_path / SETTINGS_FILE_NAME).write_text("{oops", "utf-8")
        with pytest.raises(StorageError):
            JsonSettingsStore(tmp_path).load()

    def test_unknown_version_raises(self, tmp_path: Path) -> None:
        (tmp_path / SETTINGS_FILE_NAME).write_text(json.dumps({"version": 99}), "utf-8")
        with pytest.raises(StorageError):
            JsonSettingsStore(tmp_path).load()


class TestTheme:
    def test_missing_file_yields_empty_theme(self, tmp_path: Path) -> None:
        assert JsonSettingsStore(tmp_path).load_theme() == ""

    def test_theme_round_trip(self, tmp_path: Path) -> None:
        JsonSettingsStore(tmp_path).save_theme("light")
        assert JsonSettingsStore(tmp_path).load_theme() == "light"

    def test_theme_save_preserves_identity(self, tmp_path: Path) -> None:
        store = JsonSettingsStore(tmp_path)
        identity = Identity(name="Oliver", email="o@example.org")
        store.save(identity)
        store.save_theme("light")
        assert store.load() == identity
        assert store.load_theme() == "light"

    def test_identity_save_preserves_theme(self, tmp_path: Path) -> None:
        store = JsonSettingsStore(tmp_path)
        store.save_theme("dark")
        store.save(Identity(name="Oliver", email="o@example.org"))
        assert store.load_theme() == "dark"

    def test_corrupt_file_raises_on_theme_read_and_write(self, tmp_path: Path) -> None:
        (tmp_path / SETTINGS_FILE_NAME).write_text("{oops", "utf-8")
        store = JsonSettingsStore(tmp_path)
        with pytest.raises(StorageError):
            store.load_theme()
        with pytest.raises(StorageError):
            store.save_theme("light")
