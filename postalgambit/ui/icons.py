"""Locate the bundled assets directory across dev and frozen builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ASSETS_DIR_NAME = "assets"
ICO_NAME = "postal-gambit.ico"
BADGE_PNG_NAME = "postal-gambit_icon_256.png"
ASSETS_ENV_OVERRIDE = "POSTAL_GAMBIT_ASSETS_DIR"


def _candidate_dirs() -> tuple[Path, ...]:
    candidates = []
    override = os.environ.get(ASSETS_ENV_OVERRIDE)
    if override:
        candidates.append(Path(override))
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.argv[0]).resolve().parent / ASSETS_DIR_NAME)
    here = Path(__file__).resolve()
    candidates.append(here.parents[2] / ASSETS_DIR_NAME)
    candidates.append(Path(sys.argv[0]).resolve().parent / ASSETS_DIR_NAME)
    return tuple(candidates)


def find_assets_dir() -> Path | None:
    for candidate in _candidate_dirs():
        if candidate.is_dir():
            return candidate
    return None


def get_app_icon_path() -> Path | None:
    assets = find_assets_dir()
    if assets is None:
        return None
    ico = assets / ICO_NAME
    if ico.is_file():
        return ico
    badge = assets / BADGE_PNG_NAME
    return badge if badge.is_file() else None


def get_badge_png_path() -> Path | None:
    assets = find_assets_dir()
    if assets is None:
        return None
    badge = assets / BADGE_PNG_NAME
    return badge if badge.is_file() else None
