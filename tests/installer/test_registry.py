"""The HKCU registrations, exercised against scratch keys.

Every write here goes to a unique test key that the fixture removes afterwards,
so the suite never reads or alters a real Postal Gambit installation. British
spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

from installer.constants import APP_AUMID, EXE_NAME, UNINSTALL_FLAG, URL_SCHEME
from installer.state.registry import (
    DEFAULT_KEYS,
    DISPLAY_ICON,
    DISPLAY_VERSION,
    ESTIMATED_SIZE,
    INSTALL_LOCATION,
    UNINSTALL_STRING,
    RegistryKeys,
    delete_key,
    delete_toast_identity,
    delete_tree,
    delete_uninstall_entry,
    installed_location,
    installed_version,
    is_autostart_enabled,
    read_string,
    set_autostart,
    subkeys_of,
    write_string,
    write_uninstall_entry,
)

# Longer than the 255 characters a registry key name allows, so creating it
# fails and the guard around the write is exercised.
_OVERLONG_KEY = "PostalGambitTests" + ("x" * 300)
_ABSENT_KEY = r"Software\PostalGambitTests\NotThere"
_VERSION = "0.2.0"
_ESTIMATED_KB = 2048
_DISPLAY_NAME = "DisplayName"


def _read_dword(key: str, name: str) -> int:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
        return int(winreg.QueryValueEx(handle, name)[0])


def test_read_string_returns_none_for_an_absent_key() -> None:
    assert read_string(_ABSENT_KEY, _DISPLAY_NAME) is None


def test_write_string_creates_the_key_it_writes_into(
    scratch_keys: RegistryKeys,
) -> None:
    key = rf"{scratch_keys.uninstall_key}\Nested"

    write_string(key, _DISPLAY_NAME, "Postal Gambit")

    assert read_string(key, _DISPLAY_NAME) == "Postal Gambit"


def test_subkeys_of_lists_the_immediate_children(scratch_keys: RegistryKeys) -> None:
    root = scratch_keys.uninstall_key
    write_string(rf"{root}\one", _DISPLAY_NAME, "a")
    write_string(rf"{root}\two", _DISPLAY_NAME, "b")

    assert sorted(subkeys_of(root)) == ["one", "two"]


def test_subkeys_of_is_empty_for_an_absent_key() -> None:
    assert subkeys_of(_ABSENT_KEY) == ()


def test_delete_tree_removes_a_key_and_everything_under_it(
    scratch_keys: RegistryKeys,
) -> None:
    """Windows refuses to delete a key that still has children."""
    root = scratch_keys.uninstall_key
    write_string(rf"{root}\shell\open\command", "", "cmd")

    delete_tree(root)

    assert subkeys_of(root) == ()
    assert read_string(root, _DISPLAY_NAME) is None


def test_write_uninstall_entry_records_the_installation(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    uninstaller = tmp_path / "_uninstall" / "Setup.exe"
    icon = tmp_path / "app.ico"

    write_uninstall_entry(
        tmp_path,
        uninstaller,
        _VERSION,
        display_icon=icon,
        estimated_kb=_ESTIMATED_KB,
        keys=scratch_keys,
    )

    key = scratch_keys.uninstall_key
    assert read_string(key, DISPLAY_VERSION) == _VERSION
    assert read_string(key, INSTALL_LOCATION) == str(tmp_path)
    assert read_string(key, UNINSTALL_STRING) == f'"{uninstaller}" {UNINSTALL_FLAG}'
    assert read_string(key, DISPLAY_ICON) == str(icon)
    assert _read_dword(key, ESTIMATED_SIZE) == _ESTIMATED_KB


def test_write_uninstall_entry_without_an_icon_or_a_size(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    write_uninstall_entry(tmp_path, tmp_path / "Setup.exe", _VERSION, keys=scratch_keys)

    assert read_string(scratch_keys.uninstall_key, DISPLAY_ICON) == str(tmp_path)
    assert read_string(scratch_keys.uninstall_key, ESTIMATED_SIZE) is None


def test_installed_version_and_location_round_trip(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    write_uninstall_entry(tmp_path, tmp_path / "Setup.exe", _VERSION, keys=scratch_keys)

    assert installed_version(scratch_keys) == _VERSION
    assert installed_location(scratch_keys) == tmp_path


def test_installed_location_is_none_when_nothing_is_recorded(
    scratch_keys: RegistryKeys,
) -> None:
    assert installed_version(scratch_keys) is None
    assert installed_location(scratch_keys) is None


def test_installed_location_rejects_a_relative_recorded_path(
    scratch_keys: RegistryKeys,
) -> None:
    """A relative value would become the current directory, which is dangerous."""
    write_uninstall_entry(
        Path("relative"), Path("Setup.exe"), _VERSION, keys=scratch_keys
    )

    assert installed_location(scratch_keys) is None


def test_delete_uninstall_entry_removes_the_registration(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    write_uninstall_entry(tmp_path, tmp_path / "Setup.exe", _VERSION, keys=scratch_keys)

    delete_uninstall_entry(scratch_keys)

    assert installed_version(scratch_keys) is None


def test_delete_key_is_silent_when_the_key_is_already_gone() -> None:
    delete_key(_ABSENT_KEY)


def test_delete_toast_identity_removes_the_notification_key(
    scratch_keys: RegistryKeys,
) -> None:
    write_string(scratch_keys.toast_key, _DISPLAY_NAME, "Postal Gambit")

    delete_toast_identity(scratch_keys)

    assert read_string(scratch_keys.toast_key, _DISPLAY_NAME) is None


def test_autostart_can_be_enabled_then_disabled(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    exe = tmp_path / EXE_NAME

    set_autostart(True, exe, scratch_keys)
    assert is_autostart_enabled(scratch_keys) is True
    assert read_string(scratch_keys.run_subkey, scratch_keys.run_value) == f'"{exe}"'

    set_autostart(False, exe, scratch_keys)
    assert is_autostart_enabled(scratch_keys) is False


def test_disabling_autostart_that_was_never_set_is_silent(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    set_autostart(False, tmp_path / EXE_NAME, scratch_keys)

    assert is_autostart_enabled(scratch_keys) is False


def test_autostart_is_silent_when_the_key_cannot_be_created(tmp_path: Path) -> None:
    keys = RegistryKeys(run_subkey=_OVERLONG_KEY)

    set_autostart(True, tmp_path / EXE_NAME, keys)

    assert is_autostart_enabled(keys) is False


def test_the_default_keys_name_the_real_registrations() -> None:
    """The shipped defaults are the real per-user locations, not a test set."""
    assert DEFAULT_KEYS.uninstall_key.endswith(r"Uninstall\PostalGambit")
    assert DEFAULT_KEYS.run_value == "PostalGambit"
    assert DEFAULT_KEYS.toast_key.endswith(rf"AppUserModelId\{APP_AUMID}")
    assert DEFAULT_KEYS.url_class_key.endswith(rf"Classes\{URL_SCHEME}")
