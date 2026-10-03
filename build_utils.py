"""Helpers shared by the delivery scripts: buildexe, buildinstaller, builddmg."""

from __future__ import annotations

import itertools
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# The Nuitka floor has one home: the nuitka line of the development
# requirements. The build reads it from there, so the pin and the check cannot
# drift apart.
REQUIREMENTS_DEV = PROJECT_ROOT / "requirements-dev.txt"
_NUITKA_FLOOR_LINE = re.compile(
    r"^\s*nuitka\s*>=\s*([0-9][0-9A-Za-z.]*)", re.IGNORECASE
)

# Run inside the interpreter that will compile, so the version checked is the
# version that builds. It prints nothing when that interpreter has no Nuitka.
_VERSION_PROBE = (
    "from importlib import metadata\n"
    "try:\n"
    "    print(metadata.version('nuitka'))\n"
    "except metadata.PackageNotFoundError:\n"
    "    pass\n"
)


def nuitka_floor(requirements: Path = REQUIREMENTS_DEV) -> tuple[int, ...]:
    """The minimum Nuitka release, read from the nuitka>= line of requirements."""
    for line in requirements.read_text(encoding="utf-8").splitlines():
        match = _NUITKA_FLOOR_LINE.match(line)
        if match:
            return _release(match.group(1))
    raise SystemExit(
        f"{requirements} has no 'nuitka>=' line; the build reads its Nuitka "
        "floor from there."
    )


def installed_nuitka(python: str) -> str | None:
    """The Nuitka version the given interpreter would compile with, if any."""
    result = subprocess.run(
        [python, "-c", _VERSION_PROBE],
        capture_output=True,
        text=True,
        check=False,
    )
    version = result.stdout.strip()
    return version if result.returncode == 0 and version else None


def require_nuitka(python: str = sys.executable) -> None:
    """Stop where the compiling interpreter's Nuitka is missing or too old."""
    installed = installed_nuitka(python)
    if installed is not None and _release(installed) >= NUITKA_MINIMUM:
        return
    wanted = ".".join(str(number) for number in NUITKA_MINIMUM)
    found = (
        f"Nuitka {installed} is installed" if installed else "Nuitka is not installed"
    )
    raise SystemExit(
        f"{found}; this build needs {wanted} or later:\n"
        f"    {python} -m pip install -r requirements-dev.txt"
    )


def _release(version: str) -> tuple[int, ...]:
    """The numeric release of a version string, '4.2.1rc1' reading as 4.2.1."""
    return tuple(
        int("".join(itertools.takewhile(str.isdigit, part)) or 0)
        for part in version.split(".")
    )


# Read at import, so a requirements file that has lost the line stops every
# build script before it does any work.
NUITKA_MINIMUM = nuitka_floor()
