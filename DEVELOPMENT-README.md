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
  `dist-installer/PostalGambitSetup.exe`. It compiles `installer_main.py`
  at the repository root, not a script inside the package: a script is
  compiled with its own directory on the module search path, so compiling
  `installer/app.py` directly would leave the `installer.*` imports
  unresolvable.

Run the setup program from source with `python installer_main.py`; run the
uninstall flow with `python installer_main.py --uninstall`.

The installer is per-user and needs no admin: it extracts to
`%LOCALAPPDATA%\Programs\PostalGambit`, writes the HKCU uninstall entry,
offers Desktop and Start Menu shortcuts, registers the `postalgambit:`
URI scheme and supports install, upgrade, repair and uninstall. It offers
to close a running Postal Gambit first and reports a phase and a
percentage while it works.

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

## The GitHub Pages site

`docs/` is a static GitHub Pages site, hand-written and with no build
step. Enable it once in the repo settings: Settings, Pages, deploy from
branch, `main` and `/docs`.

- `index.html` is the landing page: what the app is, how a game flows,
  the feature and FAQ sections and a per-platform download section. The
  download buttons point at GitHub's `releases/latest/download` redirect,
  so they never go stale; a small script decorates the page with the
  live release version and each asset's size.
- `why.html` is the reasoning page, linked from the nav.
- `open/index.html` is the click-to-import bounce page: emails carry
  `https://oernster.github.io/postal-gambit/open/#v=1&d=<payload>`, and
  the page rebuilds the `postalgambit:` URI locally (the fragment never
  reaches any server) and launches the app. That address is the one the
  app emits, from `WEB_LINK_BASE` in `postalgambit/domain/applink.py`,
  so it must keep resolving whatever canonical host the site declares
  for search engines.

Two site rules: the pages carry no dates or years of any kind; any
version number they show sits inside `<!--VERSION-->` markers that
`python stamp_version.py` refreshes from `VERSION`. Run that script after
bumping `VERSION`; it is idempotent and prints what it changed.

## Release checklist

1. Bump `VERSION`.
2. `python stamp_version.py` to carry the new version into the site.
3. `pytest -v --cov` green.
4. `python generate_icons.py` if the master icon changed.
5. Build per platform as above.
6. Draft the release notes from `NOTES.md`.
