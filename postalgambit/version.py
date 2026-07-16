"""Application identity, read from the repo-root VERSION file."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "Postal Gambit"
APP_TAGLINE = "Correspondence chess over your own email"
APP_AUTHOR = "Oliver Ernster"
_FALLBACK_VERSION = "0.0.0-dev"


def _read_version() -> str:
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    try:
        text = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return _FALLBACK_VERSION
    return text or _FALLBACK_VERSION


__version__ = _read_version()
