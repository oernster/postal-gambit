#!/usr/bin/env python3
"""Carry the version in VERSION into the GitHub Pages site.

Everything else in the repository reads VERSION at runtime or at build time,
so the version is named in exactly one place. The site under docs/ is the one
thing that cannot: it is static files served by GitHub Pages with no build
step and no template engine. So each place the site names a version wraps it
in a delimited marker:

    Version <!--VERSION-->1.2.3<!--/VERSION-->

and this script rewrites whatever sits between the markers with the current
contents of VERSION. Run it after bumping VERSION and before building.

Scope is the site tree only. Root documentation carries no version data by
policy; rewriting it here would quietly reintroduce some.

Files are read and written as bytes so that line endings and encoding survive
untouched: only the text between a pair of markers ever changes. The script is
idempotent, so a second run finds every marker already correct, changes
nothing and says so. It prints every file it touches. It fails only when it
cannot do its job, meaning a missing or empty VERSION file or no site tree at
all, never merely because there was nothing to change.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VERSION_FILE = PROJECT_ROOT / "VERSION"

# The site tree, nothing above it.
SITE_DIR = PROJECT_ROOT / "docs"
SITE_SUFFIXES = (".html", ".htm", ".css", ".js", ".json", ".md", ".txt", ".xml")

ENCODING = "utf-8"
OPEN_MARKER = "<!--VERSION-->"
CLOSE_MARKER = "<!--/VERSION-->"
MARKER_PATTERN = re.compile(
    re.escape(OPEN_MARKER) + r"(.*?)" + re.escape(CLOSE_MARKER),
    re.DOTALL,
)

EXIT_OK = 0


def read_version() -> str:
    """Return the version in VERSION; fail if it cannot be read."""
    try:
        version = VERSION_FILE.read_bytes().decode(ENCODING).strip()
    except OSError as error:
        sys.exit(f"[stamp] cannot read {VERSION_FILE}: {error}")
    if not version:
        sys.exit(f"[stamp] {VERSION_FILE} is empty")
    return version


def site_files() -> list[Path]:
    """Return every text file in the site tree, in a stable order."""
    return sorted(
        path
        for path in SITE_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in SITE_SUFFIXES
    )


def stamp(text: str, version: str) -> tuple[str, int]:
    """Return the text with every marker set to version, plus how many moved."""
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        if match.group(1) != version:
            changed += 1
        return f"{OPEN_MARKER}{version}{CLOSE_MARKER}"

    return MARKER_PATTERN.sub(replace, text), changed


def stamp_file(path: Path, version: str) -> tuple[int, int]:
    """Stamp one file. Return how many markers it holds and how many moved."""
    text = path.read_bytes().decode(ENCODING)
    found = len(MARKER_PATTERN.findall(text))
    if not found:
        return 0, 0
    stamped, changed = stamp(text, version)
    if changed:
        path.write_bytes(stamped.encode(ENCODING))
    return found, changed


def main() -> int:
    version = read_version()
    if not SITE_DIR.is_dir():
        sys.exit(f"[stamp] no site tree at {SITE_DIR}")

    print(f"[stamp] version {version} from {VERSION_FILE.name}")
    marked = 0
    touched = 0
    for path in site_files():
        found, changed = stamp_file(path, version)
        marked += found
        if changed:
            touched += 1
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            print(f"[stamp] updated {relative} ({changed} of {_markers(found)})")

    if not marked:
        print(f"[stamp] no {OPEN_MARKER} markers found under {SITE_DIR.name}/")
    elif not touched:
        print(f"[stamp] {_markers(marked)} already at {version}; nothing to do")
    return EXIT_OK


def _markers(count: int) -> str:
    """Return a count of markers, pluralised."""
    return f"{count} marker" if count == 1 else f"{count} markers"


if __name__ == "__main__":
    raise SystemExit(main())
