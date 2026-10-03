"""The Nuitka gate the build scripts share: whose Nuitka it reads, which floor.

The check must ask the interpreter that compiles. buildexe and buildinstaller
compile with the project venv whenever it exists, whatever interpreter runs
them. A check that read its own environment could pass over a Nuitka that
never builds; it could equally refuse one that does.
"""

from __future__ import annotations

import sys
import venv
from importlib import metadata
from pathlib import Path

import pytest

import build_utils

# Where a venv keeps its interpreter on each platform.
_VENV_PYTHON = (
    Path("Scripts", "python.exe") if sys.platform == "win32" else Path("bin", "python")
)


def _own_nuitka() -> str | None:
    try:
        return metadata.version("nuitka")
    except metadata.PackageNotFoundError:
        return None


@pytest.fixture(scope="module")
def bare_python(tmp_path_factory: pytest.TempPathFactory) -> str:
    """An interpreter with no Nuitka: a fresh venv built without pip."""
    root = tmp_path_factory.mktemp("bare-venv")
    venv.EnvBuilder(with_pip=False).create(root)
    return str(root / _VENV_PYTHON)


class TestCompilingInterpreter:
    def test_reads_the_named_interpreter_not_its_own(self, bare_python: str) -> None:
        assert build_utils.installed_nuitka(bare_python) is None
        assert build_utils.installed_nuitka(sys.executable) == _own_nuitka()

    def test_refuses_when_the_compiling_interpreter_has_none(
        self, bare_python: str
    ) -> None:
        with pytest.raises(SystemExit) as refusal:
            build_utils.require_nuitka(bare_python)
        message = str(refusal.value)
        wanted = ".".join(str(n) for n in build_utils.NUITKA_MINIMUM)
        assert message.startswith(
            f"Nuitka is not installed; this build needs {wanted} or later:"
        )
        assert f"{bare_python} -m pip install -r requirements-dev.txt" in message

    def test_the_windows_scripts_check_the_interpreter_they_compile_with(
        self,
    ) -> None:
        for script in ("buildexe.py", "buildinstaller.py"):
            source = (build_utils.PROJECT_ROOT / script).read_text(encoding="utf-8")
            assert "require_nuitka(resolve_python())" in source, script
            assert "require_nuitka()" not in source, script


class TestFloor:
    def test_the_floor_is_the_requirements_pin(self) -> None:
        pins = build_utils.REQUIREMENTS_DEV.read_text(encoding="utf-8")
        wanted = ".".join(str(n) for n in build_utils.NUITKA_MINIMUM)
        assert f"nuitka>={wanted}" in pins.splitlines()

    def test_reads_whatever_the_pin_says(self, tmp_path: Path) -> None:
        requirements = tmp_path / "requirements-dev.txt"
        requirements.write_text("pytest>=8\nNuitka >= 5.0.3rc2\n", encoding="utf-8")
        assert build_utils.nuitka_floor(requirements) == (5, 0, 3)

    def test_a_missing_pin_stops_with_a_reason(self, tmp_path: Path) -> None:
        requirements = tmp_path / "requirements-dev.txt"
        requirements.write_text("pytest>=8\n# nuitka>=4.2.1\n", encoding="utf-8")
        with pytest.raises(SystemExit, match="has no 'nuitka>=' line"):
            build_utils.nuitka_floor(requirements)


class TestRelease:
    def test_release_reads_the_numeric_parts(self) -> None:
        assert build_utils._release("4.2.1rc1") == (4, 2, 1)
        assert build_utils._release("4.10") > build_utils._release("4.9.9")
