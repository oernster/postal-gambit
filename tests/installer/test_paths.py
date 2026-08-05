"""The per-user locations the installer reads and writes.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

from installer.constants import (
    APP_DISPLAY_NAME,
    APP_NAME,
    ENV_APPDATA,
    ENV_LOCALAPPDATA,
    EXE_NAME,
    NUITKA_ONEFILE_ENV,
    STATE_DIR_NAME,
    UNINSTALLER_NAME,
)
from installer.ops.paths import (
    desktop_link,
    directory_size_kb,
    install_target,
    installed_exe,
    launcher_candidates,
    original_installer_exe,
    running_from_inside,
    start_menu_link,
    state_dir,
    uninstaller_path,
)

_KIB = 1024
_LAUNCHER = "PostalGambitSetup.exe"


def test_install_target_sits_under_local_appdata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(ENV_LOCALAPPDATA, str(tmp_path))

    assert install_target() == tmp_path / "Programs" / APP_NAME


def test_install_target_falls_back_when_local_appdata_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ENV_LOCALAPPDATA, raising=False)

    assert install_target() == Path.home() / "AppData" / "Local" / "Programs" / APP_NAME


def test_state_dir_is_a_dotted_directory_under_the_home_directory(
    isolated_profile: Path,
) -> None:
    """The app keeps its games under ~, not under LOCALAPPDATA."""
    assert state_dir() == isolated_profile / STATE_DIR_NAME


def test_installed_exe_and_uninstaller_path(tmp_path: Path) -> None:
    assert installed_exe(tmp_path) == tmp_path / EXE_NAME
    assert uninstaller_path(tmp_path) == tmp_path / "_uninstall" / UNINSTALLER_NAME


def test_desktop_link_is_named_for_the_display_name(isolated_profile: Path) -> None:
    assert desktop_link() == isolated_profile / "Desktop" / f"{APP_DISPLAY_NAME}.lnk"


def test_start_menu_link_sits_under_roaming_appdata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(ENV_APPDATA, str(tmp_path))

    link = start_menu_link()

    assert link is not None
    assert link.parent == tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def test_start_menu_link_is_none_without_appdata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ENV_APPDATA, raising=False)

    assert start_menu_link() is None


def test_launcher_candidates_prefer_the_onefile_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(NUITKA_ONEFILE_ENV, r"C:\Setup.exe")

    assert launcher_candidates()[0] == r"C:\Setup.exe"


def test_launcher_candidates_tolerate_an_empty_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A process started with no argv still has to answer this question."""
    monkeypatch.delenv(NUITKA_ONEFILE_ENV, raising=False)
    monkeypatch.setattr(sys, "argv", [])

    assert launcher_candidates() == ("", "")


def _elsewhere(tmp_path: Path) -> Path:
    """Return a temporary root that holds none of the candidates under test."""
    other = tmp_path / "other-temp"
    other.mkdir()
    return other


def test_original_installer_exe_returns_the_first_real_executable(
    tmp_path: Path,
) -> None:
    launcher = tmp_path / _LAUNCHER
    launcher.write_bytes(b"stub")

    found = original_installer_exe(("", str(launcher)), _elsewhere(tmp_path))

    assert found == launcher


def test_original_installer_exe_skips_a_candidate_that_is_not_an_executable(
    tmp_path: Path,
) -> None:
    script = tmp_path / "run.py"
    script.write_text("stub", encoding="utf-8")

    found = original_installer_exe((str(script),), _elsewhere(tmp_path))

    assert found == Path(sys.executable)


def test_original_installer_exe_skips_the_onefile_bootstrap(tmp_path: Path) -> None:
    """A path under the temporary directory disappears when the process exits."""
    bootstrap = tmp_path / "bootstrap.exe"
    bootstrap.write_bytes(b"stub")

    found = original_installer_exe((str(bootstrap),), tmp_path)

    assert found == Path(sys.executable)


def test_original_installer_exe_skips_the_temporary_root_itself(
    tmp_path: Path,
) -> None:
    """The bootstrap path can be the root itself, not only a child of it."""
    root = tmp_path / "boot.exe"
    root.write_bytes(b"stub")

    assert original_installer_exe((str(root),), root) == Path(sys.executable)


def test_original_installer_exe_falls_back_to_the_interpreter() -> None:
    assert original_installer_exe(()) == Path(sys.executable)


def test_original_installer_exe_defaults_to_the_system_temporary_directory(
    tmp_path: Path,
) -> None:
    """With no override the real temporary root is what a bootstrap is judged by."""
    inside = Path(tempfile.gettempdir()).resolve() / "postal-gambit-probe.exe"
    inside.write_bytes(b"stub")
    try:
        assert original_installer_exe((str(inside),)) == Path(sys.executable)
    finally:
        inside.unlink(missing_ok=True)


def test_original_installer_exe_reads_the_environment_when_given_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    launcher = tmp_path / _LAUNCHER
    launcher.write_bytes(b"stub")
    monkeypatch.setenv(NUITKA_ONEFILE_ENV, str(launcher))

    assert original_installer_exe(None, _elsewhere(tmp_path)) == launcher


def test_running_from_inside_is_true_for_the_directory_holding_this_process() -> None:
    assert running_from_inside(Path(sys.executable).parent) is True


def test_running_from_inside_is_true_for_the_running_executable_itself() -> None:
    assert running_from_inside(Path(sys.executable)) is True


def test_running_from_inside_is_false_for_an_unrelated_directory(
    tmp_path: Path,
) -> None:
    assert running_from_inside(tmp_path) is False


def test_directory_size_kb_totals_the_files(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"x" * (2 * _KIB))
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.bin").write_bytes(b"x" * (3 * _KIB))

    assert directory_size_kb(tmp_path) == 5


def test_directory_size_kb_reports_nothing_for_a_path_that_is_not_a_directory(
    tmp_path: Path,
) -> None:
    a_file = tmp_path / "a.bin"
    a_file.write_bytes(b"x")

    assert directory_size_kb(a_file) == 0
