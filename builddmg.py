#!/usr/bin/env python3
"""Build the Postal Gambit macOS .app bundle and DMG.

macOS-only; run from the repo root with the venv active:

    python builddmg.py

Flow: build the .app with Nuitka (--macos-create-app-bundle), strip the
stray Mach-O object files PySide6 ships (Gatekeeper rejects a bundle that
contains unsigned code and codesign --deep silently skips them), codesign
the bundle, wrap it in a DMG with create-dmg, then sign, notarize and
staple the DMG. Notarization runs only when APPLE_ID and APPLE_APP_PASSWORD
are set; without them the output is a signed, locally installable DMG.

The .icns ships pre-generated in assets/ (generate_icons.py emits it from
the master PNG), so no image conversion happens here.
"""

from __future__ import annotations

import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --- Project identity --------------------------------------------------------
APP_DISPLAY_NAME = "Postal Gambit"
LINK_SCHEME = "postalgambit"
APP_BUNDLE_NAME = "Postal Gambit.app"
APP_AUTHOR = "Oliver Ernster"
BUNDLE_ID = "uk.codecrafter.PostalGambit"
DMG_BASENAME = "postal-gambit"

PROJECT_ROOT = Path(__file__).resolve().parent
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"
ASSETS_DIR = PROJECT_ROOT / "assets"
ICNS_FILE = ASSETS_DIR / "postal-gambit.icns"
VERSION_FILE = PROJECT_ROOT / "VERSION"
LICENSE_FILE = PROJECT_ROOT / "LICENSE"
DIST_DIR = PROJECT_ROOT / "dist-macos"

# Signing and notarization, all overridable from the environment.
DEVELOPER_ID = os.environ.get(
    "DEVELOPER_ID_APPLICATION",
    "Developer ID Application: Oliver Ernster (W7K465GKFJ)",
)
APPLE_ID = os.environ.get("APPLE_ID", "")
APPLE_APP_PASSWORD = os.environ.get("APPLE_APP_PASSWORD", "")
APPLE_TEAM_ID = os.environ.get("APPLE_TEAM_ID", "W7K465GKFJ")

# The minimal hardened-runtime entitlement for a PySide6 app: allow loading
# the bundled Qt libraries signed under our own identity.
ENTITLEMENTS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
"""

DEFAULT_VERSION = "0.0.0-dev"
DEFAULT_JOBS = 1
# create-dmg exits 2 when it succeeds but cannot set a window background
# (for example on a headless build), so both codes count as success.
CREATE_DMG_OK_CODES = (0, 2)
DMG_WINDOW_WIDTH = 600
DMG_WINDOW_HEIGHT = 420
DMG_ICON_SIZE = 128
DMG_APP_X = 140
DMG_APP_Y = 190
DMG_DROP_X = 460
DMG_DROP_Y = 190


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, echoing it first."""
    print("  $", " ".join(str(a) for a in args))
    return subprocess.run([str(a) for a in args], **kwargs)


def section(title: str) -> None:
    print(f"\n== {title} ==")


def require(tool: str, brew_package: str | None = None) -> None:
    """Ensure a command-line tool exists, installing via Homebrew if needed."""
    if shutil.which(tool):
        return
    package = brew_package or tool
    section(f"Installing {package} via Homebrew")
    run(["brew", "install", package], check=True)
    if not shutil.which(tool):
        raise SystemExit(f"[builddmg] {tool} still missing after brew install.")


def read_version() -> str:
    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        version = ""
    return version or DEFAULT_VERSION


def build_app_bundle(version: str) -> Path:
    """Compile the .app with Nuitka and return its path."""
    section("Building the .app with Nuitka")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    DIST_DIR.mkdir(parents=True)
    jobs = str(os.cpu_count() or DEFAULT_JOBS)
    args = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--macos-create-app-bundle",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        f"--jobs={jobs}",
        f"--macos-app-name={APP_DISPLAY_NAME}",
        f"--macos-app-version={version}",
        # The postalgambit: URI scheme is registered afterwards by patching
        # Info.plist directly (register_url_scheme); Nuitka has no option for
        # CFBundleURLTypes.
        f"--output-dir={DIST_DIR}",
        f"--include-data-dir={ASSETS_DIR}=assets",
        f"--include-data-file={VERSION_FILE}=VERSION",
        f"--include-data-file={LICENSE_FILE}=LICENSE",
    ]
    if ICNS_FILE.exists():
        args.append(f"--macos-app-icon={ICNS_FILE}")
    else:
        print(f"[builddmg] WARNING: {ICNS_FILE} missing; run generate_icons.py.")
    args.append(str(ENTRY_SCRIPT))
    result = run(args, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(f"[builddmg] Nuitka failed (exit {result.returncode}).")

    # Nuitka may name the bundle after the entry script; normalise it.
    bundles = sorted(DIST_DIR.glob("*.app"))
    if not bundles:
        raise SystemExit(f"[builddmg] no .app produced under {DIST_DIR}.")
    app_path = DIST_DIR / APP_BUNDLE_NAME
    if bundles[0] != app_path:
        shutil.move(str(bundles[0]), str(app_path))
    return app_path


def strip_object_files(app_path: Path) -> None:
    """Remove PySide6's stray Mach-O .o files before signing.

    codesign --deep silently skips them and Gatekeeper then rejects the
    bundle as containing unsigned code.
    """
    section("Stripping stray object files")
    removed = 0
    for obj in app_path.rglob("*.o"):
        obj.unlink()
        removed += 1
    for objdir in sorted(app_path.rglob("objects-*"), reverse=True):
        if objdir.is_dir() and not any(objdir.iterdir()):
            objdir.rmdir()
    print(f"  removed {removed} object files")


def register_url_scheme(app_path: Path) -> None:
    """Add the postalgambit: URI scheme to the bundle's Info.plist.

    Clicked import links (postalgambit://...) only reach the app if the
    bundle advertises the scheme via CFBundleURLTypes. Nuitka has no option
    for this, so patch the plist directly. Must run before codesign, since
    editing Info.plist after signing invalidates the signature.
    """
    section("Registering the URL scheme")
    plist_path = app_path / "Contents" / "Info.plist"
    with plist_path.open("rb") as fh:
        info = plistlib.load(fh)
    info["CFBundleURLTypes"] = [
        {
            "CFBundleURLName": BUNDLE_ID,
            "CFBundleURLSchemes": [LINK_SCHEME],
        }
    ]
    with plist_path.open("wb") as fh:
        plistlib.dump(info, fh)
    print(f"  registered {LINK_SCHEME}:// in {plist_path.name}")


def sign_bundle(app_path: Path, entitlements: Path) -> None:
    section("Codesigning the bundle")
    run(
        [
            "codesign",
            "--force",
            "--deep",
            "--options",
            "runtime",
            "--entitlements",
            entitlements,
            "--sign",
            DEVELOPER_ID,
            app_path,
        ],
        check=True,
    )
    run(["codesign", "--verify", "--deep", "--strict", app_path], check=True)


def create_dmg(app_path: Path, version: str) -> Path:
    """Wrap the signed .app in a DMG; return the DMG path."""
    section("Creating the DMG")
    arch = platform.machine()
    dmg_path = PROJECT_ROOT / f"{DMG_BASENAME}-{version}-macos-{arch}.dmg"
    # create-dmg refuses to overwrite; clear any DMG left from a prior run
    # (the root is not wiped between builds the way DIST_DIR is).
    dmg_path.unlink(missing_ok=True)
    staging = DIST_DIR / "dmg-staging"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    # ditto preserves the framework symlinks codesign sealed; a plain copy
    # would dereference them and invalidate the embedded signatures.
    run(["ditto", app_path, staging / app_path.name], check=True)

    args = [
        "create-dmg",
        "--volname",
        APP_DISPLAY_NAME,
        "--window-size",
        str(DMG_WINDOW_WIDTH),
        str(DMG_WINDOW_HEIGHT),
        "--icon-size",
        str(DMG_ICON_SIZE),
        "--icon",
        app_path.name,
        str(DMG_APP_X),
        str(DMG_APP_Y),
        "--app-drop-link",
        str(DMG_DROP_X),
        str(DMG_DROP_Y),
    ]
    if ICNS_FILE.exists():
        args.extend(["--volicon", str(ICNS_FILE)])
    args.extend([str(dmg_path), str(staging)])
    result = run(args)
    if result.returncode not in CREATE_DMG_OK_CODES:
        raise SystemExit(f"[builddmg] create-dmg failed (exit {result.returncode}).")
    shutil.rmtree(staging, ignore_errors=True)
    return dmg_path


def sign_and_notarize_dmg(dmg_path: Path) -> None:
    section("Signing the DMG")
    run(["codesign", "--force", "--sign", DEVELOPER_ID, dmg_path], check=True)

    if APPLE_ID and APPLE_APP_PASSWORD:
        section("Notarizing (this waits on Apple)")
        run(
            [
                "xcrun",
                "notarytool",
                "submit",
                dmg_path,
                "--apple-id",
                APPLE_ID,
                "--password",
                APPLE_APP_PASSWORD,
                "--team-id",
                APPLE_TEAM_ID,
                "--wait",
            ],
            check=True,
        )
        run(["xcrun", "stapler", "staple", dmg_path], check=True)
    else:
        print(
            "[builddmg] APPLE_ID / APPLE_APP_PASSWORD not set; "
            "skipping notarization (DMG is signed but not notarized)."
        )

    run(["codesign", "--verify", dmg_path], check=True)


def main() -> int:
    if sys.platform != "darwin":
        print("[builddmg] ERROR: builddmg.py targets macOS.", file=sys.stderr)
        return 1

    require("create-dmg")
    if not shutil.which("codesign"):
        raise SystemExit(
            "[builddmg] codesign not found; install the Xcode Command Line "
            "Tools first (xcode-select --install)."
        )

    version = read_version()
    print(f"[builddmg] Building {APP_DISPLAY_NAME} {version} DMG")

    entitlements_fd, entitlements_name = tempfile.mkstemp(suffix=".plist")
    os.close(entitlements_fd)
    entitlements = Path(entitlements_name)
    try:
        entitlements.write_text(ENTITLEMENTS_XML, encoding="utf-8")
        app_path = build_app_bundle(version)
        strip_object_files(app_path)
        register_url_scheme(app_path)
        sign_bundle(app_path, entitlements)
        dmg_path = create_dmg(app_path, version)
        sign_and_notarize_dmg(dmg_path)
    finally:
        entitlements.unlink(missing_ok=True)

    size_mb = dmg_path.stat().st_size / (1024 * 1024)
    print(f"\n[builddmg] [OK] Built DMG: {dmg_path}")
    print(f"[builddmg] DMG size: {size_mb:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
