#!/usr/bin/env python3
"""Build the Postal Gambit standalone Windows executable with Nuitka.

This produces a self-contained GUI executable so end users do NOT need a
system-wide Python installation. It mirrors the Nuitka invocation style used
by the author's other PySide6 desktop builds and embeds Windows PE version
metadata (product name, versions, file description and copyright).

Usage (from the project root, with the venv active or detected):

    python buildexe.py

Nuitka notes:

- --standalone: produce a self-contained app directory (no system Python).
- --enable-plugin=pyside6: ensures Qt/PySide6 integration.
- --jobs=N: parallel C compilation across logical cores.
- --windows-console-mode=disable: GUI app, no console window.
- The generated icon set ships as an assets/ directory beside the executable
  so the running app's resolver (postalgambit.ui.icons) finds it; VERSION and
  LICENSE ship at the bundle root.

There is no stamp_version step: no static doc in this repo carries a version
string; runtime and build both read the VERSION file directly.

The standalone bundle is written directly into the installer payload
directory (installer/payload/PostalGambit) so buildinstaller.py can package
it without an intermediate copy step.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# --- Project identity (single source of truth for build metadata) -----------
APP_NAME = "PostalGambit"
APP_DISPLAY_NAME = "Postal Gambit"
APP_DESCRIPTION = "Correspondence chess over your own email"
APP_AUTHOR = "Oliver Ernster"
EXE_NAME = "postal-gambit"

# Repository layout, resolved relative to this script so the build works from
# any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_FILE = ASSETS_DIR / "postal-gambit.ico"
VERSION_FILE = PROJECT_ROOT / "VERSION"
LICENSE_FILE = PROJECT_ROOT / "LICENSE"

# The whole generated icon set ships as a directory: the app's icon resolver
# and the installer both look for assets/ beside the executable.
ASSETS_TARGET = "assets"

# The bundle is produced straight into the installer payload so the installer
# build can pick it up without a separate staging copy.
INSTALLER_DIR = PROJECT_ROOT / "installer"
PAYLOAD_DIR = INSTALLER_DIR / "payload"
OUTPUT_DIR = PAYLOAD_DIR
BUNDLE_DIR_NAME = APP_NAME

# Defaults that are structural, not domain values.
DEFAULT_VERSION = "0.0.0-dev"
DEFAULT_JOBS = 1

# Nuitka requires a 4-part numeric version (a.b.c.d) for the PE resource.
PE_VERSION_PARTS = 4
PE_VERSION_PAD_VALUE = "0"

# Console-mode toggles. Set POSTAL_GAMBIT_DEBUG_CONSOLE=1 to build a
# console-visible binary for diagnosing the packaged app; release builds keep
# it disabled.
CONSOLE_MODE_DEBUG = "attach"
CONSOLE_MODE_RELEASE = "disable"
DEBUG_CONSOLE_ENV_VAR = "POSTAL_GAMBIT_DEBUG_CONSOLE"
TRUTHY_VALUES = {"1", "true", "yes", "on"}


def read_version() -> str:
    """Return the project version from the VERSION file, or a safe default."""
    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        version = ""
    return version or DEFAULT_VERSION


def to_pe_version(version: str) -> str:
    """Normalise a semantic version into the 4-part numeric form Nuitka wants.

    Non-numeric suffixes (for example a pre-release tag) are dropped, and the
    tuple is padded or truncated to exactly PE_VERSION_PARTS numeric segments.
    """
    numeric_parts: list[str] = []
    for raw_part in version.split("."):
        digits = "".join(ch for ch in raw_part if ch.isdigit())
        numeric_parts.append(digits if digits else PE_VERSION_PAD_VALUE)
        if len(numeric_parts) == PE_VERSION_PARTS:
            break
    while len(numeric_parts) < PE_VERSION_PARTS:
        numeric_parts.append(PE_VERSION_PAD_VALUE)
    return ".".join(numeric_parts)


def resolve_python() -> str:
    """Return the interpreter to drive Nuitka (prefer the project venv)."""
    venv_python = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def parallel_jobs() -> str:
    """Return the number of parallel compile jobs as a string."""
    return str(os.cpu_count() or DEFAULT_JOBS)


def copyright_text() -> str:
    """Return the copyright string embedded in the PE version resource."""
    return f"Copyright {APP_AUTHOR}"


def build_exe() -> int:
    """Build the standalone executable with Nuitka. Returns a process code."""
    if os.name != "nt":
        print("[buildexe] ERROR: buildexe.py targets Windows.", file=sys.stderr)
        return 1

    if not ENTRY_SCRIPT.exists():
        print(
            f"[buildexe] ERROR: entry point not found at {ENTRY_SCRIPT}.",
            file=sys.stderr,
        )
        return 1

    version = read_version()
    pe_version = to_pe_version(version)
    console_mode = (
        CONSOLE_MODE_DEBUG
        if os.environ.get(DEBUG_CONSOLE_ENV_VAR, "").lower() in TRUTHY_VALUES
        else CONSOLE_MODE_RELEASE
    )
    python_exe = resolve_python()
    jobs = parallel_jobs()

    print(f"[buildexe] Building {APP_DISPLAY_NAME} {version} (PE {pe_version})")
    print(f"[buildexe] Entry script: {ENTRY_SCRIPT}")
    print(f"[buildexe] Python: {python_exe}")
    print(f"[buildexe] Parallel jobs: {jobs}")
    print(f"[buildexe] Windows console mode: {console_mode}")
    print(f"[buildexe] Output directory: {OUTPUT_DIR}")

    # Remove a previous standalone tree so stale files cannot leak into a build.
    standalone_dir = OUTPUT_DIR / f"{ENTRY_SCRIPT.stem}.dist"
    if standalone_dir.exists():
        print(f"[buildexe] Removing previous build: {standalone_dir}")
        shutil.rmtree(standalone_dir, ignore_errors=True)

    final_bundle_dir = OUTPUT_DIR / BUNDLE_DIR_NAME
    if final_bundle_dir.exists():
        print(f"[buildexe] Removing previous bundle: {final_bundle_dir}")
        shutil.rmtree(final_bundle_dir, ignore_errors=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    nuitka_args: list[str] = [
        python_exe,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        f"--jobs={jobs}",
        f"--windows-console-mode={console_mode}",
        f"--output-dir={OUTPUT_DIR}",
        f"--output-filename={EXE_NAME}.exe",
        # Windows PE version metadata.
        f"--company-name={APP_AUTHOR}",
        f"--product-name={APP_DISPLAY_NAME}",
        f"--file-version={pe_version}",
        f"--product-version={pe_version}",
        f"--file-description={APP_DESCRIPTION}",
        f"--copyright={copyright_text()}",
    ]

    if ICON_FILE.exists():
        nuitka_args.append(f"--windows-icon-from-ico={ICON_FILE}")
        print(f"[buildexe] Icon: {ICON_FILE}")
    else:
        print(
            f"[buildexe] WARNING: icon not found at {ICON_FILE}; "
            "building without it. Run generate_icons.py first."
        )

    # Ship the whole generated icon set so the in-app resolver and the
    # installer find the icons beside the executable.
    if ASSETS_DIR.is_dir():
        nuitka_args.append(f"--include-data-dir={ASSETS_DIR}={ASSETS_TARGET}")
        print(f"[buildexe] Bundling assets dir: {ASSETS_DIR} -> {ASSETS_TARGET}")
    else:
        print(
            f"[buildexe] WARNING: assets dir not found at {ASSETS_DIR}; "
            "run generate_icons.py first."
        )

    # Ship the VERSION file so the running app can report its own version.
    if VERSION_FILE.exists():
        nuitka_args.append(f"--include-data-file={VERSION_FILE}=VERSION")
        print(f"[buildexe] Bundling data file: {VERSION_FILE} -> VERSION")

    # Ship the licence so the in-app Help can show it.
    if LICENSE_FILE.exists():
        nuitka_args.append(f"--include-data-file={LICENSE_FILE}=LICENSE")
        print(f"[buildexe] Bundling data file: {LICENSE_FILE} -> LICENSE")

    nuitka_args.append(str(ENTRY_SCRIPT))

    print("[buildexe] Running Nuitka with args:")
    for part in nuitka_args:
        print("  ", part)

    result = subprocess.run(nuitka_args, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(
            f"[buildexe] ERROR: Nuitka build failed (exit {result.returncode}).",
            file=sys.stderr,
        )
        return result.returncode

    # Rename the Nuitka output (main.dist) to the product bundle name so the
    # payload directory is installer/payload/PostalGambit.
    exe_path = standalone_dir / f"{EXE_NAME}.exe"
    if not exe_path.exists():
        print(
            f"[buildexe] ERROR: build finished but {exe_path} was not found.\n"
            "Check the Nuitka output above for details.",
            file=sys.stderr,
        )
        return 1

    print(f"[buildexe] Renaming bundle: {standalone_dir} -> {final_bundle_dir}")
    shutil.move(str(standalone_dir), str(final_bundle_dir))

    final_exe = final_bundle_dir / f"{EXE_NAME}.exe"
    size_mb = final_exe.stat().st_size / (1024 * 1024)
    print(f"[buildexe] [OK] Build complete: {final_exe}")
    print(f"[buildexe] Executable size: {size_mb:.1f} MB")
    print(f"[buildexe] Standalone bundle: {final_bundle_dir}")
    return 0


def main() -> int:
    return build_exe()


if __name__ == "__main__":
    raise SystemExit(main())
