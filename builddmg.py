#!/usr/bin/env python3
"""Build the Postal Gambit macOS .app bundle and DMG.

macOS-only; run from the repo root with the venv active:

    python builddmg.py

Flow: build the .app with Nuitka (--macos-create-app-bundle), strip the
stray Mach-O object files PySide6 ships (Gatekeeper rejects a bundle that
contains unsigned code and codesign --deep silently skips them), codesign
the bundle, notarize and staple the bundle, wrap it in a DMG with
create-dmg, then sign, notarize and staple the DMG.

Notarization is mandatory. A Developer ID signature alone is not enough:
since macOS 10.15 Gatekeeper rejects signed-but-unnotarized apps with
"Apple could not verify ... is free of malware". Credentials come from the
keychain profile named in NOTARY_PROFILE, created once with
`xcrun notarytool store-credentials`. Set ALLOW_UNNOTARIZED=1 for a local
test build; that output must never be published as a release artifact.

The .icns ships pre-generated in assets/ (generate_icons.py emits it from
the master PNG), so no image conversion happens here.
"""

from __future__ import annotations

import os
import re
import plistlib
import shutil
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement

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

# The notarization credential for this app, created once with
#   xcrun notarytool store-credentials PostalGambit \
#     --apple-id <id> --team-id <team> --password <app-specific>
# One profile per app means a leaked credential can be revoked for a single
# app. Stated explicitly rather than derived from a display name: the profile
# is a fact registered with Apple, and deriving it would silently change which
# credential the build looks for if that name were ever edited.
# APPLE_KEYCHAIN_PROFILE overrides it.
NOTARY_PROFILE = os.environ.get("APPLE_KEYCHAIN_PROFILE", "") or "PostalGambit"

# The notary service accepts only an app-specific password from appleid.apple.com
# and rejects the Apple account password with HTTP 401. The shape is distinctive,
# so it is checked before the build rather than discovered after it.
APP_SPECIFIC_PASSWORD_RE = re.compile(r"^[a-z]{4}-[a-z]{4}-[a-z]{4}-[a-z]{4}$")

# Escape hatch for local test builds. Distribution builds must never set this:
# an unnotarized DMG is rejected by Gatekeeper on every machine but the one
# that signed it, and the failure is invisible at build time.
ALLOW_UNNOTARIZED = os.environ.get("ALLOW_UNNOTARIZED", "") == "1"
# Notarization is the default and the keychain profile always resolves, so
# the only way to skip it is to ask for that explicitly.
NOTARIZING = not ALLOW_UNNOTARIZED

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


def create_dmg(app_path: Path) -> Path:
    """Wrap the signed .app in a DMG; return the DMG path."""
    section("Creating the DMG")
    dmg_path = PROJECT_ROOT / f"{DMG_BASENAME}.dmg"
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
    set_dmg_file_icon(dmg_path)
    return dmg_path


def set_dmg_file_icon(dmg_path: Path) -> None:
    """Give the .dmg file its own Finder icon (the app icon).

    create-dmg's --volicon only skins the mounted volume; the downloaded
    .dmg file shows a generic disk-image icon unless a custom icon resource
    is attached to the file itself. This attaches it via the Xcode CLT tools
    (already required for codesign). Best-effort: the icon lives in the file's
    resource fork, independent of the DMG's code signature, so if a tool is
    missing the build continues with the volume icon still applied.
    """
    if not ICNS_FILE.exists() or not shutil.which("xcrun"):
        print("[builddmg] WARNING: cannot set .dmg file icon; volume icon only.")
        return
    section("Setting the DMG file icon")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            icon_copy = Path(tmp) / "icon.icns"
            rsrc = Path(tmp) / "icon.rsrc"
            shutil.copyfile(ICNS_FILE, icon_copy)
            run(
                ["sips", "-i", str(icon_copy)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            with rsrc.open("wb") as fh:
                run(
                    ["xcrun", "DeRez", "-only", "icns", str(icon_copy)],
                    check=True,
                    stdout=fh,
                )
            run(["xcrun", "Rez", "-append", str(rsrc), "-o", str(dmg_path)], check=True)
            run(["xcrun", "SetFile", "-a", "C", str(dmg_path)], check=True)
        print(f"  applied {ICNS_FILE.name} as the .dmg file icon")
    except (subprocess.CalledProcessError, OSError) as exc:
        print(
            f"[builddmg] WARNING: could not set .dmg file icon ({exc}); "
            "volume icon still applied."
        )


def require_notarization_credentials() -> None:
    """Stop before the build starts if the release cannot be notarized.

    Checked next to the create-dmg and codesign requirements so a missing
    password costs a second rather than a failed Nuitka run.
    """
    if ALLOW_UNNOTARIZED:
        print("[builddmg] WARNING: ALLOW_UNNOTARIZED=1; local test build only.")
        return
    if APPLE_ID and APPLE_APP_PASSWORD:
        if not APP_SPECIFIC_PASSWORD_RE.match(APPLE_APP_PASSWORD):
            raise SystemExit(
                "[builddmg] APPLE_APP_PASSWORD is not an app-specific password.\n"
                "Expected four lowercase groups of four, like abcd-efgh-ijkl-mnop.\n"
                "An Apple account password is rejected by the notary service with\n"
                "'HTTP status code: 401. Invalid credentials'.\n"
                "Generate one at https://appleid.apple.com (Sign-In and Security,\n"
                "App-Specific Passwords), or leave both variables unset and store\n"
                f"the credential in the keychain as profile {NOTARY_PROFILE}."
            )
        print(f"[builddmg] Notarizing as {APPLE_ID} (team {APPLE_TEAM_ID})")
        return
    print(f"[builddmg] Notarizing with keychain profile {NOTARY_PROFILE}")


def notarytool_submit(target: Path) -> None:
    """Submit target to Apple and wait for the verdict.

    A failed submission stops the build rather than leaving an artifact that
    looks distributable. subprocess is called directly rather than through run()
    so that neither the echoed command nor the failure path exposes the
    password. Stapling is separate because the submitted file and the file that
    carries the ticket differ for a bundle: a zip goes up, the .app gets
    stapled.
    """
    cmd = [
        "xcrun",
        "notarytool",
        "submit",
        str(target),
        *notarytool_credentials(),
        "--wait",
    ]
    print(f"[builddmg] $ {redact(cmd)}")
    if subprocess.run(cmd, check=False).returncode == 0:
        return
    raise SystemExit(
        "[builddmg] notarization failed (notarytool output above).\n"
        "'HTTP status code: 401' means the credential is wrong: use an\n"
        "app-specific password from https://appleid.apple.com, not your Apple\n"
        "account password.\n"
        "For an 'Invalid' verdict, the per-binary reasons are in:\n"
        f"  xcrun notarytool log <submission-id> --apple-id "
        f"{APPLE_ID or '<apple-id>'} --team-id {APPLE_TEAM_ID}"
    )


def notarytool_credentials() -> list[str]:
    """Authentication arguments for notarytool.

    An explicit APPLE_ID and APPLE_APP_PASSWORD pair wins, for CI that has no
    keychain. Otherwise the per-app profile is used, which keeps the secret out
    of the process arguments where any other process could read it via ps.
    """
    if APPLE_ID and APPLE_APP_PASSWORD:
        return [
            "--apple-id",
            APPLE_ID,
            "--password",
            APPLE_APP_PASSWORD,
            "--team-id",
            APPLE_TEAM_ID,
        ]
    return ["--keychain-profile", NOTARY_PROFILE]


def check_runtime_dependencies() -> None:
    """Fail if anything in requirements.txt is absent from the build interpreter.

    Nuitka only warns when a package it is told to include cannot be found, so a
    stale venv yields a bundle that builds, signs and notarizes cleanly and then
    dies at launch with ModuleNotFoundError. Checking the interpreter that is
    about to be frozen turns a silent runtime failure into a build failure.
    """
    section("Runtime dependencies")
    requirements = PROJECT_ROOT / "requirements.txt"
    if not requirements.is_file():
        raise SystemExit(f"[builddmg] {requirements} is missing.")

    missing: list[str] = []
    checked = 0
    for raw in requirements.read_text(encoding="utf-8").splitlines():
        line = raw.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement as error:
            raise SystemExit(f"[builddmg] cannot parse '{line}': {error}")
        # A marker such as sys_platform == "win32" means the package is not
        # wanted here, so its absence is correct rather than a fault.
        if requirement.marker is not None and not requirement.marker.evaluate():
            continue
        checked += 1
        try:
            metadata.version(requirement.name)
        except metadata.PackageNotFoundError:
            missing.append(requirement.name)

    if missing:
        raise SystemExit(
            f"[builddmg] the build interpreter is missing {len(missing)} of "
            f"{checked} requirements:\n"
            + "".join(f"  {name}\n" for name in missing)
            + "Nuitka would omit them and the app would crash at launch with\n"
            "ModuleNotFoundError. Install them first:\n"
            "  pip install -r requirements.txt"
        )
    print(f"  all {checked} requirements present")


def redact(cmd: list[str]) -> str:
    """Render a command with the value after --password masked.

    run() echoes every command it runs, and CalledProcessError repeats the whole
    argument list in its traceback. Both would otherwise copy the app-specific
    password into build logs and CI output.
    """
    parts: list[str] = []
    mask_next = False
    for arg in (str(c) for c in cmd):
        parts.append("********" if mask_next else arg)
        mask_next = arg == "--password"
    return " ".join(parts)


def notarize_bundle(app_path: Path) -> None:
    """Notarize and staple the .app before it is wrapped in the DMG.

    Stapling only the DMG leaves the copied-out .app with no local ticket, so
    Gatekeeper falls back to an online check and the app fails to launch for
    anyone offline or behind a restrictive network. notarytool takes archives
    only, so ditto zips the bundle first (ditto preserves the framework
    symlinks the embedded signature depends on); the ticket goes on the bundle,
    since a zip cannot carry one.
    """
    if not NOTARIZING:
        return
    section("Notarizing the app bundle (this waits on Apple)")
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"{app_path.stem}.zip"
        run(
            ["ditto", "-c", "-k", "--keepParent", app_path, archive],
            check=True,
        )
        notarytool_submit(archive)
    run(["xcrun", "stapler", "staple", app_path], check=True)


def sign_and_notarize_dmg(dmg_path: Path) -> None:
    section("Signing the DMG")
    run(["codesign", "--force", "--sign", DEVELOPER_ID, dmg_path], check=True)
    run(["codesign", "--verify", dmg_path], check=True)

    if not NOTARIZING:
        print("[builddmg] WARNING: unnotarized DMG; do not publish this build.")
        return

    section("Notarizing the DMG (this waits on Apple)")
    notarytool_submit(dmg_path)
    run(["xcrun", "stapler", "staple", dmg_path], check=True)
    # stapler validate proves a ticket is attached; spctl replays the check
    # Gatekeeper runs on the end user's machine. Together they catch the silent
    # case where signing succeeded but notarization never happened.
    run(["xcrun", "stapler", "validate", dmg_path], check=True)
    run(["spctl", "--assess", "--type", "install", "-vv", dmg_path], check=True)


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
    check_runtime_dependencies()
    require_notarization_credentials()

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
        notarize_bundle(app_path)
        dmg_path = create_dmg(app_path)
        sign_and_notarize_dmg(dmg_path)
    finally:
        entitlements.unlink(missing_ok=True)

    size_mb = dmg_path.stat().st_size / (1024 * 1024)
    print(f"\n[builddmg] [OK] Built DMG: {dmg_path}")
    print(f"[builddmg] DMG size: {size_mb:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
