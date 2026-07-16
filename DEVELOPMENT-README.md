# Postal Gambit Development

How to set up, test and build Postal Gambit on each platform. User-facing
documentation lives in [README.md](README.md); architecture in
[ARCHITECTURE.md](ARCHITECTURE.md); the test policy in
[TESTING.md](TESTING.md).

## Setup

Python 3.13 or newer.

```
pip install -r requirements.txt -r requirements-dev.txt
python main.py
```

The app stores its data under `~/.postal-gambit/` (one JSON file per game
plus `settings.json`).

## Test

```
pytest -v --cov
```

The gate is 100% coverage outside the UI layer; see
[TESTING.md](TESTING.md). black and flake8 run inside the suite, so a
green run also means the tree is formatted and lint-clean.

## Versioning

The version lives in the `VERSION` file at the repo root and nowhere
else. Runtime reads it through `postalgambit/version.py`; every build
script reads it through a shared helper. To cut a release, bump `VERSION`
and rebuild.

## Icons

Every platform asset derives from the repo-root master
`postal-gambit.png` (1024x1024 RGBA, transparent background):

```
python generate_icons.py
```

writes the size set, the multi-frame `assets/postal-gambit.ico` and the
macOS `assets/postal-gambit.icns`. Never edit the generated files; edit
the master and regenerate.

## Windows: exe and installer

Nuitka needs a working C compiler (MSVC or MinGW via Nuitka's prompts).
The repo venv carries Nuitka; any interpreter with the two requirements
files plus Nuitka works.

```
python buildexe.py
python buildinstaller.py
```

- `buildexe.py` builds the standalone bundle (PE metadata, icon, bundled
  assets and licences) directly into `installer/payload/PostalGambit/`.
- `buildinstaller.py` zips the payload (Nuitka onefile strips loose
  executables from data dirs, so zip-then-extract is load-bearing) and
  builds the themed GUI installer to
  `dist-installer/PostalGambitSetup.exe`.

The installer is per-user and needs no admin: it extracts to
`%LOCALAPPDATA%\Programs\PostalGambit`, writes the HKCU uninstall entry,
offers Desktop and Start Menu shortcuts, registers the `postalgambit:`
URI scheme and supports install, upgrade, repair and uninstall.

## Linux: Flatpak

Requires `flatpak` and `flatpak-builder` with the freedesktop Platform
runtime (the exact version is pinned inside the script).

```
./build_flatpak.sh
```

The script self-generates the manifest, launcher, desktop entry and
metainfo, pre-downloads the Python wheels on the host so the sandbox
build runs offline, installs the real hicolor icon set and registers the
`postalgambit:` scheme handler. App id `uk.codecrafter.PostalGambit`.
`./clean_flatpak.sh` removes only the flatpak artefacts; the Windows and
macOS outputs are untouched.

## macOS: DMG

Run on macOS with `create-dmg` installed (Homebrew).

```
python builddmg.py
```

Builds the `.app` bundle with Nuitka, strips stray object files that
break Gatekeeper, signs with the Developer ID certificate when one is
available, wraps the DMG and notarizes plus staples only when `APPLE_ID`
and `APPLE_APP_PASSWORD` are set. Output lands in `dist-macos/`. The
bundle declares the `postalgambit:` URL scheme.

## Click-to-import page

`docs/` is a static GitHub Pages site. `docs/open/index.html` is the
click-to-import bounce page: emails carry
`https://oernster.github.io/postal-gambit/open/#v=1&d=<payload>` and the
page rebuilds the `postalgambit:` URI locally (the fragment never reaches
any server) and launches the app. Enable it once in the repo settings:
Settings, Pages, deploy from branch, `main` and `/docs`. The page is
self-contained; no build step.

## Release checklist

1. Bump `VERSION`.
2. `pytest -v --cov` green.
3. `python generate_icons.py` if the master icon changed.
4. Build per platform as above.
5. Draft the release notes from `NOTES.md`.
