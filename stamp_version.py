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

The same run versions every site page's local stylesheet and script links by
content, as ?v=<hash> of the file each one names. GitHub Pages lets a browser
keep a cached stylesheet for minutes after a deploy; with the hash, any change
to the file is a new address, so a new page never renders against old CSS.

Scope is the site tree only. Root documentation carries no version data by
policy; rewriting it here would quietly reintroduce some.

Files are read and written as bytes so that line endings and encoding survive
untouched: only the text between a pair of markers ever changes. The script is
idempotent, so a second run finds every marker already correct, changes
nothing and says so. It prints every file it touches. It fails only when it
cannot do its job, meaning a missing or empty VERSION file, no site tree at
all or a page linking an asset that does not exist, never merely because there
was nothing to change.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import unquote

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

# A local stylesheet or script link plus any query it already carries. A colon
# in the path means a scheme, so absolute URLs never match; root-absolute and
# protocol-relative paths are left alone by version_assets.
PAGE_SUFFIX = ".html"
ASSET_HASH_LENGTH = 10
ASSET_LINK_PATTERN = re.compile(
    r'\b(?P<attribute>href|src)="(?P<path>[^"?#:]+\.(?:css|js))(?:\?[^"#]*)?"'
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


def asset_hash(path: Path) -> str:
    """Return the short content hash of one asset, reading CRLF as LF.

    A Windows checkout and the LF blob GitHub serves then agree, so a run on
    another machine does not rewrite every page.
    """
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()[:ASSET_HASH_LENGTH]


def version_assets(page: Path) -> int:
    """Set ?v=<hash> on one page's local asset links. Return how many moved."""
    text = page.read_bytes().decode(ENCODING)
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        link = match.group("path")
        if link.startswith("/"):
            return match.group(0)
        asset = page.parent / unquote(link)
        if not asset.is_file():
            sys.exit(f"[stamp] {page} links {link}; {asset} does not exist")
        versioned = f'{match.group("attribute")}="{link}?v={asset_hash(asset)}"'
        if versioned != match.group(0):
            changed += 1
        return versioned

    stamped = ASSET_LINK_PATTERN.sub(replace, text)
    if changed:
        page.write_bytes(stamped.encode(ENCODING))
    return changed


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

    versioned = 0
    for path in site_files():
        if path.suffix.lower() != PAGE_SUFFIX:
            continue
        moved = version_assets(path)
        if moved:
            versioned += 1
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            print(f"[stamp] versioned {relative} ({_links(moved)})")
    if not versioned:
        print("[stamp] asset links already carry their current hashes")
    return EXIT_OK


def _markers(count: int) -> str:
    """Return a count of markers, pluralised."""
    return f"{count} marker" if count == 1 else f"{count} markers"


def _links(count: int) -> str:
    """Return a count of asset links, pluralised."""
    return f"{count} asset link" if count == 1 else f"{count} asset links"


if __name__ == "__main__":
    raise SystemExit(main())
