"""The postalgambit: URI scheme registration and its removal.

The scheme key is part of the injected RegistryKeys value, so every test here
writes a scratch scheme and never touches the one a real installation owns.
British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

from installer.constants import (
    EXE_NAME,
    SHORTCUT_ICON_SUBPATH,
    URL_CLASS_DESCRIPTION,
    URL_DEFAULT_ICON_SUBKEY,
    URL_OPEN_COMMAND_SUBKEY,
    URL_PROTOCOL_VALUE,
)
from installer.state.registry import (
    RegistryKeys,
    read_string,
    subkeys_of,
    write_string,
)
from installer.state.url_scheme import (
    delete_url_scheme,
    register_url_scheme,
    scheme_entries,
)

_DEFAULT_VALUE = ""


def _install_with_icon(tmp_path: Path) -> Path:
    """Return an install directory that carries the multi-size .ico."""
    install_dir = tmp_path / "installed"
    (install_dir / SHORTCUT_ICON_SUBPATH[0]).mkdir(parents=True)
    install_dir.joinpath(*SHORTCUT_ICON_SUBPATH).write_bytes(b"ico")
    return install_dir


def test_the_scheme_points_at_the_installed_executable(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    install_dir = _install_with_icon(tmp_path)

    register_url_scheme(install_dir, scratch_keys)

    root = scratch_keys.url_class_key
    assert read_string(root, _DEFAULT_VALUE) == URL_CLASS_DESCRIPTION
    assert read_string(root, URL_PROTOCOL_VALUE) == _DEFAULT_VALUE
    command = read_string(rf"{root}\{URL_OPEN_COMMAND_SUBKEY}", _DEFAULT_VALUE)
    assert command == f'"{install_dir / EXE_NAME}" "%1"'


def test_the_scheme_uses_the_installed_icon_when_there_is_one(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    install_dir = _install_with_icon(tmp_path)

    register_url_scheme(install_dir, scratch_keys)

    icon = read_string(
        rf"{scratch_keys.url_class_key}\{URL_DEFAULT_ICON_SUBKEY}", _DEFAULT_VALUE
    )
    assert str(install_dir.joinpath(*SHORTCUT_ICON_SUBPATH)) in icon


def test_the_scheme_falls_back_to_the_executable_for_its_icon(
    tmp_path: Path,
) -> None:
    """The executable carries the same icon in its resources."""
    install_dir = tmp_path / "installed"

    entries = scheme_entries(install_dir)
    icons = [value for key, _name, value in entries if key.endswith("DefaultIcon")]

    assert icons == [f'"{install_dir / EXE_NAME}",0']


def test_delete_url_scheme_removes_the_whole_tree(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    """The registration is several levels deep, so a single delete would fail."""
    register_url_scheme(_install_with_icon(tmp_path), scratch_keys)

    delete_url_scheme(scratch_keys)

    assert subkeys_of(scratch_keys.url_class_key) == ()
    assert read_string(scratch_keys.url_class_key, _DEFAULT_VALUE) is None


def test_delete_url_scheme_is_silent_when_nothing_is_registered(
    scratch_keys: RegistryKeys,
) -> None:
    delete_url_scheme(scratch_keys)

    assert read_string(scratch_keys.url_class_key, _DEFAULT_VALUE) is None


def test_registering_twice_leaves_one_clean_registration(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    """An upgrade re-points the scheme rather than accumulating keys."""
    install_dir = _install_with_icon(tmp_path)
    write_string(
        rf"{scratch_keys.url_class_key}\{URL_OPEN_COMMAND_SUBKEY}",
        _DEFAULT_VALUE,
        "stale",
    )

    register_url_scheme(install_dir, scratch_keys)
    register_url_scheme(install_dir, scratch_keys)

    command = read_string(
        rf"{scratch_keys.url_class_key}\{URL_OPEN_COMMAND_SUBKEY}", _DEFAULT_VALUE
    )
    assert command == f'"{install_dir / EXE_NAME}" "%1"'
