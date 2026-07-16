"""Invariant 10: formatting and lint run as part of the suite."""

from __future__ import annotations

import subprocess
import sys

from tests.structural.scan import REPO_ROOT

_CHECK_TARGETS = (
    "postalgambit",
    "tests",
    "main.py",
    "generate_icons.py",
    "buildexe.py",
    "buildinstaller.py",
    "builddmg.py",
    "installer",
)


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


class TestStyle:
    def test_black_is_clean(self) -> None:
        result = _run("black", "--check", "--quiet", *_CHECK_TARGETS)
        assert result.returncode == 0, result.stderr or result.stdout

    def test_flake8_is_clean(self) -> None:
        result = _run("flake8", *_CHECK_TARGETS)
        assert result.returncode == 0, result.stdout
