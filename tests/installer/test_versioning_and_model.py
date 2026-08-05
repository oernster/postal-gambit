"""Version comparison and the installed-state model.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

from installer.constants import EXE_NAME, FALLBACK_VERSION
from installer.state.model import InstallState, classify, detect
from installer.state.registry import (
    RegistryKeys,
    set_autostart,
    write_uninstall_entry,
)
from installer.state.versioning import (
    NEWER,
    OLDER,
    SAME,
    compare_versions,
    version_tuple,
)

_INSTALLED = "0.2.0"
_NEWER = "0.3.0"
_OLDER = "0.1.0"


def test_version_tuple_reads_the_numeric_parts() -> None:
    assert version_tuple(_INSTALLED) == (0, 2, 0)


def test_version_tuple_treats_a_part_with_no_digits_as_zero() -> None:
    assert version_tuple("0.2.0-rc") == (0, 2, 0)


def test_version_tuple_of_an_empty_string_is_zero() -> None:
    assert version_tuple("") == (0,)


def test_compare_versions_orders_older_same_and_newer() -> None:
    assert compare_versions(_OLDER, _INSTALLED) == OLDER
    assert compare_versions(_INSTALLED, _INSTALLED) == SAME
    assert compare_versions(_NEWER, _INSTALLED) == NEWER


def test_classify_reports_not_installed_when_nothing_is_recorded() -> None:
    assert classify(_INSTALLED, None) == InstallState.NOT_INSTALLED


def test_classify_reports_upgrade_reinstall_and_downgrade() -> None:
    assert classify(_NEWER, _INSTALLED) == InstallState.UPGRADE
    assert classify(_INSTALLED, _INSTALLED) == InstallState.REINSTALL
    assert classify(_OLDER, _INSTALLED) == InstallState.DOWNGRADE


def test_detect_reports_not_installed_with_no_registration(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    snapshot = detect(_INSTALLED, tmp_path, keys=scratch_keys)

    assert snapshot.state == InstallState.NOT_INSTALLED
    assert snapshot.installed is False
    assert snapshot.install_dir == tmp_path
    assert snapshot.installed_version == ""
    assert snapshot.autostart is False


def test_detect_reads_the_recorded_installation(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    """The sign-in flag is read back, so the checkbox reflects the machine."""
    install_dir = tmp_path / "installed"
    install_dir.mkdir()
    write_uninstall_entry(
        install_dir, install_dir / "setup.exe", _INSTALLED, keys=scratch_keys
    )
    set_autostart(True, install_dir / EXE_NAME, scratch_keys)

    snapshot = detect(_NEWER, tmp_path, keys=scratch_keys)

    assert snapshot.state == InstallState.UPGRADE
    assert snapshot.installed is True
    assert snapshot.installed_version == _INSTALLED
    assert snapshot.install_dir == install_dir
    assert snapshot.autostart is True


def test_detect_treats_a_registration_whose_directory_has_gone_as_absent(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    """A stale entry must not offer Repair against a directory that is not there."""
    missing = tmp_path / "gone"
    write_uninstall_entry(missing, missing / "setup.exe", _INSTALLED, keys=scratch_keys)

    snapshot = detect(_NEWER, tmp_path, keys=scratch_keys)

    assert snapshot.state == InstallState.NOT_INSTALLED
    assert snapshot.install_dir == tmp_path


def test_detect_falls_back_when_the_bundle_carries_no_version(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    snapshot = detect("", tmp_path, keys=scratch_keys)

    assert snapshot.bundled_version == FALLBACK_VERSION
