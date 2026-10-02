"""Helpers shared by the delivery scripts: buildexe, buildinstaller, builddmg."""

from __future__ import annotations

import itertools
from importlib import metadata

# The Nuitka the packaged build is written against: the release Stellody moved
# to on 2026-09-13. An older one left in the environment stops the build here,
# rather than a release nobody chose compiling what ships.
NUITKA_MINIMUM = (4, 2, 1)


def require_nuitka() -> None:
    """Stop where Nuitka is missing or older than the build is written against."""
    try:
        installed = metadata.version("nuitka")
    except metadata.PackageNotFoundError:
        installed = None
    if installed is not None and _release(installed) >= NUITKA_MINIMUM:
        return
    wanted = ".".join(str(number) for number in NUITKA_MINIMUM)
    found = (
        f"Nuitka {installed} is installed" if installed else "Nuitka is not installed"
    )
    raise SystemExit(
        f"{found}; this build needs {wanted} or later:\n"
        "    python -m pip install -r requirements-dev.txt"
    )


def _release(version: str) -> tuple[int, ...]:
    """The numeric release of a version string, '4.2.1rc1' reading as 4.2.1."""
    return tuple(
        int("".join(itertools.takewhile(str.isdigit, part)) or 0)
        for part in version.split(".")
    )
